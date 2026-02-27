"""
Aho-Corasick automaton index manager for VoxSentinel.

Builds and maintains the Aho-Corasick automaton for O(n) exact
multi-pattern matching across configured keyword rules. Supports
hot-reload when keyword configurations change.
"""

from __future__ import annotations

import ahocorasick
