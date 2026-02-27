"""
Redis client wrapper for VoxSentinel.

Provides an async Redis client for pub/sub messaging, stream (XADD/XREAD)
operations, and general key–value access.  Handles connection pooling and
reconnection transparently.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from tg_common.config import get_settings


class RedisClient:
    """Async Redis wrapper with publish, subscribe, xadd, and xread helpers.

    Args:
        url: Redis connection URL.  Falls back to ``Settings.redis_url``.
    """

    def __init__(self, url: str | None = None) -> None:
        self._url = url or get_settings().redis_url
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None

    # ── lifecycle ──

    async def connect(self) -> None:
        """Establish the Redis connection (idempotent)."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._url,
                decode_responses=True,
            )

    async def close(self) -> None:
        """Close the Redis connection and pubsub, if open."""
        if self._pubsub is not None:
            await self._pubsub.close()
            self._pubsub = None
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    @property
    def redis(self) -> aioredis.Redis:
        """Return the underlying ``aioredis.Redis`` instance.

        Raises:
            RuntimeError: If ``connect()`` has not been called.
        """
        if self._redis is None:
            raise RuntimeError("RedisClient is not connected. Call connect() first.")
        return self._redis

    # ── pub/sub helpers ──

    async def publish(self, channel: str, message: dict[str, Any] | str) -> int:
        """Publish a message to a Redis pub/sub *channel*.

        Args:
            channel: Channel name.
            message: Message payload (dict is JSON-serialised automatically).

        Returns:
            Number of subscribers that received the message.
        """
        payload = json.dumps(message) if isinstance(message, dict) else message
        result: int = await self.redis.publish(channel, payload)
        return result

    async def subscribe(self, *channels: str) -> aioredis.client.PubSub:
        """Subscribe to one or more pub/sub *channels*.

        Args:
            channels: Channel names to subscribe to.

        Returns:
            A ``PubSub`` instance that can be iterated for incoming messages.
        """
        self._pubsub = self.redis.pubsub()
        await self._pubsub.subscribe(*channels)
        return self._pubsub

    # ── stream (XADD / XREAD) helpers ──

    async def xadd(
        self,
        stream: str,
        fields: dict[str, str],
        maxlen: int | None = None,
    ) -> str:
        """Append an entry to a Redis Stream.

        Args:
            stream: Stream key name.
            fields: Field–value mapping for the entry.
            maxlen: Optional maximum stream length (approximate trimming).

        Returns:
            The auto-generated entry ID.
        """
        entry_id: str = await self.redis.xadd(  # type: ignore[assignment]
            stream,
            fields,
            maxlen=maxlen,
            approximate=True if maxlen else False,
        )
        return entry_id

    async def xread(
        self,
        streams: dict[str, str],
        count: int = 10,
        block: int | None = None,
    ) -> list[Any]:
        """Read new entries from one or more Redis Streams.

        Args:
            streams: Mapping of stream key → last-seen entry ID (e.g. ``"0"``
                     for all entries, ``"$"`` for only new entries).
            count: Maximum entries to return per stream.
            block: Milliseconds to block waiting for new data (``None`` = no block).

        Returns:
            A list of ``[stream_key, [(entry_id, fields), ...]]`` tuples.
        """
        result: list[Any] = await self.redis.xread(  # type: ignore[assignment]
            streams,
            count=count,
            block=block,
        )
        return result

    # ── health check ──

    async def health_check(self) -> bool:
        """Verify connectivity by issuing a ``PING``.

        Returns:
            ``True`` if Redis responds, ``False`` otherwise.
        """
        try:
            return bool(await self.redis.ping())
        except Exception:  # noqa: BLE001
            return False
