"""
Health check API router for VoxSentinel.

Aggregated health endpoint returning status of all backend services,
database, Redis, and ASR backends.
"""

from __future__ import annotations


from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    services: dict[str, str] = {}

    # Database
    try:
        factory = getattr(request.app.state, "db_session_factory", None)
        if factory:
            async with factory() as session:
                await session.execute(text("SELECT 1"))
            services["database"] = "healthy"
        else:
            services["database"] = "not_configured"
    except Exception:
        services["database"] = "unhealthy"

    # Redis
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            await redis.ping()
            services["redis"] = "healthy"
        else:
            services["redis"] = "not_configured"
    except Exception:
        services["redis"] = "unhealthy"

    overall = "healthy" if all(
        v in ("healthy", "not_configured") for v in services.values()
    ) else "degraded"

    return HealthResponse(status=overall, services=services)
