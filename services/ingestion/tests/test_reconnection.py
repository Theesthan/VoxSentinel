"""
Tests for the reconnection module.

Validates exponential backoff, max retry enforcement,
on-failure callback invocation, and metric counter increments.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ingestion.reconnection import (
    INITIAL_DELAY_S,
    MAX_RETRIES,
    ReconnectionFailed,
    with_reconnection,
)


class TestWithReconnection:
    """Test suite for ``with_reconnection``."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        """Should return immediately on success."""
        factory = AsyncMock(return_value="ok")
        result = await with_reconnection(factory, stream_id="s1")
        assert result == "ok"
        factory.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self) -> None:
        """Should retry on failure and eventually succeed."""
        call_count = 0

        async def _factory() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("nope")
            return "recovered"

        result = await with_reconnection(_factory, stream_id="s2", initial_delay=0.01)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        """Should raise ReconnectionFailed after max_retries."""
        factory = AsyncMock(side_effect=ConnectionError("fail"))

        with pytest.raises(ReconnectionFailed, match="all 3 reconnection attempts failed"):
            await with_reconnection(
                factory,
                stream_id="s3",
                max_retries=3,
                initial_delay=0.01,
            )

        assert factory.await_count == 3

    @pytest.mark.asyncio
    async def test_on_failure_called(self) -> None:
        """on_failure callback should be called when retries exhausted."""
        factory = AsyncMock(side_effect=RuntimeError("die"))
        on_fail = AsyncMock()

        with pytest.raises(ReconnectionFailed):
            await with_reconnection(
                factory,
                stream_id="s4",
                max_retries=2,
                initial_delay=0.01,
                on_failure=on_fail,
            )

        on_fail.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reconnection_counter_incremented(self) -> None:
        """Counter callback should be called on each retry."""
        call_count = 0

        async def _factory() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("retry me")
            return "done"

        counter = MagicMock()
        await with_reconnection(
            _factory,
            stream_id="s5",
            initial_delay=0.01,
            reconnection_counter=counter,
        )

        # Counter called on retry 1 and retry 2 (2 failures before success).
        assert counter.call_count == 2

    @pytest.mark.asyncio
    async def test_defaults(self) -> None:
        """Module-level defaults should be sensible."""
        assert MAX_RETRIES == 5
        assert INITIAL_DELAY_S == 1.0
