"""
Health check endpoint for VoxSentinel ASR service.

Exposes a ``/health`` endpoint returning service status and connectivity
checks for all configured ASR backends.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()

# Populated by main.py after engine initialisation.
_engine_status: dict[str, bool] = {}


def set_engine_status(name: str, ready: bool) -> None:
    """Update the readiness flag for an engine."""
    _engine_status[name] = ready


def get_engine_status() -> dict[str, bool]:
    """Return the current engine readiness map."""
    return dict(_engine_status)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return service health including ASR engine readiness.

    Returns:
        Dict with ``status``, ``service``, and ``engines`` keys.
    """
    all_ok = bool(_engine_status) and any(_engine_status.values())
    status = "ok" if all_ok else "degraded"
    return {
        "status": status,
        "service": "asr",
        "engines": dict(_engine_status),
    }
