"""
Fuzzy string matching wrapper for VoxSentinel.

Uses RapidFuzz token_set_ratio and partial_ratio to detect approximate
keyword matches with configurable similarity thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rapidfuzz import fuzz

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class FuzzyMatch:
    """Result of a fuzzy keyword match.

    Attributes:
        keyword: The keyword from the rule.
        rule_id: UUID of the originating KeywordRule.
        score: Similarity score from rapidfuzz (0–100).
        matched_text: The portion of text that was compared.
    """

    keyword: str
    rule_id: UUID
    score: float
    matched_text: str


class FuzzyMatcher:
    """Wraps RapidFuzz ``token_set_ratio`` for fuzzy keyword detection.

    Each rule carries its own *fuzzy_threshold* (0.0–1.0); only matches
    that meet or exceed that threshold are returned.
    """

    def match(
        self,
        text: str,
        rules: list[tuple[str, UUID, float]],
    ) -> list[FuzzyMatch]:
        """Find fuzzy matches of *rules* against *text*.

        Args:
            text: The haystack text to scan.
            rules: Iterable of ``(keyword, rule_id, threshold_0_to_1)``
                tuples.  Only rules with ``match_type == 'fuzzy'`` should be
                passed here.

        Returns:
            List of :class:`FuzzyMatch` for every rule whose score >= threshold.
        """
        if not text:
            return []

        results: list[FuzzyMatch] = []
        for keyword, rule_id, threshold in rules:
            # rapidfuzz returns 0-100; threshold is 0.0-1.0
            score = fuzz.token_set_ratio(keyword.lower(), text.lower())
            if score >= threshold * 100:
                results.append(
                    FuzzyMatch(
                        keyword=keyword,
                        rule_id=rule_id,
                        score=score / 100.0,
                        matched_text=text,
                    )
                )
        return results
