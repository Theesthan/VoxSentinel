"""
Tests for the Aho-Corasick index manager.

Covers edge cases: overlapping patterns, Unicode keywords, empty
input, and automaton rebuild on rule hot-reload.
"""

from __future__ import annotations
