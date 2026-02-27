"""
VAD chunk classification processor for VoxSentinel.

Subscribes to Redis stream ``audio_chunks:{stream_id}`` via blocking
``xread``, classifies each chunk with Silero VAD, and forwards speech
chunks to ``speech_chunks:{stream_id}``.  Emits a ``vad_speech_ratio``
gauge per stream per 60-second window.
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import structlog
from prometheus_client import Gauge

from tg_common.config import get_settings
from tg_common.messaging.redis_client import RedisClient

from vad.silero_vad import SileroVADModel

logger = structlog.get_logger()

# ── Prometheus metrics ──
VAD_SPEECH_RATIO = Gauge(
    "vad_speech_ratio",
    "Ratio of speech chunks to total chunks per stream (60 s window).",
    ["stream_id"],
)

# Window for speech-ratio metric (seconds).
_METRIC_WINDOW_S: float = 60.0


class VADProcessor:
    """Consume audio chunks from Redis, classify, and forward speech.

    For each ``audio_chunks:{stream_id}`` entry the processor:

    1. Decodes the base-64 PCM payload.
    2. Calls ``SileroVADModel.classify`` (via ``asyncio.to_thread``).
    3. If the score >= ``TG_VAD_THRESHOLD`` (default 0.5), publishes
       the chunk to ``speech_chunks:{stream_id}``.
    4. Updates the ``vad_speech_ratio`` gauge every 60 s.

    Args:
        vad_model: A **loaded** ``SileroVADModel`` instance.
        redis_client: A **connected** ``RedisClient``.
        threshold: Speech-confidence threshold (0.0–1.0).
    """

    def __init__(
        self,
        vad_model: SileroVADModel,
        redis_client: RedisClient,
        threshold: float | None = None,
    ) -> None:
        self._model = vad_model
        self._redis = redis_client
        self._threshold = threshold if threshold is not None else get_settings().vad_threshold

        # Per-stream counters for the speech-ratio metric window.
        self._window_total: dict[str, int] = {}
        self._window_speech: dict[str, int] = {}
        self._window_start: float = time.monotonic()

    # ── public API ──

    async def process_stream(
        self,
        stream_id: str,
        *,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Blocking loop: read chunks from Redis & classify.

        Args:
            stream_id: The stream UUID whose chunks to consume.
            stop_event: Set this event to break the loop gracefully.
        """
        redis_key = f"audio_chunks:{stream_id}"
        out_key = f"speech_chunks:{stream_id}"
        last_id = "0"  # start from the beginning
        log = logger.bind(stream_id=stream_id)
        log.info("vad_processor_started", redis_key=redis_key)

        while stop_event is None or not stop_event.is_set():
            try:
                entries = await self._redis.xread(
                    {redis_key: last_id},
                    count=10,
                    block=1000,  # 1 s block to allow stop_event checks
                )
            except Exception:
                log.exception("vad_xread_error")
                await asyncio.sleep(1)
                continue

            if not entries:
                self._maybe_flush_metrics()
                continue

            for _stream_name, messages in entries:
                for entry_id, fields in messages:
                    last_id = entry_id
                    await self._handle_chunk(fields, stream_id, out_key, log)

            self._maybe_flush_metrics()

        log.info("vad_processor_stopped")

    # ── internal ──

    async def _handle_chunk(
        self,
        fields: dict[str, str],
        stream_id: str,
        out_key: str,
        log: Any,
    ) -> None:
        """Classify a single chunk and forward if speech."""
        pcm_b64 = fields.get("pcm_b64", "")
        if not pcm_b64:
            log.warning("vad_missing_pcm_b64")
            return

        pcm_bytes = base64.b64decode(pcm_b64)
        score = await self._model.classify(pcm_bytes)

        # Update window counters.
        self._window_total[stream_id] = self._window_total.get(stream_id, 0) + 1

        if score >= self._threshold:
            self._window_speech[stream_id] = self._window_speech.get(stream_id, 0) + 1
            # Forward the original fields to the speech_chunks stream.
            await self._redis.xadd(out_key, fields, maxlen=10_000)
            log.debug("vad_speech", score=round(score, 3))
        else:
            log.debug("vad_non_speech", score=round(score, 3))

    def _maybe_flush_metrics(self) -> None:
        """Emit ``vad_speech_ratio`` gauge if the 60 s window elapsed."""
        now = time.monotonic()
        if now - self._window_start < _METRIC_WINDOW_S:
            return

        for sid in self._window_total:
            total = self._window_total[sid]
            speech = self._window_speech.get(sid, 0)
            ratio = speech / total if total > 0 else 0.0
            VAD_SPEECH_RATIO.labels(stream_id=sid).set(round(ratio, 4))
            logger.info(
                "vad_speech_ratio_emitted",
                stream_id=sid,
                ratio=round(ratio, 4),
                total=total,
                speech=speech,
            )

        # Reset window.
        self._window_total.clear()
        self._window_speech.clear()
        self._window_start = now
