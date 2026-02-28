"""
Whisper V3 Turbo ASR engine implementation for VoxSentinel.

Self-hosted Whisper V3 Turbo inference using faster-whisper
(CTranslate2-based). Accepts audio chunks, accumulates 3 seconds
of PCM before running inference, and returns TranscriptToken
objects in the unified format.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import structlog
from faster_whisper import WhisperModel

from tg_common.models import TranscriptToken, WordTimestamp

from asr.engine_base import ASREngine

logger = structlog.get_logger()

# 16-bit signed PCM → 2 bytes per sample, mono 16 kHz.
_BYTES_PER_SAMPLE = 2
_SAMPLE_RATE = 16_000


class WhisperV3TurboEngine(ASREngine):  # type: ignore[misc]
    """Whisper V3 Turbo local-inference ASR engine.

    Accumulates PCM audio in an internal buffer.  Once the buffer
    reaches *accumulation_seconds* (default 3.0 s), the full buffer is
    transcribed using ``faster-whisper`` and tokens are yielded.

    Args:
        model_size: CTranslate2 model identifier.
        device: ``"cuda"`` or ``"cpu"``; ``None`` = auto-detect.
        compute_type: CTranslate2 compute type.
        accumulation_seconds: Seconds of audio to buffer before
            running inference (default 3.0).
    """

    def __init__(
        self,
        model_size: str = "large-v3-turbo",
        *,
        device: str | None = None,
        compute_type: str = "float16",
        accumulation_seconds: float = 3.0,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._accumulation_seconds = accumulation_seconds

        self._model: WhisperModel | None = None
        self._audio_buffer = bytearray()
        self._buffer_threshold = int(
            accumulation_seconds * _SAMPLE_RATE * _BYTES_PER_SAMPLE
        )
        self._session_start: datetime | None = None
        self._total_samples_processed: int = 0

    # ── ASREngine interface ──

    @property
    def name(self) -> str:  # noqa: D401
        """Engine identifier."""
        return "whisper_v3_turbo"

    async def connect(self) -> None:
        """Load the Whisper model on GPU (CUDA) or CPU."""
        import torch  # deferred import — may not be installed in CI

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        compute_type = self._compute_type if device == "cuda" else "int8"

        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(self._model_size, device=device, compute_type=compute_type),
        )
        self._session_start = datetime.now(timezone.utc)
        self._audio_buffer = bytearray()
        self._total_samples_processed = 0
        logger.info(
            "whisper_model_loaded",
            model=self._model_size,
            device=device,
            compute_type=compute_type,
        )

    async def disconnect(self) -> None:
        """Unload the Whisper model and flush the audio buffer."""
        remaining_tokens: list[TranscriptToken] = []
        if self._audio_buffer and self._model is not None:
            async for token in self._transcribe_buffer():
                remaining_tokens.append(token)
        self._model = None
        self._audio_buffer = bytearray()
        logger.info("whisper_model_unloaded", flushed_tokens=len(remaining_tokens))

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        """Accumulate *chunk* and transcribe when the buffer is full.

        Yields nothing until ``accumulation_seconds`` of audio have been
        buffered, then transcribes the full buffer and yields tokens.
        """
        if self._model is None:
            raise RuntimeError("Whisper engine is not connected")

        self._audio_buffer.extend(chunk)

        if len(self._audio_buffer) < self._buffer_threshold:
            return  # not enough audio yet

        async for token in self._transcribe_buffer():
            yield token

    async def health_check(self) -> bool:
        """Return ``True`` when the Whisper model is loaded."""
        return self._model is not None

    # ── internal helpers ──

    async def _transcribe_buffer(self) -> AsyncIterator[TranscriptToken]:
        """Run inference on the accumulated buffer and yield tokens."""
        if not self._audio_buffer or self._model is None:
            return

        # Convert 16-bit PCM → float32 normalised to [-1, 1].
        audio_array = (
            np.frombuffer(bytes(self._audio_buffer), dtype=np.int16).astype(np.float32)
            / 32768.0
        )

        model = self._model  # local ref for the executor closure
        loop = asyncio.get_running_loop()

        def _run_transcription() -> tuple[list[Any], Any]:
            seg_gen, info = model.transcribe(
                audio_array, beam_size=5, word_timestamps=True
            )
            return list(seg_gen), info

        segments, info = await loop.run_in_executor(None, _run_transcription)

        offset_s = self._total_samples_processed / _SAMPLE_RATE
        session_start = self._session_start or datetime.now(timezone.utc)

        for segment in segments:
            words: list[WordTimestamp] = []
            for w in getattr(segment, "words", []) or []:
                words.append(
                    WordTimestamp(
                        word=w.word.strip(),
                        start_ms=int((offset_s + w.start) * 1000),
                        end_ms=int((offset_s + w.end) * 1000),
                        confidence=float(w.probability),
                    )
                )

            avg_conf = (
                sum(w.confidence for w in words) / len(words) if words else 0.0
            )
            start_time = session_start + timedelta(seconds=offset_s + segment.start)
            end_time = session_start + timedelta(seconds=offset_s + segment.end)

            yield TranscriptToken(
                text=segment.text.strip(),
                is_final=True,
                start_time=start_time,
                end_time=end_time,
                confidence=avg_conf,
                language=getattr(info, "language", "en"),
                word_timestamps=words,
            )

        # Advance the sample counter and reset the buffer.
        self._total_samples_processed += len(self._audio_buffer) // _BYTES_PER_SAMPLE
        self._audio_buffer = bytearray()
