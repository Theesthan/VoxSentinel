"""
Tests for the alert deduplication logic.

Validates cooldown period enforcement, Jaccard distance context
change detection, and correct suppression behavior.
"""

from __future__ import annotations
