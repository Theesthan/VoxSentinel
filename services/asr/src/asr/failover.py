"""
Circuit breaker and failover logic for VoxSentinel ASR service.

Implements the circuit breaker pattern for ASR backend connections,
tracking consecutive failures and automatically switching to fallback
backends when the primary is unavailable.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from enum import Enum

import structlog
from circuitbreaker import CircuitBreakerError  # re-exported for callers

from tg_common.models import TranscriptToken

from asr.engine_base import ASREngine

logger = structlog.get_logger()

# Re-export so callers can ``from asr.failover import CircuitBreakerError``.
__all__ = [
    "ASRCircuitBreaker",
    "ASRFailoverManager",
    "CircuitBreakerError",
    "CircuitState",
]


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class ASRCircuitBreaker:
    """Async-friendly circuit breaker for ASR engine calls.

    Tracks consecutive failures.  After *failure_threshold* failures
    the circuit opens for *recovery_timeout* seconds, then transitions
    to half-open to probe recovery.

    Args:
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to stay open before half-open probe.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: CircuitState = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may transition on read)."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        """Number of consecutive failures recorded."""
        return self._failure_count

    @property
    def is_available(self) -> bool:
        """``True`` when the breaker allows requests through."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Reset the failure counter and close the circuit."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Increment the failure counter; open the circuit if threshold reached."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Force-reset the breaker to closed with zero failures."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = 0.0


class ASRFailoverManager:
    """Manage primary/fallback ASR engine selection with circuit breaker.

    Routes audio to the primary engine.  When the primary's circuit
    opens (after *failure_threshold* consecutive failures), traffic
    is transparently redirected to the *fallback* engine with a
    ``WARNING`` log.

    Args:
        primary: The primary :class:`ASREngine` instance.
        fallback: Optional fallback :class:`ASREngine` instance.
        failure_threshold: Consecutive failures before failover.
        recovery_timeout: Seconds to wait before probing primary again.
    """

    def __init__(
        self,
        primary: ASREngine,
        fallback: ASREngine | None = None,
        *,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._breaker = ASRCircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        self._using_fallback: bool = False

    @property
    def active_engine(self) -> ASREngine:
        """The engine currently handling traffic."""
        if not self._breaker.is_available and self._fallback is not None:
            return self._fallback
        return self._primary

    @property
    def breaker(self) -> ASRCircuitBreaker:
        """Expose the circuit breaker for inspection (e.g. health checks)."""
        return self._breaker

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        """Route *chunk* to the appropriate engine via the circuit breaker.

        Yields :class:`TranscriptToken` objects from the active engine.
        """
        if self._breaker.is_available:
            try:
                async for token in self._primary.stream_audio(chunk):
                    self._breaker.record_success()
                    self._using_fallback = False
                    yield token
                return
            except Exception as exc:
                self._breaker.record_failure()
                logger.warning(
                    "asr_primary_failure",
                    engine=self._primary.name,
                    failure_count=self._breaker.failure_count,
                    error=str(exc),
                )

        # Primary unavailable — fall back.
        if self._fallback is not None:
            if not self._using_fallback:
                logger.warning(
                    "asr_failover_activated",
                    primary=self._primary.name,
                    fallback=self._fallback.name,
                    breaker_state=self._breaker.state.value,
                )
                self._using_fallback = True
            async for token in self._fallback.stream_audio(chunk):
                yield token
        else:
            raise CircuitBreakerError(
                f"ASR engine '{self._primary.name}' circuit open and no fallback configured"
            )
