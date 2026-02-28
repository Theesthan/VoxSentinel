"""
Tests for the alert deduplication logic.

Validates cooldown period enforcement, Jaccard distance context
change detection, and correct suppression behavior.
"""

from __future__ import annotations

import time


from nlp.deduplication import Deduplicator, _jaccard_distance


class TestJaccardDistance:
    """Tests for the Jaccard distance helper."""

    def test_identical_strings(self) -> None:
        assert _jaccard_distance("hello world", "hello world") == 0.0

    def test_completely_different(self) -> None:
        assert _jaccard_distance("cat dog", "fish bird") == 1.0

    def test_partial_overlap(self) -> None:
        dist = _jaccard_distance("hello world", "hello there")
        assert 0.0 < dist < 1.0

    def test_empty_strings(self) -> None:
        assert _jaccard_distance("", "") == 0.0

    def test_case_insensitive(self) -> None:
        assert _jaccard_distance("Hello World", "hello world") == 0.0


class TestDeduplicator:
    """Tests for Deduplicator."""

    def test_first_alert_not_suppressed(self) -> None:
        dedup = Deduplicator(cooldown_s=10.0)
        assert dedup.should_suppress("s1", "gun", "exact", "context text") is False

    def test_repeat_within_cooldown_suppressed(self) -> None:
        dedup = Deduplicator(cooldown_s=10.0)
        dedup.should_suppress("s1", "gun", "exact", "context text")
        assert dedup.should_suppress("s1", "gun", "exact", "context text") is True

    def test_different_keyword_not_suppressed(self) -> None:
        dedup = Deduplicator(cooldown_s=10.0)
        dedup.should_suppress("s1", "gun", "exact", "context")
        assert dedup.should_suppress("s1", "fire", "exact", "context") is False

    def test_different_stream_not_suppressed(self) -> None:
        dedup = Deduplicator(cooldown_s=10.0)
        dedup.should_suppress("s1", "gun", "exact", "context")
        assert dedup.should_suppress("s2", "gun", "exact", "context") is False

    def test_context_change_allows_alert(self) -> None:
        dedup = Deduplicator(cooldown_s=10.0)
        dedup.should_suppress("s1", "gun", "exact", "he has a gun near the entrance")
        # Very different context → should not suppress
        result = dedup.should_suppress(
            "s1", "gun", "exact",
            "completely different topic about something else entirely"
        )
        assert result is False

    def test_expired_cooldown_allows_alert(self) -> None:
        dedup = Deduplicator(cooldown_s=0.01)
        dedup.should_suppress("s1", "gun", "exact", "context")
        time.sleep(0.02)  # wait for cooldown to expire
        assert dedup.should_suppress("s1", "gun", "exact", "context") is False

    def test_clear(self) -> None:
        dedup = Deduplicator(cooldown_s=10.0)
        dedup.should_suppress("s1", "gun", "exact", "context")
        dedup.clear()
        # After clear, should act like first alert
        assert dedup.should_suppress("s1", "gun", "exact", "context") is False

