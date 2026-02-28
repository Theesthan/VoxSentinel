"""
Health check endpoint for VoxSentinel diarization service.

Exposes a /health endpoint returning service status and diarization
model readiness.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_pipeline: object | None = None


def configure(pipeline: object) -> None:
    """Inject the ``PyannotePipeline`` instance for readiness checks.

    Args:
        pipeline: A ``PyannotePipeline`` with an ``is_ready`` property.
    """
    global _pipeline
    _pipeline = pipeline


@router.get("/health")
async def health() -> JSONResponse:
    """Return service health and model readiness."""
    ready = getattr(_pipeline, "is_ready", False) if _pipeline else False
    return JSONResponse(
        content={
            "service": "diarization",
            "pipeline_ready": ready,
            "status": "ok" if ready else "degraded",
        },
        status_code=200,
    )
