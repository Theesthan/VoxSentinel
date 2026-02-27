"""
Tests for the stream manager module.

Validates stream start/stop lifecycle, concurrent stream handling,
chunk publishing to Redis, and Prometheus metric counters.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tg_common.models.stream import SourceType, Stream, StreamStatus

from ingestion.stream_manager import StreamManager


def _make_stream(
    stream_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
) -> Stream:
    """Build a test Stream model."""
    return Stream(
        stream_id=stream_id or uuid.uuid4(),
        name="Test Stream",
        source_type=SourceType.FILE,
        source_url="file:///test.wav",
        status=StreamStatus.ACTIVE,
        session_id=session_id or uuid.uuid4(),
    )


class TestStreamManagerLifecycle:
    """Start / stop / stop_all semantics."""

    @pytest.mark.asyncio
    async def test_start_stream_creates_task(self, mock_redis: AsyncMock) -> None:
        """start_stream should create an asyncio task."""
        mgr = StreamManager(mock_redis)
        stream = _make_stream()

        with patch("ingestion.stream_manager.extract_audio") as mock_extract:
            # Make the pipeline end immediately — empty async gen.
            async def _empty_gen(*a, **kw):  # type: ignore[no-untyped-def]
                return
                yield  # noqa: unreachable — makes it an async gen  # type: ignore[misc]

            mock_extract.return_value = _empty_gen()

            await mgr.start_stream(stream)
            await asyncio.sleep(0.05)  # let task spin up

        sid = str(stream.stream_id)
        assert sid in mgr._tasks

    @pytest.mark.asyncio
    async def test_stop_stream(self, mock_redis: AsyncMock) -> None:
        """stop_stream should cancel the running task."""
        mgr = StreamManager(mock_redis)
        stream = _make_stream()

        with patch("ingestion.stream_manager.extract_audio") as mock_extract:
            async def _slow_gen(*a, **kw):  # type: ignore[no-untyped-def]
                while True:
                    await asyncio.sleep(10)
                    yield b""

            mock_extract.return_value = _slow_gen()
            await mgr.start_stream(stream)
            await asyncio.sleep(0.05)

            await mgr.stop_stream(stream.stream_id)

        sid = str(stream.stream_id)
        assert sid not in mgr._tasks

    @pytest.mark.asyncio
    async def test_stop_all(self, mock_redis: AsyncMock) -> None:
        """stop_all should cancel every running task."""
        mgr = StreamManager(mock_redis)

        async def _slow_gen(*a, **kw):  # type: ignore[no-untyped-def]
            while True:
                await asyncio.sleep(10)
                yield b""

        with patch("ingestion.stream_manager.extract_audio", side_effect=lambda *a, **kw: _slow_gen()):
            await mgr.start_stream(_make_stream())
            await mgr.start_stream(_make_stream())
            await asyncio.sleep(0.05)

            assert len(mgr.active_streams) == 2
            await mgr.stop_all()

        assert len(mgr.active_streams) == 0

    @pytest.mark.asyncio
    async def test_start_same_stream_twice_is_noop(self, mock_redis: AsyncMock) -> None:
        """Starting an already-running stream should not create a second task."""
        mgr = StreamManager(mock_redis)
        stream = _make_stream()

        async def _slow_gen(*a, **kw):  # type: ignore[no-untyped-def]
            while True:
                await asyncio.sleep(10)
                yield b""

        with patch("ingestion.stream_manager.extract_audio", return_value=_slow_gen()):
            await mgr.start_stream(stream)
            await asyncio.sleep(0.05)

            await mgr.start_stream(stream)  # should be no-op
            assert len(mgr.active_streams) == 1
            await mgr.stop_all()


class TestStreamManagerPublish:
    """Chunk publishing to Redis."""

    @pytest.mark.asyncio
    async def test_chunks_published_via_xadd(self, mock_redis: AsyncMock) -> None:
        """Each produced chunk should be published to Redis."""
        mgr = StreamManager(mock_redis)
        stream = _make_stream()
        sid = str(stream.stream_id)

        # Build a fake audio extractor yielding exactly one chunk worth of bytes.
        pcm_data = b"\x00" * 8960  # one 280ms chunk

        async def _pcm_gen(*a, **kw):  # type: ignore[no-untyped-def]
            yield pcm_data

        with patch("ingestion.stream_manager.extract_audio", return_value=_pcm_gen()):
            await mgr.start_stream(stream)
            await asyncio.sleep(0.2)  # let pipeline process

        # xadd should have been called at least once.
        assert mock_redis.xadd.await_count >= 1

        # Inspect the first call's redis key argument.
        call_args = mock_redis.xadd.call_args_list[0]
        redis_key = call_args.args[0] if call_args.args else call_args.kwargs.get("stream")
        assert redis_key == f"audio_chunks:{sid}"

        await mgr.stop_all()
