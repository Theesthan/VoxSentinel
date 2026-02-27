"""
Alert rate limiting and throttling for VoxSentinel.

Enforces configurable rate limits (max N alerts per stream per minute)
and deduplication windows to prevent alert storms.
"""

from __future__ import annotations
