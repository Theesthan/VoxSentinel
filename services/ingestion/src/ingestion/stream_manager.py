"""
Stream connection manager for VoxSentinel ingestion service.

Manages multiple concurrent streams.  On ``start_stream`` it spawns
an asyncio task running the extract → chunk → publish pipeline.
Each chunk is published to the Redis stream ``audio_chunks:{stream_id}``
via ``xadd``.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from typing import Any

import structlog
from prometheus_client import Counter

from tg_common.messaging.redis_client import RedisClient
from tg_common.models.stream import Stream

from ingestion.audio_extractor import extract_audio
from ingestion.chunk_producer import AudioChunk, produce_chunks
from ingestion.reconnection import ReconnectionFailed, with_reconnection

logger = structlog.get_logger()

# ── Prometheus metrics ──
CHUNKS_PRODUCED = Counter(
    "ingestion_chunks_produced_total",
    "Total number of audio chunks produced and published.",
    ["stream_id"],
)
RECONNECTIONS = Counter(
    "ingestion_stream_reconnections_total",
    "Total number of stream reconnection attempts.",
    ["stream_id"],
)


class StreamManager:
    """Manages concurrent audio-ingestion pipelines.

    Each managed stream gets its own asyncio task that:

    1. Opens the source URL with PyAV via ``audio_extractor``.
    2. Buffers and chunks PCM bytes via ``chunk_producer``.
    3. Publishes each ``AudioChunk`` to ``audio_chunks:{stream_id}``
       via Redis ``xadd``.

    Reconnection is handled automatically using exponential backoff.

    Args:
        redis_client: An **already-connected** ``RedisClient``.
    """

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._stop_events: dict[str, asyncio.Event] = {}

    # ── public API ──

    async def start_stream(self, stream: Stream) -> None:
        """Start an ingestion pipeline for *stream*.

        If the stream is already running the call is a no-op.

        Args:
            stream: ``Stream`` Pydantic model from tg-common.
        """
        sid = str(stream.stream_id)
        if sid in self._tasks and not self._tasks[sid].done():
            logger.info("stream_already_running", stream_id=sid)
            return

        stop_event = asyncio.Event()
        self._stop_events[sid] = stop_event
        task = asyncio.create_task(
            self._run_pipeline(stream, stop_event),
            name=f"ingest-{sid}",
        )
        self._tasks[sid] = task
        logger.info("stream_started", stream_id=sid, source_url=stream.source_url)

    async def stop_stream(self, stream_id: str | uuid.UUID) -> None:
        """Stop a running ingestion pipeline.

        Args:
            stream_id: The stream UUID (str or UUID).
        """
        sid = str(stream_id)
        stop_event = self._stop_events.pop(sid, None)
        if stop_event is not None:
            stop_event.set()

        task = self._tasks.pop(sid, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("stream_stopped", stream_id=sid)

    async def stop_all(self) -> None:
        """Stop all running pipelines."""
        sids = list(self._tasks.keys())
        for sid in sids:
            await self.stop_stream(sid)

    @property
    def active_streams(self) -> list[str]:
        """Return IDs of currently running streams."""
        return [sid for sid, t in self._tasks.items() if not t.done()]

    # ── internal ──

    async def _run_pipeline(self, stream: Stream, stop_event: asyncio.Event) -> None:
        """Execute the extract → chunk → publish loop with reconnection.

        Args:
            stream: Stream configuration.
            stop_event: Set when the pipeline should terminate.
        """
        sid = str(stream.stream_id)
        session_id = stream.session_id or uuid.uuid4()
        log = logger.bind(stream_id=sid, session_id=str(session_id))

        def _reconnection_counter() -> None:
            RECONNECTIONS.labels(stream_id=sid).inc()

        async def _run_once() -> None:
            pcm_gen = extract_audio(stream.source_url, stream_id=sid)
            chunk_gen = produce_chunks(
                pcm_gen,
                stream_id=stream.stream_id,
                session_id=session_id,
            )
            redis_key = f"audio_chunks:{sid}"
            async for chunk in chunk_gen:
                if stop_event.is_set():
                    return
                await self._publish_chunk(redis_key, chunk)
                CHUNKS_PRODUCED.labels(stream_id=sid).inc()

        try:
            await with_reconnection(
                _run_once,
                stream_id=sid,
                reconnection_counter=_reconnection_counter,
            )
        except ReconnectionFailed:
            log.error("pipeline_reconnection_failed")
        except asyncio.CancelledError:
            log.info("pipeline_cancelled")
        except Exception:
            log.exception("pipeline_unexpected_error")

    async def _publish_chunk(self, redis_key: str, chunk: AudioChunk) -> None:
        """Publish an ``AudioChunk`` to a Redis stream via xadd.

        Args:
            redis_key: Redis stream key (``audio_chunks:{stream_id}``).
            chunk: The audio chunk to publish.
        """
        fields: dict[str, str] = {
            "chunk_id": str(chunk.chunk_id),
            "stream_id": str(chunk.stream_id),
            "session_id": str(chunk.session_id),
            "pcm_b64": base64.b64encode(chunk.pcm_bytes).decode(),
            "timestamp": chunk.timestamp.isoformat(),
            "duration_ms": str(chunk.duration_ms),
        }
        await self._redis.xadd(redis_key, fields, maxlen=10_000)
