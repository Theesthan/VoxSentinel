"""
Storage service entry point for VoxSentinel.

Initializes database connections, Elasticsearch client, subscribes to
transcript and alert event streams, and exposes health and metrics
endpoints.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI

from storage.health import router as health_router

logger = structlog.get_logger(__name__)


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
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "storage.main:app",
        host="0.0.0.0",
        port=8007,
        log_level="info",
    )
