"""
Tests for the alert dispatcher.

Validates alert routing to configured channels based on severity,
alert type, and stream assignment filters.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock


from tg_common.models.alert import AlertType, MatchType, Severity
from alerts.dispatcher import (
    AlertDispatcher,
    _keyword_event_to_alert,
    _sentiment_event_to_alert,
)
from alerts.throttle import AlertThrottle


# ── helpers ──


def _make_channel(name: str = "test", send_ok: bool = True) -> MagicMock:
    """Create a mock AlertChannel."""
    ch = AsyncMock()
    ch.name = name
    ch.enabled = True
    ch.send = AsyncMock(return_value=send_ok)
    return ch


def _make_throttle(mock_redis: AsyncMock) -> AlertThrottle:
    """Create a throttle bound to the mock redis."""
    return AlertThrottle(mock_redis)


# ── event parsing ──


class TestEventParsing:
    """Tests for parse_event (JSON → Alert)."""

    def test_parse_keyword_event(self, stream_id, session_id) -> None:
        data = {
            "keyword": "gun",
            "match_type": "exact",
            "matched_text": "he has a gun",
            "stream_id": stream_id,
            "session_id": session_id,
            "surrounding_context": "context here",
        }
        alert = AlertDispatcher.parse_event("match_events:1", json.dumps(data))
        assert alert is not None
        assert alert.alert_type == AlertType.KEYWORD
        assert alert.matched_rule == "gun"

    def test_parse_sentiment_event(self, stream_id, session_id) -> None:
        data = {
            "stream_id": stream_id,
            "session_id": session_id,
            "sentiment_label": "negative",
            "sentiment_score": 0.92,
        }
        alert = AlertDispatcher.parse_event("sentiment_events:1", json.dumps(data))
        assert alert is not None
        assert alert.alert_type == AlertType.SENTIMENT
        assert alert.matched_rule == "negative"

    def test_parse_invalid_json_returns_none(self) -> None:
        assert AlertDispatcher.parse_event("match_events:1", "not json") is None

    def test_parse_unknown_channel_returns_none(self, stream_id, session_id) -> None:
        data = {"stream_id": stream_id, "session_id": session_id}
        assert AlertDispatcher.parse_event("unknown_channel", json.dumps(data)) is None

    def test_parse_malformed_event_returns_none(self) -> None:
        # Missing required fields for KeywordMatchEvent
        data = {"keyword": "gun"}
        assert AlertDispatcher.parse_event("match_events:1", json.dumps(data)) is None


# ── conversion helpers ──


class TestConversionHelpers:
    """Tests for KeywordMatchEvent → Alert / SentimentEvent → Alert."""

    def test_keyword_event_to_alert_sets_type(self, stream_id, session_id) -> None:
        from tg_common.models.alert import KeywordMatchEvent

        event = KeywordMatchEvent(
            keyword="gun",
            match_type=MatchType.EXACT,
            matched_text="gun",
            stream_id=stream_id,
            session_id=session_id,
        )
        alert = _keyword_event_to_alert(event)
        assert alert.alert_type == AlertType.KEYWORD
        assert alert.severity == Severity.HIGH

    def test_sentiment_event_to_alert_sets_type(self, stream_id, session_id) -> None:
        from tg_common.models.alert import SentimentEvent

        event = SentimentEvent(
            stream_id=stream_id,
            session_id=session_id,
            sentiment_label="negative",
            sentiment_score=0.95,
        )
        alert = _sentiment_event_to_alert(event)
        assert alert.alert_type == AlertType.SENTIMENT
        assert alert.match_type == MatchType.SENTIMENT_THRESHOLD
        assert alert.sentiment_scores == {"negative": 0.95}


# ── dispatch pipeline ──


class TestDispatchPipeline:
    """Tests for the full dispatch() flow."""

    async def test_dispatch_sends_to_all_enabled_channels(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch1 = _make_channel("ws")
        ch2 = _make_channel("webhook")
        dispatcher = AlertDispatcher(throttle, [ch1, ch2])

        result = await dispatcher.dispatch(sample_alert)
        assert result is True
        ch1.send.assert_awaited_once()
        ch2.send.assert_awaited_once()

    async def test_dispatch_skips_disabled_channels(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("disabled")
        ch.enabled = False
        dispatcher = AlertDispatcher(throttle, [ch])

        result = await dispatcher.dispatch(sample_alert)
        assert result is False
        ch.send.assert_not_awaited()

    async def test_dispatch_records_delivery_status(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("ws", send_ok=True)
        dispatcher = AlertDispatcher(throttle, [ch])

        await dispatcher.dispatch(sample_alert)
        assert "ws" in sample_alert.delivered_to
        assert sample_alert.delivery_status["ws"] == "delivered"

    async def test_dispatch_marks_failed_channel(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("webhook", send_ok=False)
        dispatcher = AlertDispatcher(throttle, [ch])

        result = await dispatcher.dispatch(sample_alert)
        assert result is False
        assert sample_alert.delivery_status["webhook"] == "failed"

    async def test_dispatch_calls_retry_enqueue_on_failure(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("webhook", send_ok=False)
        retry_fn = MagicMock()
        dispatcher = AlertDispatcher(throttle, [ch], retry_enqueue=retry_fn)

        await dispatcher.dispatch(sample_alert)
        retry_fn.assert_called_once_with(sample_alert, "webhook")

    async def test_dispatch_calls_alert_writer(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("ws")
        writer = AsyncMock()
        dispatcher = AlertDispatcher(throttle, [ch], alert_writer=writer)

        await dispatcher.dispatch(sample_alert)
        writer.assert_awaited_once_with(sample_alert)


# ── dedup integration ──


class TestDispatchDedup:
    """Tests for dedup suppression in the dispatch pipeline."""

    async def test_duplicate_alert_is_suppressed(
        self, mock_redis, sample_alert
    ) -> None:
        mock_redis.set = AsyncMock(return_value=None)  # already exists
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("ws")
        dispatcher = AlertDispatcher(throttle, [ch])

        result = await dispatcher.dispatch(sample_alert)
        assert result is False
        ch.send.assert_not_awaited()
        assert sample_alert.deduplicated is True


# ── throttle integration ──


class TestDispatchThrottle:
    """Tests for throttle suppression in the dispatch pipeline."""

    async def test_throttled_alert_is_suppressed(
        self, mock_redis, sample_alert
    ) -> None:
        mock_redis.set = AsyncMock(return_value=True)  # dedup passes
        pipe = mock_redis.pipeline()
        pipe.execute = AsyncMock(return_value=[0, 30])  # at limit
        throttle = AlertThrottle(mock_redis, max_per_minute=30)
        ch = _make_channel("ws")
        dispatcher = AlertDispatcher(throttle, [ch])

        result = await dispatcher.dispatch(sample_alert)
        assert result is False
        ch.send.assert_not_awaited()


# ── channel error handling ──


class TestDispatchErrors:
    """Tests for error handling during channel dispatch."""

    async def test_channel_exception_is_caught(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("broken")
        ch.send = AsyncMock(side_effect=RuntimeError("boom"))
        dispatcher = AlertDispatcher(throttle, [ch])

        result = await dispatcher.dispatch(sample_alert)
        assert result is False
        assert sample_alert.delivery_status["broken"] == "error"

    async def test_writer_exception_does_not_crash(
        self, mock_redis, sample_alert
    ) -> None:
        throttle = _make_throttle(mock_redis)
        ch = _make_channel("ws")
        writer = AsyncMock(side_effect=RuntimeError("db down"))
        dispatcher = AlertDispatcher(throttle, [ch], alert_writer=writer)

        # Should not raise
        result = await dispatcher.dispatch(sample_alert)
        assert result is True

