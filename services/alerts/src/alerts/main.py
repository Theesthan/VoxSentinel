"""
Alert service entry point for VoxSentinel.

Initializes the alert dispatch service, loads channel configurations,
subscribes to match/sentiment/compliance event streams, and exposes
health and metrics endpoints.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI

from .health import router as health_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle for the alerts service."""
    logger.info("alerts_service_starting")
    yield
    logger.info("alerts_service_stopping")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="VoxSentinel Alerts Service", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "alerts.main:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
    )
