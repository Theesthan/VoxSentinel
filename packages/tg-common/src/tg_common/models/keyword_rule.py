"""
Keyword rule data model for VoxSentinel.

Defines the Pydantic model for configurable keyword detection rules,
supporting exact (Aho-Corasick), fuzzy (RapidFuzz), and regex matching
modes with severity levels and category groupings.
"""

from __future__ import annotations

from pydantic import BaseModel
