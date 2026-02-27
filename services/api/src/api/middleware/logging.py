"""
Request logging middleware for VoxSentinel API.

Logs all incoming requests and responses with structured JSON format,
including correlation IDs, latency, and status codes.
"""

from __future__ import annotations

import structlog
