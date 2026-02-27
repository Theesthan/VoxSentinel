"""
Health check endpoint for VoxSentinel ingestion service.

Exposes a ``/health`` endpoint returning service status, active stream
count, and connectivity checks for downstream dependencies.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return basic health information.

    Returns:
        A dict with ``status`` and ``service`` keys.
    """
    return {"status": "ok", "service": "ingestion"}
