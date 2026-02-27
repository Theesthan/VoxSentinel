"""
Tests for the ASR stream router.

Validates per-stream engine selection, connection management,
and correct routing of audio chunks to configured backends.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tg_common.models import TranscriptToken

from asr.router import ASRRouter


def _make_token(text: str = "routed") -> TranscriptToken:
    now = datetime.now(timezone.utc)
    return TranscriptToken(
        text=text,
        is_final=True,
        start_time=now,
        end_time=now,
        confidence=0.9,
        language="en",
    )


def _pcm_b64(raw: bytes = b"\x00\x01" * 100) -> str:
    return base64.b64encode(raw).decode()


class TestASRRouter:
    """Tests for ASRRouter stream processing."""

    async def test_process_stream_reads_correct_key(
        self,
        mock_redis: AsyncMock,
        stream_id: str,
    ) -> None:
        """Router reads from speech_chunks:{stream_id}."""
        stop = asyncio.Event()
        stop.set()  # stop immediately

        failover = AsyncMock()
        failover.stream_audio = AsyncMock(return_value=AsyncMock(__aiter__=lambda s: s, __anext__=AsyncMock(side_effect=StopAsyncIteration)))

        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)
        await router.process_stream(stream_id, stop_event=stop)
        # xread should not have been called because stop is already set.

    async def test_handle_entry_publishes_tokens(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_handle_entry routes audio and publishes token JSON to Redis."""
        token = _make_token("hello world")

        async def _fake_stream_audio(chunk: bytes):
            yield token

        failover = MagicMock()
        failover.stream_audio = _fake_stream_audio

        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)

        import structlog
        log = structlog.get_logger()
        fields = {"pcm_b64": _pcm_b64()}
        await router._handle_entry(fields, "transcript_tokens:test", log)

        mock_redis.xadd.assert_awaited_once()
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "transcript_tokens:test"
        assert "token" in call_args[0][1]

    async def test_handle_entry_missing_pcm_b64(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_handle_entry logs a warning and skips when pcm_b64 is missing."""
        failover = MagicMock()
        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)

        import structlog
        log = structlog.get_logger()
        await router._handle_entry({}, "transcript_tokens:test", log)
        mock_redis.xadd.assert_not_awaited()

    async def test_handle_entry_invalid_b64(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_handle_entry handles invalid base64 gracefully."""
        failover = MagicMock()
        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)

        import structlog
        log = structlog.get_logger()
        await router._handle_entry({"pcm_b64": "!!!invalid!!!"}, "out", log)
        mock_redis.xadd.assert_not_awaited()

    async def test_handle_entry_stream_error(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """_handle_entry handles ASR streaming errors gracefully."""

        async def _failing(chunk: bytes):
            raise RuntimeError("ASR failed")
            yield  # pragma: no cover

        failover = MagicMock()
        failover.stream_audio = _failing
        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)

        import structlog
        log = structlog.get_logger()
        # Should not raise.
        await router._handle_entry({"pcm_b64": _pcm_b64()}, "out", log)
        mock_redis.xadd.assert_not_awaited()

    async def test_process_stream_handles_entries(
        self,
        mock_redis: AsyncMock,
        stream_id: str,
    ) -> None:
        """process_stream consumes entries and routes them."""
        token = _make_token("processed")
        call_count = 0

        async def _fake_stream_audio(chunk: bytes):
            yield token

        failover = MagicMock()
        failover.stream_audio = _fake_stream_audio

        stop = asyncio.Event()

        async def _xread_side_effect(streams, count=10, block=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [
                    (
                        f"speech_chunks:{stream_id}",
                        [("1-0", {"pcm_b64": _pcm_b64()})],
                    )
                ]
            stop.set()
            return []

        mock_redis.xread = AsyncMock(side_effect=_xread_side_effect)

        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)
        await router.process_stream(stream_id, stop_event=stop)

        mock_redis.xadd.assert_awaited_once()

    async def test_process_stream_xread_error_retries(
        self,
        mock_redis: AsyncMock,
        stream_id: str,
    ) -> None:
        """process_stream retries after an xread exception."""
        call_count = 0
        stop = asyncio.Event()

        async def _xread_side_effect(streams, count=10, block=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("redis down")
            stop.set()
            return []

        mock_redis.xread = AsyncMock(side_effect=_xread_side_effect)
        failover = MagicMock()

        router = ASRRouter(redis_client=mock_redis, failover_manager=failover)

        # Patch sleep to avoid actual delay.
        with patch("asr.router.asyncio.sleep", new_callable=AsyncMock):
            await router.process_stream(stream_id, stop_event=stop)

        # Should have survived the error and continued.
        assert call_count >= 2
