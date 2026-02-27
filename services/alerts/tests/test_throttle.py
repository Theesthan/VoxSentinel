"""
Tests for the alert throttle module.

Validates rate limiting enforcement, deduplication window handling,
and overflow logging behavior.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from alerts.throttle import AlertThrottle


# ── deduplication ──


class TestDeduplication:
    """Tests for the dedup TTL-key mechanism."""

    async def test_first_occurrence_is_not_duplicate(self, mock_redis, stream_id) -> None:
        mock_redis.set = AsyncMock(return_value=True)  # NX succeeded → new key
        throttle = AlertThrottle(mock_redis)
        assert await throttle.is_duplicate(stream_id, "gun", "exact") is False

    async def test_second_occurrence_within_ttl_is_duplicate(
        self, mock_redis, stream_id
    ) -> None:
        mock_redis.set = AsyncMock(return_value=None)  # NX failed → already exists
        throttle = AlertThrottle(mock_redis)
        assert await throttle.is_duplicate(stream_id, "gun", "exact") is True

    async def test_dedup_key_format(self, mock_redis, stream_id) -> None:
        mock_redis.set = AsyncMock(return_value=True)
        throttle = AlertThrottle(mock_redis)
        await throttle.is_duplicate(stream_id, "bomb", "fuzzy")
        key = mock_redis.set.call_args[0][0]
        assert key == f"dedup:{stream_id}:bomb:fuzzy"

    async def test_dedup_uses_configured_ttl(self, mock_redis, stream_id) -> None:
        mock_redis.set = AsyncMock(return_value=True)
        throttle = AlertThrottle(mock_redis, dedup_ttl_s=30)
        await throttle.is_duplicate(stream_id, "test", "exact")
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 30

    async def test_dedup_default_ttl_is_10(self, mock_redis, stream_id) -> None:
        mock_redis.set = AsyncMock(return_value=True)
        throttle = AlertThrottle(mock_redis)
        await throttle.is_duplicate(stream_id, "test", "exact")
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 10

    async def test_different_keywords_are_independent(
        self, mock_redis, stream_id
    ) -> None:
        call_count = 0

        async def _set_side_effect(key, val, **kw):
            return True  # always new

        mock_redis.set = AsyncMock(side_effect=_set_side_effect)
        throttle = AlertThrottle(mock_redis)
        assert await throttle.is_duplicate(stream_id, "gun", "exact") is False
        assert await throttle.is_duplicate(stream_id, "bomb", "exact") is False


# ── rate limiting ──


class TestRateLimiting:
    """Tests for the sliding-window sorted-set rate limiter."""

    async def test_under_limit_is_not_throttled(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[0, 5])  # 5 alerts in window
        throttle = AlertThrottle(mock_redis, max_per_minute=30)
        assert await throttle.is_throttled(stream_id) is False

    async def test_at_limit_is_throttled(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[0, 30])  # exactly at limit
        throttle = AlertThrottle(mock_redis, max_per_minute=30)
        assert await throttle.is_throttled(stream_id) is True

    async def test_over_limit_is_throttled(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[0, 50])
        throttle = AlertThrottle(mock_redis, max_per_minute=30)
        assert await throttle.is_throttled(stream_id) is True

    async def test_custom_max_per_minute(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[0, 10])
        throttle = AlertThrottle(mock_redis, max_per_minute=10)
        assert await throttle.is_throttled(stream_id) is True

    async def test_throttle_key_format(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[0, 0])
        throttle = AlertThrottle(mock_redis)
        await throttle.is_throttled(stream_id)
        pipe.zremrangebyscore.assert_called_once()
        key = pipe.zremrangebyscore.call_args[0][0]
        assert key == f"throttle:{stream_id}"


# ── record ──


class TestRecord:
    """Tests for recording dispatched alerts."""

    async def test_record_adds_entry_to_sorted_set(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[1, True])
        throttle = AlertThrottle(mock_redis)
        await throttle.record(stream_id)
        pipe.zadd.assert_called_once()

    async def test_record_sets_ttl_on_key(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[1, True])
        throttle = AlertThrottle(mock_redis)
        await throttle.record(stream_id)
        pipe.expire.assert_called_once()
        assert pipe.expire.call_args[0][1] == 120

    async def test_record_key_format(self, mock_redis, stream_id) -> None:
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[1, True])
        throttle = AlertThrottle(mock_redis)
        await throttle.record(stream_id)
        key = pipe.zadd.call_args[0][0]
        assert key == f"throttle:{stream_id}"

