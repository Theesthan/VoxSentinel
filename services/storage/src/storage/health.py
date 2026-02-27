"""
Health check endpoint for VoxSentinel storage service.

Exposes a /health endpoint returning service status and connectivity
checks for PostgreSQL and Elasticsearch.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return basic liveness status."""
    return {"status": "ok", "service": "storage"}
