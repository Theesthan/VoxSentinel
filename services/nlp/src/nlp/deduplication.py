"""
Alert deduplication logic for VoxSentinel NLP service.

Prevents re-alerting for the same keyword within a configurable
cooldown period unless surrounding context changes by more than
30% (measured via Jaccard distance).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

DEFAULT_COOLDOWN_S: float = 10.0
CONTEXT_CHANGE_THRESHOLD: float = 0.30


def _jaccard_distance(a: str, b: str) -> float:
    """Compute Jaccard distance between word sets of two strings."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 0.0
    return 1.0 - len(intersection) / len(union)


@dataclass
class _DeduplicationEntry:
    """Tracks the last alert time and context for a (stream_id, keyword, match_type) key."""

    last_alert_time: float
    last_context: str


class Deduplicator:
    """Suppresses duplicate keyword alerts within a cooldown window.

    A repeat alert for the same ``(stream_id, keyword, match_type)`` is
    suppressed for *cooldown_s* seconds unless the surrounding context
    changes by more than 30% (Jaccard distance).

    Args:
        cooldown_s: Cooldown period in seconds.
    """

    def __init__(self, cooldown_s: float = DEFAULT_COOLDOWN_S) -> None:
        self._cooldown_s = cooldown_s
        self._cache: dict[str, _DeduplicationEntry] = {}

    def should_suppress(
        self,
        stream_id: str,
        keyword: str,
        match_type: str,
        context: str,
    ) -> bool:
        """Return ``True`` if this alert should be suppressed.

        Args:
            stream_id: Stream identifier.
            keyword: The matched keyword.
            match_type: Matching mode (exact/fuzzy/regex).
            context: Surrounding transcript context.

        Returns:
            ``True`` to suppress (duplicate), ``False`` to emit.
        """
        key = f"{stream_id}:{keyword}:{match_type}"
        now = time.monotonic()
        entry = self._cache.get(key)

        if entry is None:
            self._cache[key] = _DeduplicationEntry(last_alert_time=now, last_context=context)
            return False

        elapsed = now - entry.last_alert_time
        if elapsed > self._cooldown_s:
            # Cooldown expired — allow
            entry.last_alert_time = now
            entry.last_context = context
            return False

        # Within cooldown — check if context changed significantly
        distance = _jaccard_distance(entry.last_context, context)
        if distance > CONTEXT_CHANGE_THRESHOLD:
            entry.last_alert_time = now
            entry.last_context = context
            return False

        # Suppress
        return True

    def clear(self) -> None:
        """Clear all deduplication state."""
        self._cache.clear()
