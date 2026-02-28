"""
Tests for the sentiment classification engine.

Validates DistilBERT inference, confidence scoring, and escalation
alert triggering on persistent negative sentiment.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from nlp.sentiment_engine import SentimentEngine

STREAM_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_ID = UUID("87654321-4321-8765-4321-876543218765")


class TestSentimentClassification:
    """Tests for basic sentiment classification."""

    @pytest.fixture(autouse=True)
    def _setup_engine(self) -> None:
        self.engine = SentimentEngine()
        # Inject a mock pipeline directly
        self.mock_pipeline = MagicMock()
        self.engine._pipeline = self.mock_pipeline

    async def test_positive_sentiment(self) -> None:
        self.mock_pipeline.return_value = [{"label": "POSITIVE", "score": 0.95}]
        result, event = await self.engine.classify(
            "I love this product", 1.0, STREAM_ID, SESSION_ID
        )
        assert result.label == "POSITIVE"
        assert result.score == 0.95
        assert event is None

    async def test_negative_sentiment(self) -> None:
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.9}]
        result, event = await self.engine.classify(
            "This is terrible", 1.0, STREAM_ID, SESSION_ID
        )
        assert result.label == "NEGATIVE"
        assert result.score == 0.9

    async def test_empty_text_returns_neutral(self) -> None:
        result, event = await self.engine.classify("", 1.0, STREAM_ID, SESSION_ID)
        assert result.label == "NEUTRAL"
        assert event is None

    async def test_whitespace_only_returns_neutral(self) -> None:
        result, event = await self.engine.classify("   ", 1.0, STREAM_ID, SESSION_ID)
        assert result.label == "NEUTRAL"
        assert event is None


class TestSentimentEscalation:
    """Tests for escalation triggering on persistent negative sentiment."""

    @pytest.fixture(autouse=True)
    def _setup_engine(self) -> None:
        self.engine = SentimentEngine(
            consecutive_threshold=3,
            score_threshold=0.8,
            rolling_window_s=30.0,
        )
        self.mock_pipeline = MagicMock()
        self.engine._pipeline = self.mock_pipeline

    async def test_escalation_triggers_after_3_consecutive_negatives(self) -> None:
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.85}]

        # First two negatives: no escalation
        _, evt1 = await self.engine.classify("bad", 1.0, STREAM_ID, SESSION_ID)
        _, evt2 = await self.engine.classify("terrible", 2.0, STREAM_ID, SESSION_ID)
        assert evt1 is None
        assert evt2 is None

        # Third consecutive negative: escalation triggered
        _, evt3 = await self.engine.classify("awful", 3.0, STREAM_ID, SESSION_ID)
        assert evt3 is not None
        assert evt3.sentiment_label == "negative"
        assert evt3.stream_id == STREAM_ID

    async def test_no_escalation_if_positive_breaks_streak(self) -> None:
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.85}]
        await self.engine.classify("bad", 1.0, STREAM_ID, SESSION_ID)
        await self.engine.classify("terrible", 2.0, STREAM_ID, SESSION_ID)

        # Inject a positive result to break the streak
        self.mock_pipeline.return_value = [{"label": "POSITIVE", "score": 0.9}]
        _, evt = await self.engine.classify("good news", 3.0, STREAM_ID, SESSION_ID)
        assert evt is None

        # Continue with negatives — streak resets
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.85}]
        _, evt = await self.engine.classify("bad again", 4.0, STREAM_ID, SESSION_ID)
        assert evt is None  # only 1 consecutive negative after break

    async def test_no_escalation_below_score_threshold(self) -> None:
        # Score is negative but below 0.8 threshold
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.7}]
        for i in range(5):
            _, evt = await self.engine.classify(f"bad {i}", float(i), STREAM_ID, SESSION_ID)
            assert evt is None

    async def test_escalation_continues_after_more_negatives(self) -> None:
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.9}]
        events = []
        for i in range(5):
            _, evt = await self.engine.classify(f"bad {i}", float(i), STREAM_ID, SESSION_ID)
            events.append(evt)
        # Escalation should trigger on 3rd, 4th, 5th
        assert events[0] is None
        assert events[1] is None
        assert events[2] is not None
        assert events[3] is not None
        assert events[4] is not None


class TestSentimentWindowEviction:
    """Tests for rolling window eviction."""

    @pytest.fixture(autouse=True)
    def _setup_engine(self) -> None:
        self.engine = SentimentEngine(
            consecutive_threshold=3,
            score_threshold=0.8,
            rolling_window_s=5.0,  # small window for testing
        )
        self.mock_pipeline = MagicMock()
        self.engine._pipeline = self.mock_pipeline

    async def test_old_entries_evicted(self) -> None:
        self.mock_pipeline.return_value = [{"label": "NEGATIVE", "score": 0.85}]
        await self.engine.classify("bad", 1.0, STREAM_ID, SESSION_ID)
        await self.engine.classify("terrible", 2.0, STREAM_ID, SESSION_ID)

        # Jump far ahead — old entries should be evicted
        await self.engine.classify("awful", 20.0, STREAM_ID, SESSION_ID)
        # Only 1 entry in window now (the one at t=20.0), not 3
        sid = str(STREAM_ID)
        assert len(self.engine._history[sid]) == 1


class TestSentimentReadiness:
    """Tests for model readiness."""

    def test_not_ready_before_load(self) -> None:
        engine = SentimentEngine()
        assert engine.is_ready is False

    def test_ready_after_pipeline_set(self) -> None:
        engine = SentimentEngine()
        engine._pipeline = MagicMock()
        assert engine.is_ready is True

    def test_remove_stream_clears_history(self) -> None:
        engine = SentimentEngine()
        engine._history["test-stream"].append(MagicMock())
        engine.remove_stream("test-stream")
        assert "test-stream" not in engine._history

