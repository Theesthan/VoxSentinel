"""
Health check endpoint for VoxSentinel NLP service.

Exposes a /health endpoint returning service status, model readiness,
and keyword rule count.
"""

from __future__ import annotations

from fastapi import APIRouter
