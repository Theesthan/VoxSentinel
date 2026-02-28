"""
Storage service entry point for VoxSentinel.

Initializes database connections, Elasticsearch client, subscribes to
transcript and alert event streams, and exposes health and metrics
endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app

from storage.health import router as health_router

logger = structlog.get_logger(__name__)

# ── Prometheus metrics ──
storage_writes_total = Counter(
    "storage_writes_total",
    "Total records written to PostgreSQL",
    ["table"],
)
storage_es_indexes_total = Counter(
    "storage_es_indexes_total",
    "Total documents indexed in Elasticsearch",
    ["index"],
)
storage_write_duration_seconds = Histogram(
    "storage_write_duration_seconds",
    "Time spent writing a record to storage",
    ["backend"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup / shutdown of background workers."""
    logger.info("storage_service_starting")
    yield
    logger.info("storage_service_stopping")


def create_app() -> FastAPI:
    """Build the FastAPI application with health routes."""
    app = FastAPI(title="VoxSentinel Storage", lifespan=lifespan)
    app.include_router(health_router)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8007,
        log_level="info",
    )
