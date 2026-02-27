"""
Rate limiting middleware for VoxSentinel API.

Enforces configurable request rate limits (default 100 req/min
per API key) to prevent abuse and ensure fair resource usage.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

DEFAULT_LIMIT = 100  # requests
DEFAULT_WINDOW = 60  # seconds

# Paths that skip rate-limiting.
_SKIP_PATHS: set[str] = {"/health", "/docs", "/openapi.json", "/redoc", "/metrics"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding-window rate limiter (100 req/min per API key).

    When no Redis client is available, falls back to an in-memory store
    so unit tests and dev mode still work.
    """

    def __init__(self, app: Any, redis: Any | None = None, limit: int = DEFAULT_LIMIT, window: int = DEFAULT_WINDOW) -> None:
        super().__init__(app)
        self._redis = redis
        self._limit = limit
        self._window = window
        # In-memory fallback: {key: list[float timestamps]}
        self._mem: dict[str, list[float]] = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS or path.startswith("/ws/"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        key = auth[len("Bearer "):] if auth.startswith("Bearer ") else "anonymous"
        bucket = f"rate:{key}"

        if self._redis is not None:
            allowed = await self._check_redis(bucket)
        else:
            allowed = self._check_memory(bucket)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        return await call_next(request)

    async def _check_redis(self, bucket: str) -> bool:
        """Sliding-window counter using a Redis sorted set."""
        now = time.time()
        window_start = now - self._window

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(bucket, 0, window_start)
        pipe.zadd(bucket, {str(now): now})
        pipe.zcard(bucket)
        pipe.expire(bucket, self._window)
        results = await pipe.execute()
        count = results[2]
        return count <= self._limit

    def _check_memory(self, bucket: str) -> bool:
        """Simple in-memory sliding window (for dev/tests)."""
        now = time.time()
        window_start = now - self._window
        timestamps = self._mem.get(bucket, [])
        timestamps = [t for t in timestamps if t > window_start]
        timestamps.append(now)
        self._mem[bucket] = timestamps
        return len(timestamps) <= self._limit
