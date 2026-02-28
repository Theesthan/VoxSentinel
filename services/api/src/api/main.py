"""
FastAPI application entry point for VoxSentinel API gateway.

Creates and configures the FastAPI app, registers routers, middleware,
startup/shutdown event handlers, and exposes the ASGI application.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app

from api.middleware.auth import AuthMiddleware
from api.middleware.cors import add_cors
from api.middleware.logging import LoggingMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.routers import (
    alert_channels,
    alerts,
    audit,
    health,
    rules,
    search,
    streams,
    transcripts,
    ws,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    # — Startup —
    redis = None
    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = aioredis.from_url(redis_url, decode_responses=True)
    except Exception:  # pragma: no cover
        pass
    app.state.redis = redis

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://vox:vox@localhost:5432/voxsentinel",
        )
        engine = create_async_engine(db_url, echo=False)
        app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    except Exception:  # pragma: no cover
        app.state.db_session_factory = None

    try:
        from elasticsearch import AsyncElasticsearch

        es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        app.state.es_client = AsyncElasticsearch(es_url)
    except Exception:  # pragma: no cover
        app.state.es_client = None

    yield

    # — Shutdown —
    es = getattr(app.state, "es_client", None)
    if es:
        await es.close()
    r = getattr(app.state, "redis", None)
    if r:
        await r.close()


# ── Prometheus metrics ──
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests received",
    ["method", "endpoint", "status"],
)
api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
)


def create_app() -> FastAPI:
    """Build and return the fully-configured FastAPI application."""
    app = FastAPI(
        title="VoxSentinel API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Routers (under /api/v1 prefix) ──
    api_prefix = "/api/v1"
    app.include_router(streams.router, prefix=api_prefix)
    app.include_router(rules.router, prefix=api_prefix)
    app.include_router(alerts.router, prefix=api_prefix)
    app.include_router(alert_channels.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(transcripts.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)

    # Health + WS are mounted at root (no /api/v1 prefix).
    app.include_router(health.router)
    app.include_router(ws.router)

    # Prometheus metrics endpoint
    app.mount("/metrics", make_asgi_app())

    # ── Middleware (applied outermost-first) ──
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        redis=None,  # will be replaced at startup via app.state
        limit=int(os.getenv("RATE_LIMIT", "100")),
        window=int(os.getenv("RATE_WINDOW", "60")),
    )
    app.add_middleware(AuthMiddleware)
    add_cors(app)

    return app


app = create_app()
