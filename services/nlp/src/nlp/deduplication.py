"""
Alert deduplication logic for VoxSentinel NLP service.

Prevents re-alerting for the same keyword within a configurable
cooldown period unless surrounding context changes by more than
30% (measured via Jaccard distance).
"""

from __future__ import annotations
