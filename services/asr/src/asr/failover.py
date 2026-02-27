"""
Circuit breaker and failover logic for VoxSentinel ASR service.

Implements the circuit breaker pattern for ASR backend connections,
tracking consecutive failures and automatically switching to fallback
backends when the primary is unavailable.
"""

from __future__ import annotations

import structlog
