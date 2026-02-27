"""
Keyword detection engine for VoxSentinel.

Orchestrates all three matching modes (Aho-Corasick exact, RapidFuzz
fuzzy, and regex) against the per-stream sliding transcript window.
Emits KeywordMatchEvent objects for all matches found.
"""

from __future__ import annotations

import structlog
