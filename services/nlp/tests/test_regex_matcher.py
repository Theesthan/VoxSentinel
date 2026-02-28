"""
Tests for the regex matcher module.

Validates pattern compilation, matching, error handling for invalid
patterns, and edge cases.
"""

from __future__ import annotations

from uuid import uuid4


from nlp.regex_matcher import RegexMatcher


class TestRegexMatcherLoad:
    """Tests for RegexMatcher.load_rules()."""

    def test_valid_patterns_loaded(self) -> None:
        matcher = RegexMatcher()
        errors = matcher.load_rules([
            (r"\bgun\b", uuid4()),
            (r"\d{3}-\d{4}", uuid4()),
        ])
        assert errors == []
        assert matcher.pattern_count == 2

    def test_invalid_pattern_returns_error(self) -> None:
        matcher = RegexMatcher()
        errors = matcher.load_rules([
            ("[invalid", uuid4()),
        ])
        assert len(errors) == 1
        assert matcher.pattern_count == 0

    def test_mixed_valid_and_invalid(self) -> None:
        matcher = RegexMatcher()
        errors = matcher.load_rules([
            (r"\bgun\b", uuid4()),
            ("[bad", uuid4()),
            (r"\bfire\b", uuid4()),
        ])
        assert len(errors) == 1
        assert matcher.pattern_count == 2

    def test_reload_clears_old_patterns(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\bgun\b", uuid4())])
        assert matcher.pattern_count == 1
        matcher.load_rules([(r"\bfire\b", uuid4()), (r"\bhelp\b", uuid4())])
        assert matcher.pattern_count == 2


class TestRegexMatcherMatch:
    """Tests for RegexMatcher.match()."""

    def test_simple_match(self) -> None:
        matcher = RegexMatcher()
        rule_id = uuid4()
        matcher.load_rules([(r"\bgun\b", rule_id)])
        results = matcher.match("he has a gun")
        assert len(results) == 1
        assert results[0].matched_text == "gun"
        assert results[0].rule_id == rule_id

    def test_case_insensitive(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\bgun\b", uuid4())])
        results = matcher.match("he has a GUN")
        assert len(results) == 1

    def test_phone_number_pattern(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\d{3}-\d{4}", uuid4())])
        results = matcher.match("call 555-1234 now")
        assert len(results) == 1
        assert results[0].matched_text == "555-1234"

    def test_no_match(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\bgun\b", uuid4())])
        results = matcher.match("everything is peaceful")
        assert results == []

    def test_empty_text(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\bgun\b", uuid4())])
        results = matcher.match("")
        assert results == []

    def test_multiple_matches_same_pattern(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\b\d+\b", uuid4())])
        results = matcher.match("1 and 2 and 3")
        assert len(results) == 3

    def test_multiple_patterns(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([
            (r"\bgun\b", uuid4()),
            (r"\bfire\b", uuid4()),
        ])
        results = matcher.match("gun and fire")
        assert len(results) == 2

    def test_match_start_end_positions(self) -> None:
        matcher = RegexMatcher()
        matcher.load_rules([(r"\bgun\b", uuid4())])
        results = matcher.match("a gun here")
        assert results[0].start == 2
        assert results[0].end == 5
