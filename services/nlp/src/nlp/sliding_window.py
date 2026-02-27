"""
Per-stream sliding text window for VoxSentinel NLP service.

Maintains a rolling window of the last N seconds (default 10 s) of
finalized transcript text per stream for keyword detection. Updates
on each new TranscriptToken arrival.
"""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_WINDOW_SECONDS: float = 10.0


@dataclass
class _Entry:
    """A single finalised transcript fragment with its timing."""

    text: str
    start_s: float
    end_s: float


class SlidingWindow:
    """Per-stream rolling text buffer of the last *window_s* seconds.

    Args:
        window_s: Duration of the sliding window in seconds.
    """

    def __init__(self, window_s: float = DEFAULT_WINDOW_SECONDS) -> None:
        self._window_s = window_s
        self._entries: list[_Entry] = []

    # ── public API ──

    def append(self, text: str, start_s: float, end_s: float) -> str:
        """Add a finalised transcript fragment and return the current window text.

        Args:
            text: The finalized transcript text.
            start_s: Start time in seconds (stream-relative offset).
            end_s: End time in seconds (stream-relative offset).

        Returns:
            Concatenated text of all entries currently within the window.
        """
        self._entries.append(_Entry(text=text, start_s=start_s, end_s=end_s))
        self._evict(end_s)
        return self.get_text()

    def get_text(self) -> str:
        """Return the current window text (space-joined fragments)."""
        return " ".join(e.text for e in self._entries if e.text)

    def clear(self) -> None:
        """Remove all entries from the window."""
        self._entries.clear()

    @property
    def entry_count(self) -> int:
        """Number of fragments currently in the window."""
        return len(self._entries)

    # ── internal ──

    def _evict(self, latest_end_s: float) -> None:
        """Drop entries whose *end_s* is older than the window boundary."""
        cutoff = latest_end_s - self._window_s
        self._entries = [e for e in self._entries if e.end_s > cutoff]
