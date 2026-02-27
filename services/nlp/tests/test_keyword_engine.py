"""
Tests for the keyword detection engine.

Validates orchestration of all three matching modes, event emission,
and correct handling of multiple simultaneous matches.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from tg_common.models import KeywordRule, MatchType, RuleMatchType, Severity

from nlp.keyword_engine import KeywordEngine


def _make_rule(
    keyword: str,
    match_type: RuleMatchType = RuleMatchType.EXACT,
    severity: Severity = Severity.CRITICAL,
    fuzzy_threshold: float = 0.8,
    rule_id: UUID | None = None,
) -> KeywordRule:
    """Helper to create a KeywordRule for tests."""
    return KeywordRule(
        rule_id=rule_id or uuid4(),
        rule_set_name="test_rules",
        keyword=keyword,
        match_type=match_type,
        fuzzy_threshold=fuzzy_threshold,
        severity=severity,
        enabled=True,
    )


STREAM_ID = UUID("12345678-1234-5678-1234-567812345678")
SESSION_ID = UUID("87654321-4321-8765-4321-876543218765")


class TestExactMatch:
    """Tests for Aho-Corasick exact matching via KeywordEngine."""

    def test_exact_match_finds_keyword(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule("gun")])
        events = engine.detect("he has a gun", 0.0, 1.0, STREAM_ID, SESSION_ID)
        assert len(events) == 1
        assert events[0].keyword == "gun"
        assert events[0].match_type == MatchType.EXACT
        assert events[0].similarity_score == 1.0

    def test_exact_match_case_insensitive(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule("fire")])
        events = engine.detect("FIRE in the building", 0.0, 1.0, STREAM_ID, SESSION_ID)
        assert len(events) == 1

    def test_no_match_returns_empty(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule("gun")])
        events = engine.detect("all is quiet", 0.0, 1.0, STREAM_ID, SESSION_ID)
        assert events == []

    def test_multiple_exact_keywords(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule("gun"), _make_rule("fire")])
        events = engine.detect("gun and fire", 0.0, 1.0, STREAM_ID, SESSION_ID)
        assert len(events) == 2
        keywords = {e.keyword for e in events}
        assert keywords == {"gun", "fire"}


class TestFuzzyMatch:
    """Tests for fuzzy matching via KeywordEngine."""

    def test_fuzzy_match_above_threshold(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule("fire", match_type=RuleMatchType.FUZZY, fuzzy_threshold=0.5)])
        events = engine.detect("there was a fire", 0.0, 1.0, STREAM_ID, SESSION_ID)
        fuzzy_events = [e for e in events if e.match_type == MatchType.FUZZY]
        assert len(fuzzy_events) >= 1

    def test_fuzzy_match_below_threshold_returns_no_result(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([
            _make_rule(
                "active shooter situation",
                match_type=RuleMatchType.FUZZY,
                fuzzy_threshold=0.95,
            )
        ])
        events = engine.detect("the weather is nice", 0.0, 1.0, STREAM_ID, SESSION_ID)
        fuzzy_events = [e for e in events if e.match_type == MatchType.FUZZY]
        assert fuzzy_events == []


class TestRegexMatch:
    """Tests for regex matching via KeywordEngine."""

    def test_regex_match_finds_pattern(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule(r"\b\d{3}-\d{4}\b", match_type=RuleMatchType.REGEX)])
        events = engine.detect("call me at 555-1234", 0.0, 1.0, STREAM_ID, SESSION_ID)
        regex_events = [e for e in events if e.match_type == MatchType.REGEX]
        assert len(regex_events) == 1
        assert regex_events[0].matched_text == "555-1234"

    def test_regex_no_match(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule(r"\b\d{10}\b", match_type=RuleMatchType.REGEX)])
        events = engine.detect("no numbers here", 0.0, 1.0, STREAM_ID, SESSION_ID)
        regex_events = [e for e in events if e.match_type == MatchType.REGEX]
        assert regex_events == []

    def test_invalid_regex_returns_error(self) -> None:
        engine = KeywordEngine()
        errors = engine.load_rules([_make_rule("[invalid", match_type=RuleMatchType.REGEX)])
        assert len(errors) == 1


class TestMixedRules:
    """Tests for combined exact + fuzzy + regex rules."""

    def test_all_three_match_types(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([
            _make_rule("gun", match_type=RuleMatchType.EXACT),
            _make_rule("fire", match_type=RuleMatchType.FUZZY, fuzzy_threshold=0.5),
            _make_rule(r"\bhelp\b", match_type=RuleMatchType.REGEX),
        ])
        events = engine.detect("gun fire help", 0.0, 1.0, STREAM_ID, SESSION_ID)
        match_types = {e.match_type for e in events}
        assert MatchType.EXACT in match_types
        assert MatchType.REGEX in match_types

    def test_disabled_rule_not_matched(self) -> None:
        engine = KeywordEngine()
        rule = _make_rule("gun")
        rule.enabled = False
        engine.load_rules([rule])
        events = engine.detect("he has a gun", 0.0, 1.0, STREAM_ID, SESSION_ID)
        assert events == []


class TestSlidingWindow:
    """Tests for sliding window integration in KeywordEngine."""

    def test_window_accumulates_text(self) -> None:
        engine = KeywordEngine(window_seconds=10.0)
        engine.load_rules([_make_rule("gun fire")])
        engine.detect("gun", 0.0, 1.0, STREAM_ID, SESSION_ID)
        events = engine.detect("fire", 1.0, 2.0, STREAM_ID, SESSION_ID)
        # "gun fire" should now be in the window
        assert len(events) == 1

    def test_window_evicts_old_text(self) -> None:
        engine = KeywordEngine(window_seconds=2.0)
        engine.load_rules([_make_rule("old keyword")])
        engine.detect("old keyword", 0.0, 1.0, STREAM_ID, SESSION_ID)
        events = engine.detect("new text", 10.0, 11.0, STREAM_ID, SESSION_ID)
        # "old keyword" should have been evicted
        assert events == []

    def test_remove_stream_clears_window(self) -> None:
        engine = KeywordEngine()
        engine.load_rules([_make_rule("gun")])
        engine.detect("gun", 0.0, 1.0, STREAM_ID, SESSION_ID)
        engine.remove_stream(str(STREAM_ID))
        # New text in same stream starts fresh
        events = engine.detect("peaceful morning", 2.0, 3.0, STREAM_ID, SESSION_ID)
        assert events == []

