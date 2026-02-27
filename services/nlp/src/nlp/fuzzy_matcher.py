"""
Fuzzy string matching wrapper for VoxSentinel.

Uses RapidFuzz token_set_ratio and partial_ratio to detect approximate
keyword matches with configurable similarity thresholds.
"""

from __future__ import annotations

from rapidfuzz import fuzz
