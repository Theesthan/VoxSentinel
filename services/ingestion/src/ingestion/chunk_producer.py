"""
Audio chunk producer for VoxSentinel ingestion service.

Buffers raw 16 kHz mono s16 PCM bytes and yields exactly 280 ms
chunks as ``AudioChunk`` Pydantic models.  Each chunk is
16000 Hz × 0.28 s × 2 bytes/sample = 8 960 bytes.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger()

# 16 kHz × 0.28 s × 2 bytes = 8960 bytes per chunk
SAMPLE_RATE: int = 16_000
CHUNK_DURATION_S: float = 0.28
CHUNK_SIZE_BYTES: int = int(SAMPLE_RATE * CHUNK_DURATION_S * 2)  # 8960
CHUNK_DURATION_MS: int = int(CHUNK_DURATION_S * 1000)  # 280


class AudioChunk(BaseModel):
    """A single timestamped PCM audio chunk.

    Attributes:
        chunk_id: Unique identifier for this chunk.
        stream_id: Parent stream UUID.
        session_id: Parent session UUID.
        pcm_bytes: Raw 16 kHz mono s16 PCM audio data.
        timestamp: UTC timestamp when the chunk was produced.
        duration_ms: Duration of the audio in milliseconds.
    """

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}

    chunk_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique chunk identifier.")
    stream_id: uuid.UUID = Field(..., description="Parent stream UUID.")
    session_id: uuid.UUID = Field(..., description="Parent session UUID.")
    pcm_bytes: bytes = Field(..., description="Raw 16 kHz mono s16 PCM audio data.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of chunk production.",
    )
    duration_ms: int = Field(default=CHUNK_DURATION_MS, description="Audio duration in ms.")


async def produce_chunks(
    pcm_stream: AsyncIterator[bytes],
    *,
    stream_id: uuid.UUID,
    session_id: uuid.UUID,
) -> AsyncIterator[AudioChunk]:
    """Buffer PCM bytes from *pcm_stream* and yield fixed-size ``AudioChunk`` objects.

    The producer accumulates incoming PCM bytes until exactly
    ``CHUNK_SIZE_BYTES`` (8 960) are available, then yields an
    ``AudioChunk``.  Any trailing bytes smaller than a full chunk
    are discarded when the source stream ends.

    Args:
        pcm_stream: Async iterator yielding raw PCM byte blocks.
        stream_id: Stream UUID to stamp on every chunk.
        session_id: Session UUID to stamp on every chunk.

    Yields:
        ``AudioChunk`` objects of exactly ``CHUNK_SIZE_BYTES``.
    """
    log = logger.bind(stream_id=str(stream_id), session_id=str(session_id))
    buffer = bytearray()

    async for pcm_bytes in pcm_stream:
        buffer.extend(pcm_bytes)

        while len(buffer) >= CHUNK_SIZE_BYTES:
            chunk_data = bytes(buffer[:CHUNK_SIZE_BYTES])
            del buffer[:CHUNK_SIZE_BYTES]

            chunk = AudioChunk(
                stream_id=stream_id,
                session_id=session_id,
                pcm_bytes=chunk_data,
            )
            log.debug("chunk_produced", chunk_id=str(chunk.chunk_id), size=len(chunk_data))
            yield chunk

    if buffer:
        log.debug("chunk_producer_trailing_bytes_discarded", bytes_discarded=len(buffer))
