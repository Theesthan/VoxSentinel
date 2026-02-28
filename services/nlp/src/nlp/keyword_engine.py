"""
Keyword detection engine for VoxSentinel.

Orchestrates all three matching modes (Aho-Corasick exact, RapidFuzz
fuzzy, and regex) against the per-stream sliding transcript window.
Emits KeywordMatchEvent objects for all matches found.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from tg_common.models import KeywordMatchEvent, KeywordRule, MatchType, RuleMatchType

from nlp.aho_corasick_index import AhoCorasickIndex
from nlp.fuzzy_matcher import FuzzyMatcher
from nlp.regex_matcher import RegexMatcher
from nlp.sliding_window import SlidingWindow

logger = structlog.get_logger()


class KeywordEngine:
    """Orchestrates exact, fuzzy, and regex keyword matching.

    Maintains per-stream :class:`SlidingWindow` instances and dispatches
    incoming finalised transcript text through all three matchers.  Emits
    :class:`KeywordMatchEvent` for every hit.

    Args:
        window_seconds: Duration of the per-stream sliding window.
    """

    def __init__(self, window_seconds: float = 10.0) -> None:
        self._window_seconds = window_seconds
        self._windows: dict[str, SlidingWindow] = {}
        self._aho_index = AhoCorasickIndex()
        self._fuzzy_matcher = FuzzyMatcher()
        self._regex_matcher = RegexMatcher()
        self._rules: list[KeywordRule] = []
        # Lookup for severity/category by rule_id
        self._rule_map: dict[UUID, KeywordRule] = {}

    # ── rule management ──

    def load_rules(self, rules: list[KeywordRule]) -> list[str]:
        """Load (or hot-reload) keyword rules into all matchers.

        Args:
            rules: Full list of :class:`KeywordRule` objects to use.

        Returns:
            List of error messages for invalid regex patterns (if any).
        """
        self._rules = [r for r in rules if r.enabled]
        self._rule_map = {r.rule_id: r for r in self._rules}

        # Split by match type
        exact_rules = [
            (r.keyword, r.rule_id)
            for r in self._rules
            if r.match_type == RuleMatchType.EXACT
        ]
        fuzzy_rules = [
            (r.keyword, r.rule_id, r.fuzzy_threshold)
            for r in self._rules
            if r.match_type == RuleMatchType.FUZZY
        ]
        regex_rules = [
            (r.keyword, r.rule_id)
            for r in self._rules
            if r.match_type == RuleMatchType.REGEX
        ]

        self._aho_index.build(exact_rules)
        errors: list[str] = self._regex_matcher.load_rules(regex_rules)
        # Fuzzy rules are passed per-call; store them for later
        self._fuzzy_rules = fuzzy_rules

        logger.info(
            "keyword_engine_rules_loaded",
            exact=len(exact_rules),
            fuzzy=len(fuzzy_rules),
            regex=len(regex_rules),
        )
        return errors

    # ── detection ──

    def detect(
        self,
        text: str,
        start_s: float,
        end_s: float,
        stream_id: UUID,
        session_id: UUID,
        speaker_id: str | None = None,
    ) -> list[KeywordMatchEvent]:
        """Run all matchers against a new finalized transcript fragment.

        Appends the fragment to the per-stream sliding window, then scans
        the full window text through exact, fuzzy, and regex matchers.

        Args:
            text: The finalized transcript text.
            start_s: Start time in seconds (stream-relative).
            end_s: End time in seconds (stream-relative).
            stream_id: UUID of the source stream.
            session_id: UUID of the active session.
            speaker_id: Speaker label if available.

        Returns:
            List of :class:`KeywordMatchEvent` for every match found.
        """
        sid = str(stream_id)
        if sid not in self._windows:
            self._windows[sid] = SlidingWindow(self._window_seconds)

        window_text = self._windows[sid].append(text, start_s, end_s)
        if not window_text:
            return []

        events: list[KeywordMatchEvent] = []

        # 1) Aho-Corasick exact matches
        for hit in self._aho_index.search(window_text):
            _rule = self._rule_map.get(hit.rule_id)  # reserved for future severity lookup
            events.append(
                KeywordMatchEvent(
                    keyword=hit.keyword,
                    match_type=MatchType.EXACT,
                    similarity_score=1.0,
                    matched_text=hit.keyword,
                    stream_id=stream_id,
                    session_id=session_id,
                    speaker_id=speaker_id,
                    surrounding_context=window_text,
                )
            )

        # 2) Fuzzy matches
        for hit in self._fuzzy_matcher.match(window_text, self._fuzzy_rules):
            events.append(
                KeywordMatchEvent(
                    keyword=hit.keyword,
                    match_type=MatchType.FUZZY,
                    similarity_score=hit.score,
                    matched_text=hit.matched_text,
                    stream_id=stream_id,
                    session_id=session_id,
                    speaker_id=speaker_id,
                    surrounding_context=window_text,
                )
            )

        # 3) Regex matches
        for hit in self._regex_matcher.match(window_text):
            events.append(
                KeywordMatchEvent(
                    keyword=hit.keyword,
                    match_type=MatchType.REGEX,
                    similarity_score=None,
                    matched_text=hit.matched_text,
                    stream_id=stream_id,
                    session_id=session_id,
                    speaker_id=speaker_id,
                    surrounding_context=window_text,
                )
            )

        if events:
            logger.info(
                "keyword_matches_detected",
                stream_id=sid,
                match_count=len(events),
            )
        return events

    def remove_stream(self, stream_id: str) -> None:
        """Remove the sliding window for a completed/stopped stream."""
        self._windows.pop(stream_id, None)

    @property
    def aho_index(self) -> AhoCorasickIndex:
        """Access the underlying Aho-Corasick index (for health checks)."""
        return self._aho_index

    @property
    def regex_matcher(self) -> RegexMatcher:
        """Access the underlying regex matcher."""
        return self._regex_matcher
