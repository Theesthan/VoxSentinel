"""
Health check endpoint for VoxSentinel diarization service.

Exposes a /health endpoint returning service status and diarization
model readiness.
"""

from __future__ import annotations

from fastapi import APIRouter
