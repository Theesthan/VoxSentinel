"""
Reconnection logic for VoxSentinel ingestion service.

Implements exponential backoff reconnection strategy for stream
disconnections, with configurable max retries and jitter to prevent
thundering herd problems.
"""

from __future__ import annotations

import asyncio

import structlog
