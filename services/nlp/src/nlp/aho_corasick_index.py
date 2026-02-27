"""
Aho-Corasick automaton index manager for VoxSentinel.

Builds and maintains the Aho-Corasick automaton for O(n) exact
multi-pattern matching across configured keyword rules. Supports
hot-reload when keyword configurations change.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import ahocorasick
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class AhoMatch:
    """Result of an Aho-Corasick exact-match hit.

    Attributes:
        keyword: The keyword that matched.
        rule_id: UUID of the originating KeywordRule.
        end_index: Character index in the haystack where the match ends.
    """

    keyword: str
    rule_id: UUID
    end_index: int


class AhoCorasickIndex:
    """Manages a pyahocorasick ``Automaton`` for exact multi-pattern matching.

    The automaton is rebuilt from scratch whenever rules change (hot-reload).
    All keywords are stored and searched in lower-case for case-insensitive
    matching.
    """

    def __init__(self) -> None:
        self._automaton: ahocorasick.Automaton | None = None
        self._pattern_count: int = 0

    # ── public API ──

    def build(self, rules: list[tuple[str, UUID]]) -> None:
        """Build (or rebuild) the automaton from *(keyword, rule_id)* pairs.

        Args:
            rules: Iterable of ``(keyword_text, rule_id)`` tuples.  Only
                rules with ``match_type == 'exact'`` should be passed here.
        """
        automaton = ahocorasick.Automaton()
        count = 0
        for keyword, rule_id in rules:
            key = keyword.lower()
            automaton.add_word(key, (key, rule_id))
            count += 1
        if count:
            automaton.make_automaton()
            self._automaton = automaton
        else:
            self._automaton = None
        self._pattern_count = count
        logger.info("aho_corasick_index_built", pattern_count=count)

    def search(self, text: str) -> list[AhoMatch]:
        """Search *text* for all exact-match keywords.

        Args:
            text: Haystack text to scan (converted to lower-case internally).

        Returns:
            List of :class:`AhoMatch` instances for every hit.
        """
        if self._automaton is None or not text:
            return []
        results: list[AhoMatch] = []
        for end_index, (keyword, rule_id) in self._automaton.iter(text.lower()):
            results.append(AhoMatch(keyword=keyword, rule_id=rule_id, end_index=end_index))
        return results

    @property
    def pattern_count(self) -> int:
        """Number of patterns currently loaded."""
        return self._pattern_count

    @property
    def is_ready(self) -> bool:
        """Whether the automaton has been built and contains patterns."""
        return self._automaton is not None
