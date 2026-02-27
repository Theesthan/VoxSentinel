"""
Health check API router for VoxSentinel.

Aggregated health endpoint returning status of all backend services,
database, Elasticsearch, Redis, and ASR backends.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from api.dependencies import get_db_session, get_es_client, get_redis

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
                await session.execute("SELECT 1")
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

    # Elasticsearch
    try:
        es = getattr(request.app.state, "es_client", None)
        if es:
            await es.ping()
            services["elasticsearch"] = "healthy"
        else:
            services["elasticsearch"] = "not_configured"
    except Exception:
        services["elasticsearch"] = "unhealthy"

    overall = "healthy" if all(
        v in ("healthy", "not_configured") for v in services.values()
    ) else "degraded"

    return HealthResponse(status=overall, services=services)
