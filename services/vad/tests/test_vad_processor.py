"""
Tests for ``vad.vad_processor.VADProcessor``.

Covers chunk classification routing, speech-ratio metric emission,
stop-event handling, and error resilience.
"""

from __future__ import annotations

import asyncio
import base64
import struct
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vad.vad_processor import VADProcessor, VAD_SPEECH_RATIO, _METRIC_WINDOW_S


# ── helpers ──

def _make_pcm_b64(n_samples: int = 160, amplitude: int = 1000) -> str:
    """Return a base64-encoded 16-bit LE PCM payload."""
    raw = struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))
    return base64.b64encode(raw).decode()


def _make_xread_result(
    stream_key: str,
    fields: dict[str, str],
    entry_id: str = "1-0",
) -> list:
    """Mimic the return value of ``RedisClient.xread``."""
    return [(stream_key, [(entry_id, fields)])]


# ── tests ──


class TestHandleChunk:
    """Low-level _handle_chunk behaviour."""

    @pytest.mark.asyncio
    async def test_speech_chunk_forwarded(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """Chunks with score >= threshold are xadd-ed to speech_chunks."""
        mock_vad_model.classify = AsyncMock(return_value=0.85)
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        fields = {"pcm_b64": _make_pcm_b64(), "chunk_id": "c1"}
        await proc._handle_chunk(fields, "s1", "speech_chunks:s1", MagicMock())

        mock_redis.xadd.assert_awaited_once()
        args = mock_redis.xadd.call_args
        assert args[0][0] == "speech_chunks:s1"
        assert args[0][1] == fields

    @pytest.mark.asyncio
    async def test_non_speech_chunk_dropped(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """Chunks with score < threshold are NOT forwarded."""
        mock_vad_model.classify = AsyncMock(return_value=0.2)
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        fields = {"pcm_b64": _make_pcm_b64(), "chunk_id": "c1"}
        await proc._handle_chunk(fields, "s1", "speech_chunks:s1", MagicMock())

        mock_redis.xadd.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_pcm_b64_skipped(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """Fields missing ``pcm_b64`` are logged and skipped."""
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        await proc._handle_chunk({}, "s1", "speech_chunks:s1", MagicMock())

        mock_vad_model.classify.assert_not_awaited()
        mock_redis.xadd.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_boundary_score_is_speech(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """A score of exactly the threshold should be classified as speech."""
        mock_vad_model.classify = AsyncMock(return_value=0.5)
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        fields = {"pcm_b64": _make_pcm_b64()}
        await proc._handle_chunk(fields, "s1", "speech_chunks:s1", MagicMock())

        mock_redis.xadd.assert_awaited_once()


class TestWindowCounters:
    """Per-stream speech/total counters and metric gauge."""

    @pytest.mark.asyncio
    async def test_counters_updated_on_speech(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        mock_vad_model.classify = AsyncMock(return_value=0.9)
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        fields = {"pcm_b64": _make_pcm_b64()}
        await proc._handle_chunk(fields, "s1", "speech_chunks:s1", MagicMock())

        assert proc._window_total["s1"] == 1
        assert proc._window_speech["s1"] == 1

    @pytest.mark.asyncio
    async def test_counters_updated_on_non_speech(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        mock_vad_model.classify = AsyncMock(return_value=0.1)
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        fields = {"pcm_b64": _make_pcm_b64()}
        await proc._handle_chunk(fields, "s1", "speech_chunks:s1", MagicMock())

        assert proc._window_total["s1"] == 1
        assert proc._window_speech.get("s1", 0) == 0


class TestMaybeFlushMetrics:
    """``_maybe_flush_metrics`` fires after the 60 s window."""

    def test_no_flush_before_window(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)
        proc._window_total["s1"] = 10
        proc._window_speech["s1"] = 7

        proc._maybe_flush_metrics()

        # Window hasn't elapsed → counters untouched.
        assert proc._window_total["s1"] == 10

    def test_flush_after_window(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)
        proc._window_total["s1"] = 10
        proc._window_speech["s1"] = 7
        proc._window_start = time.monotonic() - 61  # past the 60 s window

        proc._maybe_flush_metrics()

        # Counters should be cleared after flush.
        assert proc._window_total == {}
        assert proc._window_speech == {}

    def test_gauge_set_correctly(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """After flush the gauge should reflect speech / total ratio."""
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)
        proc._window_total["s1"] = 100
        proc._window_speech["s1"] = 75
        proc._window_start = time.monotonic() - 61

        proc._maybe_flush_metrics()

        # Retrieve the gauge value.
        sample = VAD_SPEECH_RATIO.labels(stream_id="s1")._value.get()
        assert sample == pytest.approx(0.75, abs=0.01)


class TestProcessStreamLoop:
    """Integration-level tests for the xread loop in ``process_stream``."""

    @pytest.mark.asyncio
    async def test_stop_event_terminates_loop(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """Setting stop_event exits the loop quickly."""
        mock_redis.xread = AsyncMock(return_value=[])

        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)
        stop = asyncio.Event()
        stop.set()  # already set → should exit immediately

        await asyncio.wait_for(
            proc.process_stream("s1", stop_event=stop), timeout=2.0,
        )

    @pytest.mark.asyncio
    async def test_xread_error_retries(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """xread failure logs the error and sleeps for 1 s before retry."""
        call_count = 0
        stop = asyncio.Event()

        async def _failing_xread(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("boom")
            stop.set()
            return []

        mock_redis.xread = _failing_xread
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        with patch("vad.vad_processor.asyncio.sleep", new_callable=AsyncMock):
            await asyncio.wait_for(
                proc.process_stream("s1", stop_event=stop), timeout=5.0,
            )

        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_chunks_forwarded_in_loop(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        """Full loop: xread returns data → _handle_chunk → xadd."""
        stop = asyncio.Event()
        call_count = 0

        pcm_fields = {"pcm_b64": _make_pcm_b64(), "chunk_id": "c1"}

        async def _xread(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_xread_result("audio_chunks:s1", pcm_fields)
            stop.set()
            return []

        mock_redis.xread = _xread
        mock_vad_model.classify = AsyncMock(return_value=0.9)
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.5)

        await asyncio.wait_for(
            proc.process_stream("s1", stop_event=stop), timeout=5.0,
        )

        mock_redis.xadd.assert_awaited_once()


class TestThresholdDefault:
    """Threshold falls back to ``get_settings().vad_threshold``."""

    def test_default_threshold_from_settings(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        proc = VADProcessor(mock_vad_model, mock_redis)
        assert proc._threshold == 0.5  # from TG_VAD_THRESHOLD env var

    def test_explicit_threshold_overrides(
        self, mock_redis: AsyncMock, mock_vad_model: MagicMock,
    ) -> None:
        proc = VADProcessor(mock_vad_model, mock_redis, threshold=0.7)
        assert proc._threshold == 0.7
