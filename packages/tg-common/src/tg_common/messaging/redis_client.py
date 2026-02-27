"""
Redis client wrapper for VoxSentinel.

Provides an async Redis client for caching, pub/sub messaging,
and state management across all microservices. Handles connection
pooling and reconnection logic.
"""

from __future__ import annotations

import redis.asyncio as aioredis
