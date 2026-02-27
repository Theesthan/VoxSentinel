"""
VAD service entry point for VoxSentinel.

Starts a FastAPI application that:

* Loads the Silero VAD model on startup.
* Fetches active streams from the API gateway and spawns a
  ``VADProcessor`` task per stream.
* Exposes ``/health`` and ``/metrics`` endpoints.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from tg_common.config import get_settings
from tg_common.messaging.redis_client import RedisClient
from tg_common.models.stream import StreamStatus

from vad.health import router as health_router
from vad.health import set_model_loaded
from vad.silero_vad import SileroVADModel
from vad.vad_processor import VADProcessor

logger = structlog.get_logger()

_redis_client: RedisClient | None = None
_vad_model: SileroVADModel | None = None
_tasks: dict[str, asyncio.Task[None]] = {}
_stop_events: dict[str, asyncio.Event] = {}


def get_vad_model() -> SileroVADModel:
    """Return the global ``SileroVADModel`` instance."""
    if _vad_model is None:
        raise RuntimeError("VAD model not initialised.")
    return _vad_model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: load model, connect Redis, start processors."""
    global _redis_client, _vad_model  # noqa: PLW0603

    settings = get_settings()

    # ── startup ──
    _vad_model = SileroVADModel()
    _vad_model.load()
    set_model_loaded(True)

    _redis_client = RedisClient()
    await _redis_client.connect()

    logger.info("vad_startup", threshold=settings.vad_threshold)

    # Fetch active streams and spawn processors.
    await _load_active_streams(settings.api_host, settings.api_port)

    yield

    # ── shutdown ──
    logger.info("vad_shutdown")
    for sid, evt in _stop_events.items():
        evt.set()
    for task in _tasks.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _tasks.clear()
    _stop_events.clear()
    await _redis_client.close()


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="VoxSentinel VAD Service", lifespan=lifespan)
    app.include_router(health_router)

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    return app


async def _load_active_streams(api_host: str, api_port: int) -> None:
    """Fetch active streams from the API gateway and start VAD processors."""
    url = f"http://{api_host}:{api_port}/api/v1/streams"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"status": StreamStatus.ACTIVE.value})
            resp.raise_for_status()

        streams_data: list[dict[str, Any]] = resp.json()
        for item in streams_data:
            sid = str(item.get("stream_id", ""))
            if sid:
                _start_processor(sid)
        logger.info("vad_active_streams_loaded", count=len(streams_data))
    except Exception:
        logger.warning("vad_active_streams_load_failed", url=url, exc_info=True)


def _start_processor(stream_id: str) -> None:
    """Spawn a ``VADProcessor`` task for *stream_id*."""
    if stream_id in _tasks and not _tasks[stream_id].done():
        return

    stop_event = asyncio.Event()
    _stop_events[stream_id] = stop_event

    processor = VADProcessor(
        vad_model=get_vad_model(),
        redis_client=_redis_client,  # type: ignore[arg-type]
    )
    task = asyncio.create_task(
        processor.process_stream(stream_id, stop_event=stop_event),
        name=f"vad-{stream_id}",
    )
    _tasks[stream_id] = task
    logger.info("vad_processor_spawned", stream_id=stream_id)


app = create_app()


def main() -> None:
    """Run the VAD service with Uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "vad.main:app",
        host="0.0.0.0",
        port=8002,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
