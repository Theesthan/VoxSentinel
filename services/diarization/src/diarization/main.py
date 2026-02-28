"""
Diarization service entry point for VoxSentinel.

Accumulates 3 seconds of PCM from ``speech_chunks:{stream_id}``, runs
pyannote diarization, and publishes speaker segments to
``diarization_events:{stream_id}``.

Separately, subscribes to ``transcript_tokens:{stream_id}``, merges
incoming tokens with the latest diarization window, and re-publishes
enriched tokens to ``enriched_tokens:{stream_id}``.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app

from tg_common.messaging.redis_client import RedisClient

from diarization import health
from diarization.pyannote_pipeline import PyannotePipeline, SpeakerSegment
from diarization.speaker_merger import SpeakerMerger

logger = structlog.get_logger()

# ── Prometheus metrics ──
diarization_segments_total = Counter(
    "diarization_segments_total",
    "Total speaker segments produced by diarization",
    ["stream_id"],
)
diarization_processing_seconds = Histogram(
    "diarization_processing_seconds",
    "Time spent running diarization on an audio window",
)

# ── Constants ─────────────────────────────────────────────────
ACCUMULATE_S: float = 3.0
"""Seconds of PCM to accumulate before triggering diarization."""

SAMPLE_RATE: int = 16_000
BYTES_PER_SAMPLE: int = 2
ACCUMULATE_BYTES: int = int(ACCUMULATE_S * SAMPLE_RATE * BYTES_PER_SAMPLE)
"""Number of PCM bytes corresponding to ``ACCUMULATE_S``."""

# ── Service singletons (set during lifespan) ──────────────────
_pipeline: PyannotePipeline | None = None
_redis: RedisClient | None = None
_mergers: dict[str, SpeakerMerger] = {}
# Latest segments per stream (shared between diarization and merger loops).
_latest_segments: dict[str, list[SpeakerSegment]] = {}


def _get_merger(stream_id: str) -> SpeakerMerger:
    """Return or create a ``SpeakerMerger`` for *stream_id*."""
    if stream_id not in _mergers:
        _mergers[stream_id] = SpeakerMerger()
    return _mergers[stream_id]


# ── Audio accumulation + diarization loop ────────────────────

async def _diarize_loop(
    stream_id: str,
    redis: RedisClient,
    pipeline: PyannotePipeline,
) -> None:
    """Accumulate 3 s of PCM from ``speech_chunks:{stream_id}``, diarize, publish."""
    stream_key = f"speech_chunks:{stream_id}"
    last_id = "0"
    buffer = bytearray()

    while True:
        try:
            entries = await redis.xread({stream_key: last_id}, count=50, block=500)
            for _stream, messages in entries:
                for msg_id, fields in messages:
                    last_id = msg_id
                    chunk = fields.get("data", b"")
                    if isinstance(chunk, str):
                        # Redis decode_responses may have mangled bytes;
                        # prefer binary transport in production.
                        chunk = chunk.encode("latin-1")
                    buffer.extend(chunk)

            if len(buffer) >= ACCUMULATE_BYTES:
                audio_bytes = bytes(buffer[:ACCUMULATE_BYTES])
                buffer = buffer[ACCUMULATE_BYTES:]

                segments = await pipeline.diarize(audio_bytes)

                # Store for the merger loop.
                _latest_segments[stream_id] = segments
                merger = _get_merger(stream_id)
                merger.update_segments(segments)

                # Publish segment events.
                for seg in segments:
                    await redis.publish(
                        f"diarization_events:{stream_id}",
                        {
                            "speaker_id": seg.speaker_id,
                            "start_ms": seg.start_ms,
                            "end_ms": seg.end_ms,
                        },
                    )
                logger.debug(
                    "diarization_complete",
                    stream_id=stream_id,
                    segments=len(segments),
                )

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("diarize_loop_error", stream_id=stream_id)
            await asyncio.sleep(1.0)


# ── Transcript token enrichment loop ─────────────────────────

async def _enrich_loop(
    stream_id: str,
    session_id: str,
    redis: RedisClient,
) -> None:
    """Read ``transcript_tokens:{stream_id}``, merge with diarization, publish."""
    stream_key = f"transcript_tokens:{stream_id}"
    last_id = "0"

    while True:
        try:
            entries = await redis.xread({stream_key: last_id}, count=10, block=1000)
            for _stream, messages in entries:
                for msg_id, fields in messages:
                    last_id = msg_id
                    try:
                        token_data: dict[str, Any] = json.loads(
                            fields.get("data", "{}")
                        )
                        merger = _get_merger(stream_id)
                        enriched_list = merger.merge([token_data])
                        for et in enriched_list:
                            await redis.xadd(
                                f"enriched_tokens:{stream_id}",
                                {
                                    "data": json.dumps({
                                        "text": et.text,
                                        "is_final": et.is_final,
                                        "start_ms": et.start_ms,
                                        "end_ms": et.end_ms,
                                        "confidence": et.confidence,
                                        "language": et.language,
                                        "speaker_id": et.speaker_id,
                                        "stream_id": stream_id,
                                        "session_id": session_id,
                                    }),
                                },
                            )
                    except Exception:
                        logger.exception(
                            "enrich_token_error",
                            stream_id=stream_id,
                            msg_id=msg_id,
                        )
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("enrich_loop_error", stream_id=stream_id)
            await asyncio.sleep(1.0)


# ── FastAPI lifespan ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the diarization model, connect Redis, then clean up."""
    global _pipeline, _redis

    logger.info("diarization_service_starting")

    _pipeline = PyannotePipeline()
    _pipeline.load()

    _redis = RedisClient()
    await _redis.connect()

    health.configure(_pipeline)

    logger.info("diarization_service_ready")
    yield

    logger.info("diarization_service_stopping")
    if _redis:
        await _redis.close()
    logger.info("diarization_service_stopped")


app = FastAPI(title="VoxSentinel Diarization Service", lifespan=lifespan)
app.include_router(health.router)
app.mount("/metrics", make_asgi_app())


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        log_level="info",
    )
