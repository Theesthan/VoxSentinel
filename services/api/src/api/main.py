"""
FastAPI application entry point for VoxSentinel API gateway.

Creates and configures the FastAPI app, registers routers, middleware,
startup/shutdown event handlers, and exposes the ASGI application.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

# Load .env file from project root (VoxSentinel/) if dotenv is available
try:
    from dotenv import load_dotenv
    # Walk up from src/api/main.py to find the .env file
    _env_candidates = [
        Path(__file__).resolve().parents[3] / ".env",  # services/api/src -> services -> .env? no
        Path(__file__).resolve().parents[4] / ".env",  # -> VoxSentinel/.env
        Path(__file__).resolve().parents[5] / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path.cwd().parent.parent / ".env",
        Path.cwd().parent.parent.parent / ".env",
    ]
    for _env_path in _env_candidates:
        if _env_path.exists():
            load_dotenv(_env_path, override=False)
            break
except ImportError:
    pass

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
    file_analyze,
    health,
    rules,
    streams,
    transcripts,
    ws,
    youtube,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    # — Startup —
    redis = None
    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("TG_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        redis = aioredis.from_url(redis_url, decode_responses=True)
    except Exception:  # pragma: no cover
        pass
    app.state.redis = redis

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        db_url = os.getenv(
            "TG_DB_URI",
            os.getenv("DATABASE_URL", "postgresql+asyncpg://voxsentinel:changeme@localhost:5432/voxsentinel"),
        )
        # Railway (and most cloud providers) supply postgresql:// — asyncpg requires postgresql+asyncpg://
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(db_url, echo=False)
        app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    except Exception:  # pragma: no cover
        app.state.db_session_factory = None

    yield

    # — Shutdown —
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
    app.include_router(transcripts.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)
    app.include_router(file_analyze.router, prefix=api_prefix)
    app.include_router(youtube.router, prefix=api_prefix)

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
