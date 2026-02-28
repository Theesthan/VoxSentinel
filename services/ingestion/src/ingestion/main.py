"""
Ingestion service entry point for VoxSentinel.

Starts a FastAPI application that:

* Exposes ``/health`` and ``/metrics`` endpoints.
* On startup, fetches active streams from the API gateway and
  starts an ingestion pipeline for each.
* All logging is structured via ``structlog``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from tg_common.config import get_settings
from tg_common.messaging.redis_client import RedisClient
from tg_common.models.stream import Stream, StreamStatus

from ingestion.health import router as health_router
from ingestion.stream_manager import StreamManager

logger = structlog.get_logger()

# Module-level references set during lifespan.
_redis_client: RedisClient | None = None
_stream_manager: StreamManager | None = None


def get_stream_manager() -> StreamManager:
    """Return the global ``StreamManager`` instance.

    Raises:
        RuntimeError: If the application has not started yet.
    """
    if _stream_manager is None:
        raise RuntimeError("StreamManager not initialised.")
    return _stream_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: connect Redis, load active streams, shut down."""
    global _redis_client, _stream_manager  # noqa: PLW0603

    settings = get_settings()

    # ── startup ──
    _redis_client = RedisClient()
    await _redis_client.connect()
    _stream_manager = StreamManager(_redis_client)

    logger.info("ingestion_startup", api_host=settings.api_host, api_port=settings.api_port)

    # Fetch active streams from the API gateway and start them.
    await _load_active_streams(_stream_manager, settings.api_host, settings.api_port)

    yield

    # ── shutdown ──
    logger.info("ingestion_shutdown")
    await _stream_manager.stop_all()
    await _redis_client.close()


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="VoxSentinel Ingestion Service", lifespan=lifespan)
    app.include_router(health_router)

    # Mount Prometheus metrics endpoint.
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


async def _load_active_streams(
    manager: StreamManager,
    api_host: str,
    api_port: int,
) -> None:
    """Fetch active streams from the API gateway and start ingestion.

    Args:
        manager: The ``StreamManager`` instance.
        api_host: API gateway host.
        api_port: API gateway port.
    """
    url = f"http://{api_host}:{api_port}/api/v1/streams"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"status": StreamStatus.ACTIVE.value})
            resp.raise_for_status()

        streams_data: list[dict[str, Any]] = resp.json()
        for item in streams_data:
            stream = Stream(**item)
            await manager.start_stream(stream)
        logger.info("active_streams_loaded", count=len(streams_data))
    except Exception:
        logger.warning("active_streams_load_failed", url=url, exc_info=True)


app = create_app()


def main() -> None:
    """Run the ingestion service with Uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "ingestion.main:app",
        host="0.0.0.0",
        port=8001,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
