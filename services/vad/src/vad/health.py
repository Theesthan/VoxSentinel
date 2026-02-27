"""
Health check endpoint for VoxSentinel VAD service.

Exposes a ``/health`` endpoint returning service status and VAD
model readiness.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()

# Will be set by main.py after model load.
_vad_model_loaded: bool = False


def set_model_loaded(loaded: bool) -> None:
    """Update the model-readiness flag."""
    global _vad_model_loaded  # noqa: PLW0603
    _vad_model_loaded = loaded


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return service health including VAD model readiness.

    Returns:
        Dict with ``status``, ``service``, and ``model_loaded`` keys.
    """
    status = "ok" if _vad_model_loaded else "degraded"
    return {
        "status": status,
        "service": "vad",
        "model_loaded": _vad_model_loaded,
    }
