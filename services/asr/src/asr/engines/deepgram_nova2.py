"""
Deepgram Nova-2 ASR engine implementation for VoxSentinel.

Connects to the Deepgram Nova-2 streaming API via WebSocket,
sends audio chunks, and returns partial/final TranscriptToken
objects with word-level timestamps and confidence scores.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from tg_common.models import TranscriptToken, WordTimestamp

from asr.engine_base import ASREngine

logger = structlog.get_logger()


class DeepgramNova2Engine(ASREngine):
    """Deepgram Nova-2 streaming ASR engine.

    Opens a WebSocket connection to the Deepgram Nova-2 API and
    forwards PCM audio chunks.  Partial and final transcripts are
    collected into an internal queue and yielded from
    :meth:`stream_audio`.

    Args:
        api_key: Deepgram API key.
        language: BCP-47 language code.
        sample_rate: Audio sample rate in Hz.
        encoding: Audio encoding format.
        channels: Number of audio channels.
    """

    def __init__(
        self,
        api_key: str,
        *,
        language: str = "en",
        sample_rate: int = 16_000,
        encoding: str = "linear16",
        channels: int = 1,
    ) -> None:
        self._api_key = api_key
        self._language = language
        self._sample_rate = sample_rate
        self._encoding = encoding
        self._channels = channels

        self._client: DeepgramClient | None = None
        self._connection: Any = None
        self._token_queue: asyncio.Queue[TranscriptToken] = asyncio.Queue()
        self._connected: bool = False
        self._session_start: datetime | None = None

    # ── ASREngine interface ──

    @property
    def name(self) -> str:  # noqa: D401
        """Engine identifier."""
        return "deepgram_nova2"

    async def connect(self) -> None:
        """Open a live WebSocket connection to Deepgram Nova-2."""
        self._client = DeepgramClient(self._api_key)
        self._connection = self._client.listen.asynclive.v("1")

        self._connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
        self._connection.on(LiveTranscriptionEvents.Error, self._on_error)
        self._connection.on(LiveTranscriptionEvents.Close, self._on_close)

        options = LiveOptions(
            model="nova-2",
            language=self._language,
            encoding=self._encoding,
            sample_rate=self._sample_rate,
            channels=self._channels,
            smart_format=True,
            interim_results=True,
            endpointing=300,
            utterance_end_ms=1000,
        )

        started = await self._connection.start(options)
        if started:
            self._connected = True
            self._session_start = datetime.now(timezone.utc)
            # Drain any stale tokens from a previous session.
            while not self._token_queue.empty():
                self._token_queue.get_nowait()
            logger.info("deepgram_connected", language=self._language)
        else:
            raise RuntimeError("Failed to start Deepgram live connection")

    async def disconnect(self) -> None:
        """Close the Deepgram WebSocket connection."""
        if self._connection is not None:
            try:
                await self._connection.finish()
            except Exception:  # noqa: BLE001
                logger.debug("deepgram_disconnect_error", exc_info=True)
        self._connected = False
        self._connection = None
        self._client = None
        logger.info("deepgram_disconnected")

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        """Send *chunk* to Deepgram and yield any available tokens.

        Tokens are collected asynchronously via the WebSocket callback
        and drained from the internal queue on each call.
        """
        if not self._connected or self._connection is None:
            raise RuntimeError("Deepgram engine is not connected")

        await self._connection.send(chunk)

        # Give the event loop a chance to process incoming messages.
        await asyncio.sleep(0.01)

        # Drain all queued tokens.
        while not self._token_queue.empty():
            yield self._token_queue.get_nowait()

    async def health_check(self) -> bool:
        """Return ``True`` when the WebSocket is connected."""
        return self._connected

    # ── Deepgram event handlers ──

    async def _on_transcript(self, _connection: Any, result: Any, **_kw: Any) -> None:
        """Handle incoming transcript events from Deepgram."""
        try:
            channel = result.channel
            alternatives = channel.alternatives
            if not alternatives:
                return

            alt = alternatives[0]
            transcript_text: str = alt.transcript
            if not transcript_text:
                return

            # Build word-level timestamps.
            words: list[WordTimestamp] = []
            for w in getattr(alt, "words", []) or []:
                words.append(
                    WordTimestamp(
                        word=w.word,
                        start_ms=int(w.start * 1000),
                        end_ms=int(w.end * 1000),
                        confidence=float(w.confidence),
                    )
                )

            session_start = self._session_start or datetime.now(timezone.utc)
            start_offset = float(getattr(result, "start", 0))
            duration = float(getattr(result, "duration", 0))

            start_time = session_start + timedelta(seconds=start_offset)
            end_time = start_time + timedelta(seconds=duration)

            token = TranscriptToken(
                text=transcript_text,
                is_final=bool(getattr(result, "is_final", False)),
                start_time=start_time,
                end_time=end_time,
                confidence=float(getattr(alt, "confidence", 0.0)),
                language=self._language,
                word_timestamps=words,
            )
            await self._token_queue.put(token)
        except Exception:  # noqa: BLE001
            logger.error("deepgram_transcript_parse_error", exc_info=True)

    async def _on_error(self, _connection: Any, error: Any, **_kw: Any) -> None:
        """Handle Deepgram WebSocket errors."""
        logger.error("deepgram_error", error=str(error))
        self._connected = False

    async def _on_close(self, _connection: Any, close_msg: Any, **_kw: Any) -> None:
        """Handle Deepgram WebSocket close."""
        logger.warning("deepgram_connection_closed", close_msg=str(close_msg))
        self._connected = False
