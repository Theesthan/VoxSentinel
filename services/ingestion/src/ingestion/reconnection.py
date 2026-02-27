"""
Reconnection logic for VoxSentinel ingestion service.

Implements exponential backoff reconnection strategy for PyAV
connection errors: starting at 1 s, doubling each attempt, up
to ``MAX_RETRIES`` (5).  After exhausting retries, marks the
stream status as ``error`` via a REST API call.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog

logger = structlog.get_logger()

MAX_RETRIES: int = 5
INITIAL_DELAY_S: float = 1.0

T = TypeVar("T")


class ReconnectionFailed(Exception):
    """Raised when all retry attempts are exhausted."""


async def with_reconnection(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    stream_id: str = "",
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_DELAY_S,
    on_failure: Callable[[], Awaitable[None]] | None = None,
    reconnection_counter: Callable[[], None] | None = None,
) -> T:
    """Execute *coro_factory* with exponential-backoff retries.

    On each connection-level exception the function sleeps for an
    exponentially increasing delay (1 s, 2 s, 4 s, 8 s, 16 s) and
    retries.  After *max_retries* failures the optional *on_failure*
    callback is awaited (typically marking the stream as ``error``)
    and ``ReconnectionFailed`` is raised.

    Args:
        coro_factory: Zero-argument callable returning an awaitable.
        stream_id: For structured logging.
        max_retries: Maximum retry attempts before giving up.
        initial_delay: Seconds before the first retry.
        on_failure: Async callback invoked after all retries fail.
        reconnection_counter: Sync callable to increment a metric.

    Returns:
        The return value of *coro_factory()* on success.

    Raises:
        ReconnectionFailed: If all retry attempts are exhausted.
    """
    log = logger.bind(stream_id=stream_id)
    delay = initial_delay

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "reconnection_attempt",
                attempt=attempt,
                max_retries=max_retries,
                delay_s=delay,
                error=str(exc),
            )
            if reconnection_counter is not None:
                reconnection_counter()
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                log.error("reconnection_exhausted", attempts=max_retries, last_error=str(exc))
                if on_failure is not None:
                    await on_failure()
                raise ReconnectionFailed(
                    f"Stream {stream_id}: all {max_retries} reconnection attempts failed"
                ) from exc

    # Should never be reached, but keeps mypy happy.
    raise ReconnectionFailed("Unexpected code path")
