"""Tests for diarization.main module (lifespan, loops, app wiring)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from diarization.pyannote_pipeline import SpeakerSegment
from diarization.main import (
    ACCUMULATE_BYTES,
    ACCUMULATE_S,
    _diarize_loop,
    _enrich_loop,
    _get_merger,
    _mergers,
    _latest_segments,
    app,
)


# ── TestConstants ────────────────────────────────────────────

class TestConstants:
    def test_accumulate_bytes_matches_3_seconds(self) -> None:
        expected = int(3.0 * 16_000 * 2)
        assert ACCUMULATE_BYTES == expected

    def test_accumulate_s(self) -> None:
        assert ACCUMULATE_S == 3.0


# ── TestGetMerger ────────────────────────────────────────────

class TestGetMerger:
    def test_creates_new_merger(self) -> None:
        _mergers.clear()
        m = _get_merger("stream-test-1")
        assert m is not None

    def test_returns_same_instance(self) -> None:
        _mergers.clear()
        m1 = _get_merger("stream-test-2")
        m2 = _get_merger("stream-test-2")
        assert m1 is m2


# ── TestDiarizeLoop ──────────────────────────────────────────

class TestDiarizeLoop:
    @pytest.mark.asyncio
    async def test_accumulates_and_diarizes(self, mock_redis: AsyncMock) -> None:
        """Feed enough bytes to trigger one diarization call."""
        # Each chunk is half the required buffer; 2 chunks = 1 full window.
        half = ACCUMULATE_BYTES // 2
        chunk = b"\x00" * half
        call_count = 0

        async def fake_xread(streams, count=10, block=500):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return [(
                    f"speech_chunks:s1",
                    [
                        (f"{call_count}-0", {"data": chunk}),
                    ],
                )]
            # After we've sent enough, raise cancel to exit loop
            raise asyncio.CancelledError

        mock_redis.xread = AsyncMock(side_effect=fake_xread)

        pipeline = MagicMock()
        pipeline.diarize = AsyncMock(return_value=[
            SpeakerSegment("SPEAKER_00", 0, 1500),
            SpeakerSegment("SPEAKER_01", 1500, 3000),
        ])

        # CancelledError is caught inside the loop (break), so it returns normally.
        await _diarize_loop("s1", mock_redis, pipeline)

        # Pipeline should have been called once with accumulated bytes
        pipeline.diarize.assert_called_once()
        assert mock_redis.publish.call_count == 2  # 2 segments published

    @pytest.mark.asyncio
    async def test_skips_when_not_enough_data(self, mock_redis: AsyncMock) -> None:
        """If not enough bytes accumulated, no diarization runs."""
        small_chunk = b"\x00" * 100

        call_count = 0

        async def fake_xread(streams, count=10, block=500):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("speech_chunks:s1", [("1-0", {"data": small_chunk})])]
            raise asyncio.CancelledError

        mock_redis.xread = AsyncMock(side_effect=fake_xread)

        pipeline = MagicMock()
        pipeline.diarize = AsyncMock()

        # CancelledError is caught inside the loop (break), so it returns normally.
        await _diarize_loop("s1", mock_redis, pipeline)

        pipeline.diarize.assert_not_called()


# ── TestEnrichLoop ───────────────────────────────────────────

class TestEnrichLoop:
    @pytest.mark.asyncio
    async def test_enriches_and_publishes(self, mock_redis: AsyncMock) -> None:
        """Token read from stream is enriched with speaker and re-published."""
        _mergers.clear()
        merger = _get_merger("s1")
        merger.update_segments([SpeakerSegment("SPEAKER_00", 0, 5000)])

        token_data = {
            "text": "hello world",
            "is_final": True,
            "start_ms": 100,
            "end_ms": 200,
            "confidence": 0.9,
            "language": "en",
        }

        call_count = 0

        async def fake_xread(streams, count=10, block=1000):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(
                    "transcript_tokens:s1",
                    [("1-0", {"data": json.dumps(token_data)})],
                )]
            raise asyncio.CancelledError

        mock_redis.xread = AsyncMock(side_effect=fake_xread)

        # CancelledError is caught inside the loop (break), returns normally.
        await _enrich_loop("s1", "sess1", mock_redis)

        # Should have published to enriched_tokens:s1
        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == "enriched_tokens:s1"
        published = json.loads(call_args[0][1]["data"])
        assert published["speaker_id"] == "SPEAKER_00"
        assert published["text"] == "hello world"


# ── TestAppSetup ─────────────────────────────────────────────

class TestAppSetup:
    def test_app_has_health_route(self) -> None:
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_app_title(self) -> None:
        assert "Diarization" in app.title


# ── import asyncio for CancelledError ────────────────────────
import asyncio  # noqa: E402
