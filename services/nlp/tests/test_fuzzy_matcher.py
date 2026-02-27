"""
Tests for the fuzzy matcher module.

Validates RapidFuzz matching with various thresholds, token_set_ratio
and partial_ratio modes, and edge cases like empty strings.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from nlp.fuzzy_matcher import FuzzyMatcher


class TestFuzzyMatcher:
    """Tests for FuzzyMatcher.match()."""

    def test_exact_text_matches_above_threshold(self) -> None:
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match("fire in the building", [(
            "fire in the building", rule_id, 0.8
        )])
        assert len(results) == 1
        assert results[0].keyword == "fire in the building"
        assert results[0].score >= 0.8

    def test_similar_text_matches_above_threshold(self) -> None:
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match(
            "there is a fire in the building",
            [("fire in building", rule_id, 0.7)],
        )
        assert len(results) == 1
        assert results[0].score >= 0.7

    def test_below_threshold_returns_no_match(self) -> None:
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match(
            "the weather is nice today",
            [("fire in the building", rule_id, 0.8)],
        )
        assert results == []

    def test_empty_text_returns_empty(self) -> None:
        matcher = FuzzyMatcher()
        results = matcher.match("", [("gun", uuid4(), 0.8)])
        assert results == []

    def test_multiple_rules(self) -> None:
        matcher = FuzzyMatcher()
        rid1 = uuid4()
        rid2 = uuid4()
        results = matcher.match(
            "fire and gun spotted",
            [
                ("fire", rid1, 0.5),
                ("gun", rid2, 0.5),
            ],
        )
        # Both keywords should match with high score since they appear in text
        assert len(results) >= 1

    def test_case_insensitive(self) -> None:
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match("FIRE FIRE FIRE", [("fire", rule_id, 0.8)])
        assert len(results) == 1

    def test_score_normalised_to_0_to_1(self) -> None:
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match("gun", [("gun", rule_id, 0.5)])
        assert len(results) == 1
        assert 0.0 <= results[0].score <= 1.0

    def test_threshold_boundary_exact(self) -> None:
        """Threshold of 1.0 should still match an exact string."""
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match("gun", [("gun", rule_id, 1.0)])
        assert len(results) == 1

    def test_zero_threshold_matches_anything(self) -> None:
        matcher = FuzzyMatcher()
        rule_id = uuid4()
        results = matcher.match("completely different text", [("gun", rule_id, 0.0)])
        # With threshold 0, everything matches
        assert len(results) == 1

