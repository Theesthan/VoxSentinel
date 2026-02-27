"""
Health check endpoint for VoxSentinel VAD service.

Exposes a /health endpoint returning service status and VAD model
readiness.
"""

from __future__ import annotations

from fastapi import APIRouter
