"""
Rate limiting middleware for VoxSentinel API.

Enforces configurable request rate limits (default 100 req/min
per API key) to prevent abuse and ensure fair resource usage.
"""

from __future__ import annotations

from fastapi import Request
