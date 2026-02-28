"""
Tests for tg-common Redis client.

Validates the ``RedisClient`` wrapper using a mocked ``redis.asyncio`` backend,
covering connect, close, publish, subscribe, xadd, xread, and health_check.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tg_common.messaging.redis_client import RedisClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """Return a fully-mocked ``aioredis.Redis`` instance."""
    r = AsyncMock()
    r.publish = AsyncMock(return_value=1)
    r.ping = AsyncMock(return_value=True)
    r.xadd = AsyncMock(return_value="1234567890-0")
    r.xread = AsyncMock(return_value=[])
    r.close = AsyncMock()
    # pubsub mock
    ps = AsyncMock()
    ps.subscribe = AsyncMock()
    ps.close = AsyncMock()
    r.pubsub = MagicMock(return_value=ps)
    return r


@pytest.fixture()
def client(mock_redis: AsyncMock) -> RedisClient:
    """Return a ``RedisClient`` with the internal connection pre-set."""
    c = RedisClient(url="redis://localhost:6379/0")
    c._redis = mock_redis
    return c


# ---------------------------------------------------------------------------
# Tests: lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:

    @pytest.mark.asyncio
    async def test_connect_creates_redis(self) -> None:
        with patch("tg_common.messaging.redis_client.aioredis.from_url") as mock_from:
            mock_from.return_value = AsyncMock()
            c = RedisClient(url="redis://localhost:6379/0")
            await c.connect()
            mock_from.assert_called_once()
            assert c._redis is not None

    @pytest.mark.asyncio
    async def test_connect_idempotent(self) -> None:
        with patch("tg_common.messaging.redis_client.aioredis.from_url") as mock_from:
            mock_from.return_value = AsyncMock()
            c = RedisClient(url="redis://localhost:6379/0")
            await c.connect()
            await c.connect()
            mock_from.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        await client.close()
        mock_redis.close.assert_awaited_once()
        assert client._redis is None

    def test_redis_property_raises_when_not_connected(self) -> None:
        c = RedisClient(url="redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="not connected"):
            _ = c.redis


# ---------------------------------------------------------------------------
# Tests: publish / subscribe
# ---------------------------------------------------------------------------


class TestPubSub:

    @pytest.mark.asyncio
    async def test_publish_dict(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        result = await client.publish("ch", {"key": "val"})
        assert result == 1
        mock_redis.publish.assert_awaited_once()
        args = mock_redis.publish.call_args
        assert args[0][0] == "ch"
        assert '"key"' in args[0][1]  # JSON serialised

    @pytest.mark.asyncio
    async def test_publish_string(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        await client.publish("ch", "plain text")
        mock_redis.publish.assert_awaited_once_with("ch", "plain text")

    @pytest.mark.asyncio
    async def test_subscribe(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        ps = await client.subscribe("alerts", "events")
        mock_redis.pubsub.assert_called_once()
        ps.subscribe.assert_awaited_once_with("alerts", "events")


# ---------------------------------------------------------------------------
# Tests: streams (xadd / xread)
# ---------------------------------------------------------------------------


class TestStreams:

    @pytest.mark.asyncio
    async def test_xadd(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        entry_id = await client.xadd("mystream", {"f": "v"})
        assert entry_id == "1234567890-0"
        mock_redis.xadd.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_xadd_with_maxlen(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        await client.xadd("s", {"a": "b"}, maxlen=1000)
        _, kwargs = mock_redis.xadd.call_args
        assert kwargs["maxlen"] == 1000

    @pytest.mark.asyncio
    async def test_xread(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        result = await client.xread({"mystream": "0"}, count=5)
        assert result == []
        mock_redis.xread.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: health check
# ---------------------------------------------------------------------------


class TestHealthCheck:

    @pytest.mark.asyncio
    async def test_healthy(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        assert await client.health_check() is True
        mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unhealthy(self, client: RedisClient, mock_redis: AsyncMock) -> None:
        mock_redis.ping.side_effect = ConnectionError("down")
        assert await client.health_check() is False
