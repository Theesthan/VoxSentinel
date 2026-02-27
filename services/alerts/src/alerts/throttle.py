"""
Alert rate limiting and throttling for VoxSentinel.

Enforces configurable rate limits (max N alerts per stream per minute)
and deduplication windows to prevent alert storms.

Implementation
--------------
* **Rate limiting** — Redis sorted sets keyed ``throttle:{stream_id}``.
  Each alert adds its unix-epoch timestamp as both score and member.
  Before allowing an alert we trim entries older than 60 s and check the
  cardinality against ``max_per_minute``.
* **Deduplication** — Redis TTL keys
  ``dedup:{stream_id}:{keyword}:{match_type}`` with a configurable TTL
  (default 10 s).  If the key already exists the alert is considered a
  duplicate.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger()

# Tunables — overridable via constructor kwargs.
_DEFAULT_MAX_PER_MINUTE = 30
_DEFAULT_DEDUP_TTL_S = 10


class AlertThrottle:
    """Rate-limiter and deduplicator backed by Redis.

    Args:
        redis: An async Redis connection (the raw ``redis.asyncio.Redis``
               instance, **not** the ``RedisClient`` wrapper).
        max_per_minute: Maximum alerts per stream per 60-second window.
        dedup_ttl_s: Seconds to suppress duplicate
                     ``(stream_id, keyword, match_type)`` tuples.
    """

    def __init__(
        self,
        redis: Any,
        *,
        max_per_minute: int = _DEFAULT_MAX_PER_MINUTE,
        dedup_ttl_s: int = _DEFAULT_DEDUP_TTL_S,
    ) -> None:
        self._redis = redis
        self.max_per_minute = max_per_minute
        self.dedup_ttl_s = dedup_ttl_s

    # ── deduplication ──

    async def is_duplicate(
        self,
        stream_id: str,
        keyword: str,
        match_type: str,
    ) -> bool:
        """Return ``True`` if this combination was seen within the TTL window.

        If not a duplicate the key is set so subsequent calls within the
        TTL window will return ``True``.

        Args:
            stream_id: Stream identifier.
            keyword: The matched keyword/rule.
            match_type: Matching strategy (exact/fuzzy/regex/…).
        """
        key = f"dedup:{stream_id}:{keyword}:{match_type}"
        # SET … NX returns True only when the key was freshly created.
        was_set = await self._redis.set(key, "1", nx=True, ex=self.dedup_ttl_s)
        is_dup = not bool(was_set)
        if is_dup:
            logger.debug("alert_deduplicated", stream_id=stream_id, keyword=keyword)
        return is_dup

    # ── rate limiting ──

    async def is_throttled(self, stream_id: str) -> bool:
        """Return ``True`` if *stream_id* has exceeded the rate limit.

        A sliding 60-second window implemented with a Redis sorted set.
        Each accepted alert adds an entry; old entries are pruned on every
        call.

        Args:
            stream_id: Stream identifier.
        """
        key = f"throttle:{stream_id}"
        now = time.time()
        window_start = now - 60.0

        pipe = self._redis.pipeline()
        # Remove entries older than 60 s.
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Count remaining entries.
        pipe.zcard(key)
        results = await pipe.execute()

        count: int = results[1]
        if count >= self.max_per_minute:
            logger.warning(
                "alert_throttled",
                stream_id=stream_id,
                count=count,
                max=self.max_per_minute,
            )
            return True
        return False

    async def record(self, stream_id: str) -> None:
        """Record a dispatched alert for rate-limit tracking.

        Must be called after the alert passes both dedup and throttle
        checks and is actually dispatched.

        Args:
            stream_id: Stream identifier.
        """
        key = f"throttle:{stream_id}"
        now = time.time()
        member = f"{now}"
        pipe = self._redis.pipeline()
        pipe.zadd(key, {member: now})
        # Auto-expire the key after 120 s as a safety net.
        pipe.expire(key, 120)
        await pipe.execute()
