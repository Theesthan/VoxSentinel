"""
Tests for the Aho-Corasick index manager.

Covers edge cases: overlapping patterns, Unicode keywords, empty
input, and automaton rebuild on rule hot-reload.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from nlp.aho_corasick_index import AhoCorasickIndex


class TestBuild:
    """Tests for automaton construction."""

    def test_build_with_rules(self) -> None:
        index = AhoCorasickIndex()
        rules = [("gun", uuid4()), ("fire", uuid4()), ("help", uuid4())]
        index.build(rules)
        assert index.pattern_count == 3
        assert index.is_ready is True

    def test_build_with_empty_rules(self) -> None:
        index = AhoCorasickIndex()
        index.build([])
        assert index.pattern_count == 0
        assert index.is_ready is False

    def test_rebuild_replaces_old_automaton(self) -> None:
        index = AhoCorasickIndex()
        index.build([("gun", uuid4())])
        assert index.pattern_count == 1

        index.build([("fire", uuid4()), ("help", uuid4())])
        assert index.pattern_count == 2

    def test_initial_state_not_ready(self) -> None:
        index = AhoCorasickIndex()
        assert index.is_ready is False
        assert index.pattern_count == 0


class TestSearch:
    """Tests for pattern searching."""

    def test_exact_match_finds_keyword(self) -> None:
        rule_id = uuid4()
        index = AhoCorasickIndex()
        index.build([("gun", rule_id)])
        results = index.search("he has a gun near the entrance")
        assert len(results) == 1
        assert results[0].keyword == "gun"
        assert results[0].rule_id == rule_id

    def test_case_insensitive_match(self) -> None:
        index = AhoCorasickIndex()
        index.build([("gun", uuid4())])
        results = index.search("He has a GUN")
        assert len(results) == 1
        assert results[0].keyword == "gun"

    def test_multiple_matches(self) -> None:
        index = AhoCorasickIndex()
        index.build([("gun", uuid4()), ("fire", uuid4())])
        results = index.search("gun and fire everywhere")
        assert len(results) == 2
        keywords = {r.keyword for r in results}
        assert keywords == {"gun", "fire"}

    def test_no_match_returns_empty(self) -> None:
        index = AhoCorasickIndex()
        index.build([("gun", uuid4())])
        results = index.search("everything is peaceful")
        assert results == []

    def test_empty_text_returns_empty(self) -> None:
        index = AhoCorasickIndex()
        index.build([("gun", uuid4())])
        results = index.search("")
        assert results == []

    def test_no_automaton_returns_empty(self) -> None:
        index = AhoCorasickIndex()
        results = index.search("gun is here")
        assert results == []

    def test_unicode_keyword(self) -> None:
        index = AhoCorasickIndex()
        rule_id = uuid4()
        index.build([("危険", rule_id)])
        results = index.search("これは危険です")
        assert len(results) == 1
        assert results[0].keyword == "危険"

    def test_overlapping_patterns(self) -> None:
        index = AhoCorasickIndex()
        index.build([("he", uuid4()), ("help", uuid4())])
        results = index.search("help me")
        # Both "he" (within "help") and "help" should match
        keywords = {r.keyword for r in results}
        assert "he" in keywords
        assert "help" in keywords

    def test_phrase_match(self) -> None:
        index = AhoCorasickIndex()
        rule_id = uuid4()
        index.build([("active shooter", rule_id)])
        results = index.search("there is an active shooter in the building")
        assert len(results) == 1
        assert results[0].keyword == "active shooter"

    def test_duplicate_match_in_text(self) -> None:
        index = AhoCorasickIndex()
        index.build([("fire", uuid4())])
        results = index.search("fire fire fire")
        assert len(results) == 3

