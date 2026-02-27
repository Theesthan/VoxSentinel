"""
Tests for the sliding window module.

Validates text accumulation, eviction based on time, and clearing.
"""

from __future__ import annotations

import pytest

from nlp.sliding_window import SlidingWindow


class TestSlidingWindow:
    """Tests for SlidingWindow."""

    def test_append_returns_text(self) -> None:
        window = SlidingWindow(window_s=10.0)
        text = window.append("hello", 0.0, 1.0)
        assert text == "hello"

    def test_append_accumulates(self) -> None:
        window = SlidingWindow(window_s=10.0)
        window.append("hello", 0.0, 1.0)
        text = window.append("world", 1.0, 2.0)
        assert text == "hello world"

    def test_evicts_old_entries(self) -> None:
        window = SlidingWindow(window_s=5.0)
        window.append("old text", 0.0, 1.0)
        window.append("mid text", 2.0, 3.0)
        text = window.append("new text", 10.0, 11.0)
        # old and mid should be evicted (end_s <= 11.0 - 5.0 = 6.0)
        assert text == "new text"

    def test_keeps_entries_within_window(self) -> None:
        window = SlidingWindow(window_s=10.0)
        window.append("first", 0.0, 1.0)
        window.append("second", 1.0, 2.0)
        text = window.append("third", 2.0, 3.0)
        assert text == "first second third"

    def test_clear(self) -> None:
        window = SlidingWindow(window_s=10.0)
        window.append("hello", 0.0, 1.0)
        window.clear()
        assert window.get_text() == ""
        assert window.entry_count == 0

    def test_entry_count(self) -> None:
        window = SlidingWindow(window_s=10.0)
        assert window.entry_count == 0
        window.append("hello", 0.0, 1.0)
        assert window.entry_count == 1
        window.append("world", 1.0, 2.0)
        assert window.entry_count == 2

    def test_empty_text_fragments(self) -> None:
        window = SlidingWindow(window_s=10.0)
        window.append("", 0.0, 1.0)
        window.append("hello", 1.0, 2.0)
        text = window.get_text()
        assert "hello" in text

    def test_exact_boundary_eviction(self) -> None:
        window = SlidingWindow(window_s=5.0)
        window.append("boundary", 0.0, 5.0)
        text = window.append("new", 5.0, 10.0)
        # entry at end_s=5.0, cutoff = 10.0-5.0=5.0, 5.0 > 5.0 is False → evicted
        assert text == "new"
