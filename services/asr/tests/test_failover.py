"""
Tests for the ASR failover and circuit breaker logic.

Validates automatic backend switching on consecutive failures,
cooldown periods, and recovery behavior.
"""

from __future__ import annotations
