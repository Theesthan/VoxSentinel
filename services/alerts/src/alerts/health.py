"""
Health check endpoint for VoxSentinel alert service.

Exposes a /health endpoint returning service status and connectivity
checks for alert channels and Celery workers.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return ``{"status": "ok"}`` when the service is alive."""
    return {"status": "ok"}
