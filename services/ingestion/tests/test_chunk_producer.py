"""
Tests for the chunk producer module.

Verifies that PCM bytes are correctly buffered and yielded as
exactly 280 ms (8 960-byte) ``AudioChunk`` objects.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest

from ingestion.chunk_producer import (
    CHUNK_DURATION_MS,
    CHUNK_SIZE_BYTES,
    AudioChunk,
    produce_chunks,
)


# ── helpers ──


async def _bytes_gen(*blocks: bytes) -> AsyncIterator[bytes]:
    """Async generator yielding each *blocks* item."""
    for b in blocks:
        yield b


# ── tests ──


class TestChunkSizeConstants:
    """Verify chunk-size computation."""

    def test_chunk_size_bytes(self) -> None:
        """16000 Hz * 0.28 s * 2 bytes = 8960."""
        assert CHUNK_SIZE_BYTES == 8960

    def test_chunk_duration_ms(self) -> None:
        """Duration should be 280 ms."""
        assert CHUNK_DURATION_MS == 280


class TestAudioChunkModel:
    """AudioChunk Pydantic model validation."""

    def test_default_values(self) -> None:
        """Chunk should auto-generate chunk_id and timestamp."""
        chunk = AudioChunk(
            stream_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            pcm_bytes=b"\x00" * CHUNK_SIZE_BYTES,
        )
        assert chunk.chunk_id is not None
        assert chunk.timestamp is not None
        assert chunk.duration_ms == 280

    def test_pcm_bytes_is_required(self) -> None:
        """pcm_bytes is mandatory."""
        with pytest.raises(Exception):
            AudioChunk(stream_id=uuid.uuid4(), session_id=uuid.uuid4())  # type: ignore[call-arg]


class TestProduceChunks:
    """Test the produce_chunks async generator."""

    @pytest.mark.asyncio
    async def test_exact_one_chunk(self, stream_id: uuid.UUID, session_id: uuid.UUID) -> None:
        """Feeding exactly 8960 bytes yields one chunk."""
        pcm = b"\x01" * CHUNK_SIZE_BYTES
        gen = _bytes_gen(pcm)

        chunks: list[AudioChunk] = []
        async for c in produce_chunks(gen, stream_id=stream_id, session_id=session_id):
            chunks.append(c)

        assert len(chunks) == 1
        assert len(chunks[0].pcm_bytes) == CHUNK_SIZE_BYTES
        assert chunks[0].stream_id == stream_id
        assert chunks[0].session_id == session_id
        assert chunks[0].duration_ms == 280

    @pytest.mark.asyncio
    async def test_two_chunks_from_double_data(
        self, stream_id: uuid.UUID, session_id: uuid.UUID
    ) -> None:
        """Feeding 2 × 8960 bytes yields two chunks."""
        pcm = b"\x02" * (CHUNK_SIZE_BYTES * 2)
        gen = _bytes_gen(pcm)

        chunks: list[AudioChunk] = []
        async for c in produce_chunks(gen, stream_id=stream_id, session_id=session_id):
            chunks.append(c)

        assert len(chunks) == 2
        for c in chunks:
            assert len(c.pcm_bytes) == CHUNK_SIZE_BYTES

    @pytest.mark.asyncio
    async def test_trailing_bytes_discarded(
        self, stream_id: uuid.UUID, session_id: uuid.UUID
    ) -> None:
        """Bytes less than a full chunk at stream end are discarded."""
        pcm = b"\x03" * (CHUNK_SIZE_BYTES + 100)
        gen = _bytes_gen(pcm)

        chunks: list[AudioChunk] = []
        async for c in produce_chunks(gen, stream_id=stream_id, session_id=session_id):
            chunks.append(c)

        assert len(chunks) == 1
        assert len(chunks[0].pcm_bytes) == CHUNK_SIZE_BYTES

    @pytest.mark.asyncio
    async def test_small_fragments_accumulated(
        self, stream_id: uuid.UUID, session_id: uuid.UUID
    ) -> None:
        """Many small blocks should accumulate into full chunks."""
        fragment_size = 1000  # 9 fragments = 9000 bytes → 1 chunk (8960) + 40 leftover
        fragments = [b"\x04" * fragment_size for _ in range(9)]
        gen = _bytes_gen(*fragments)

        chunks: list[AudioChunk] = []
        async for c in produce_chunks(gen, stream_id=stream_id, session_id=session_id):
            chunks.append(c)

        assert len(chunks) == 1
        assert len(chunks[0].pcm_bytes) == CHUNK_SIZE_BYTES

    @pytest.mark.asyncio
    async def test_empty_stream(self, stream_id: uuid.UUID, session_id: uuid.UUID) -> None:
        """An empty source yields no chunks."""
        gen = _bytes_gen()

        chunks: list[AudioChunk] = []
        async for c in produce_chunks(gen, stream_id=stream_id, session_id=session_id):
            chunks.append(c)

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_ids_are_unique(
        self, stream_id: uuid.UUID, session_id: uuid.UUID
    ) -> None:
        """Each chunk should get a unique chunk_id."""
        pcm = b"\x05" * (CHUNK_SIZE_BYTES * 3)
        gen = _bytes_gen(pcm)

        ids: list[uuid.UUID] = []
        async for c in produce_chunks(gen, stream_id=stream_id, session_id=session_id):
            ids.append(c.chunk_id)

        assert len(ids) == 3
        assert len(set(ids)) == 3  # all unique
