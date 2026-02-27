"""
Compiled regex pattern manager for VoxSentinel.

Manages the lifecycle of compiled regex patterns for keyword detection.
Validates patterns at configuration load time and applies them against
transcript windows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class RegexMatch:
    """Result of a regex keyword match.

    Attributes:
        keyword: The original regex pattern string.
        rule_id: UUID of the originating KeywordRule.
        matched_text: The actual text captured by the regex.
        start: Start character index in the haystack.
        end: End character index in the haystack.
    """

    keyword: str
    rule_id: UUID
    matched_text: str
    start: int
    end: int


class RegexMatcher:
    """Compiles and caches regex patterns for keyword detection.

    Patterns are compiled once at :meth:`load_rules` time, validated for
    correct syntax, and then reused across searches.
    """

    def __init__(self) -> None:
        self._patterns: list[tuple[re.Pattern[str], str, UUID]] = []

    def load_rules(self, rules: list[tuple[str, UUID]]) -> list[str]:
        """Compile regex rules and return a list of invalid pattern errors.

        Args:
            rules: Iterable of ``(pattern_string, rule_id)`` tuples.  Only
                rules with ``match_type == 'regex'`` should be passed here.

        Returns:
            List of error messages for patterns that failed to compile.
        """
        self._patterns.clear()
        errors: list[str] = []
        for pattern_str, rule_id in rules:
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                self._patterns.append((compiled, pattern_str, rule_id))
            except re.error as exc:
                msg = f"Invalid regex '{pattern_str}' (rule {rule_id}): {exc}"
                errors.append(msg)
                logger.warning("regex_compile_error", pattern=pattern_str, rule_id=str(rule_id), error=str(exc))
        logger.info("regex_matcher_loaded", valid=len(self._patterns), invalid=len(errors))
        return errors

    def match(self, text: str) -> list[RegexMatch]:
        """Search *text* against all compiled patterns.

        Args:
            text: The haystack text to scan.

        Returns:
            A :class:`RegexMatch` for every pattern that matches anywhere in *text*.
        """
        if not text:
            return []
        results: list[RegexMatch] = []
        for compiled, pattern_str, rule_id in self._patterns:
            for m in compiled.finditer(text):
                results.append(
                    RegexMatch(
                        keyword=pattern_str,
                        rule_id=rule_id,
                        matched_text=m.group(),
                        start=m.start(),
                        end=m.end(),
                    )
                )
        return results

    @property
    def pattern_count(self) -> int:
        """Number of valid compiled patterns loaded."""
        return len(self._patterns)
