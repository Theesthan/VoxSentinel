"""
Tests for the ASR failover and circuit breaker logic.

Validates automatic backend switching on consecutive failures,
cooldown periods, and recovery behavior.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from circuitbreaker import CircuitBreakerError

from tg_common.models import TranscriptToken, WordTimestamp

from asr.engine_base import ASREngine
from asr.failover import ASRCircuitBreaker, ASRFailoverManager, CircuitState


# ── Helpers ──────────────────────────────────────────────────


def _make_token(text: str = "test") -> TranscriptToken:
    now = datetime.now(timezone.utc)
    return TranscriptToken(
        text=text,
        is_final=True,
        start_time=now,
        end_time=now,
        confidence=0.95,
        language="en",
    )


class _StubEngine(ASREngine):
    """Minimal engine for failover tests."""

    def __init__(self, engine_name: str = "stub") -> None:
        self._name = engine_name
        self.connected = True

    @property
    def name(self) -> str:
        return self._name

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        yield _make_token("from_" + self._name)

    async def health_check(self) -> bool:
        return self.connected


class _FailingEngine(ASREngine):
    """Engine that always raises on stream_audio."""

    def __init__(self, engine_name: str = "failing") -> None:
        self._name = engine_name

    @property
    def name(self) -> str:
        return self._name

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def stream_audio(self, chunk: bytes) -> AsyncIterator[TranscriptToken]:
        raise ConnectionError("engine unavailable")
        yield  # pragma: no cover

    async def health_check(self) -> bool:
        return False


# ── ASRCircuitBreaker tests ──────────────────────────────────


class TestASRCircuitBreaker:
    """Tests for the circuit breaker state machine."""

    def test_initial_state_is_closed(self) -> None:
        cb = ASRCircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available is True
        assert cb.failure_count == 0

    def test_single_failure_stays_closed(self) -> None:
        cb = ASRCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 1

    def test_threshold_failures_opens_circuit(self) -> None:
        cb = ASRCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_available is False

    def test_success_resets_counter(self) -> None:
        cb = ASRCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_recovery_timeout_transitions_to_half_open(self) -> None:
        cb = ASRCircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        # With recovery_timeout=0, the very first state check already
        # sees the timeout elapsed and transitions to half-open.
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_available is True

    def test_reset(self) -> None:
        cb = ASRCircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_success_after_half_open_closes(self) -> None:
        cb = ASRCircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        time.sleep(0.01)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED


# ── ASRFailoverManager tests ────────────────────────────────


class TestASRFailoverManager:
    """Tests for failover routing between primary and fallback engines."""

    async def test_uses_primary_when_healthy(self) -> None:
        """Traffic goes to primary when circuit is closed."""
        primary = _StubEngine("primary")
        fallback = _StubEngine("fallback")
        fm = ASRFailoverManager(primary, fallback)

        tokens = [t async for t in fm.stream_audio(b"\x00")]
        assert len(tokens) == 1
        assert tokens[0].text == "from_primary"

    async def test_active_engine_is_primary_initially(self) -> None:
        primary = _StubEngine("primary")
        fallback = _StubEngine("fallback")
        fm = ASRFailoverManager(primary, fallback)
        assert fm.active_engine.name == "primary"

    async def test_failover_after_three_failures(self) -> None:
        """After 3 consecutive failures the fallback engine is used."""
        primary = _FailingEngine("primary")
        fallback = _StubEngine("fallback")
        fm = ASRFailoverManager(primary, fallback, failure_threshold=3)

        # First 3 calls — each fails on primary, falls back.
        for _ in range(3):
            tokens = [t async for t in fm.stream_audio(b"\x00")]
            assert len(tokens) == 1
            assert tokens[0].text == "from_fallback"

        # After 3 failures the circuit is open.
        assert fm.breaker.state == CircuitState.OPEN
        assert fm.active_engine.name == "fallback"

    async def test_failover_logs_warning(self) -> None:
        """A WARNING is logged when failover activates."""
        primary = _FailingEngine("primary")
        fallback = _StubEngine("fallback")
        fm = ASRFailoverManager(primary, fallback, failure_threshold=1)

        with patch("asr.failover.logger") as mock_logger:
            tokens = [t async for t in fm.stream_audio(b"\x00")]

        assert len(tokens) == 1
        mock_logger.warning.assert_any_call(
            "asr_primary_failure",
            engine="primary",
            failure_count=1,
            error="engine unavailable",
        )

    async def test_no_fallback_raises_circuit_breaker_error(self) -> None:
        """CircuitBreakerError raised when no fallback and circuit open."""
        primary = _FailingEngine("primary")
        fm = ASRFailoverManager(primary, fallback=None, failure_threshold=1)

        with pytest.raises(CircuitBreakerError):
            async for _ in fm.stream_audio(b"\x00"):
                pass

    async def test_recovery_returns_to_primary(self) -> None:
        """After recovery timeout, traffic returns to primary."""
        primary = _StubEngine("primary")
        fallback = _StubEngine("fallback")
        fm = ASRFailoverManager(
            primary, fallback, failure_threshold=1, recovery_timeout=0.0
        )

        # Force the breaker open.  With timeout=0 it transitions to
        # half-open immediately on the next state read.
        fm.breaker.record_failure()
        assert fm.breaker.state == CircuitState.HALF_OPEN

        # Now primary should be tried again.
        tokens = [t async for t in fm.stream_audio(b"\x00")]
        assert tokens[0].text == "from_primary"

    async def test_breaker_property_exposed(self) -> None:
        """The breaker property returns the ASRCircuitBreaker."""
        primary = _StubEngine("primary")
        fm = ASRFailoverManager(primary)
        assert isinstance(fm.breaker, ASRCircuitBreaker)
