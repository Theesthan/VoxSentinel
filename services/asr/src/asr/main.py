"""
ASR service entry point for VoxSentinel.

Initializes the ASR engine registry, loads configured backends,
subscribes to speech chunk streams from VAD, and exposes health
and metrics endpoints.
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

from asr.engine_registry import get_engine_class, register_engine
from asr.engines.deepgram_nova2 import DeepgramNova2Engine
from asr.engines.whisper_v3_turbo import WhisperV3TurboEngine
from asr.failover import ASRFailoverManager
from asr.health import router as health_router
from asr.health import set_engine_status
from asr.router import ASRRouter

logger = structlog.get_logger()

_redis_client: RedisClient | None = None
_primary_engine: Any = None
_fallback_engine: Any = None
_failover_manager: ASRFailoverManager | None = None
_tasks: dict[str, asyncio.Task[None]] = {}
_stop_events: dict[str, asyncio.Event] = {}


def _register_default_engines() -> None:
    """Register built-in ASR engine classes."""
    register_engine("deepgram_nova2", DeepgramNova2Engine)
    register_engine("whisper_v3_turbo", WhisperV3TurboEngine)


async def _create_engine(name: str) -> Any:
    """Instantiate and connect the engine identified by *name*."""
    settings = get_settings()
    cls = get_engine_class(name)

    if name == "deepgram_nova2":
        engine = cls(api_key=settings.deepgram_api_key)
    elif name == "whisper_v3_turbo":
        engine = cls()
    else:
        engine = cls()

    await engine.connect()
    set_engine_status(name, True)
    return engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: register engines, connect, start routers."""
    global _redis_client, _primary_engine, _fallback_engine, _failover_manager  # noqa: PLW0603

    settings = get_settings()

    # ── startup ──
    _register_default_engines()

    try:
        _primary_engine = await _create_engine(settings.asr_default_backend)
    except Exception:
        logger.error(
            "asr_primary_engine_init_failed",
            engine=settings.asr_default_backend,
            exc_info=True,
        )
        set_engine_status(settings.asr_default_backend, False)

    try:
        if settings.asr_fallback_backend:
            _fallback_engine = await _create_engine(settings.asr_fallback_backend)
    except Exception:
        logger.warning(
            "asr_fallback_engine_init_failed",
            engine=settings.asr_fallback_backend,
            exc_info=True,
        )
        if settings.asr_fallback_backend:
            set_engine_status(settings.asr_fallback_backend, False)

    _failover_manager = ASRFailoverManager(
        primary=_primary_engine,
        fallback=_fallback_engine,
    )

    _redis_client = RedisClient()
    await _redis_client.connect()

    logger.info(
        "asr_startup",
        primary=settings.asr_default_backend,
        fallback=settings.asr_fallback_backend,
    )

    await _load_active_streams(settings.api_host, settings.api_port)

    yield

    # ── shutdown ──
    logger.info("asr_shutdown")
    for evt in _stop_events.values():
        evt.set()
    for task in _tasks.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _tasks.clear()
    _stop_events.clear()

    if _primary_engine is not None:
        await _primary_engine.disconnect()
    if _fallback_engine is not None:
        await _fallback_engine.disconnect()
    await _redis_client.close()


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="VoxSentinel ASR Service", lifespan=lifespan)
    app.include_router(health_router)

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    return app


async def _load_active_streams(api_host: str, api_port: int) -> None:
    """Fetch active streams from the API gateway and start ASR routers."""
    url = f"http://{api_host}:{api_port}/api/v1/streams"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"status": StreamStatus.ACTIVE.value})
            resp.raise_for_status()

        streams_data: list[dict[str, Any]] = resp.json()
        for item in streams_data:
            sid = str(item.get("stream_id", ""))
            if sid:
                _start_router(sid)
        logger.info("asr_active_streams_loaded", count=len(streams_data))
    except Exception:
        logger.warning("asr_active_streams_load_failed", url=url, exc_info=True)


def _start_router(stream_id: str) -> None:
    """Spawn an ``ASRRouter`` task for *stream_id*."""
    if stream_id in _tasks and not _tasks[stream_id].done():
        return

    stop_event = asyncio.Event()
    _stop_events[stream_id] = stop_event

    asr_router = ASRRouter(
        redis_client=_redis_client,
        failover_manager=_failover_manager,
    )
    task = asyncio.create_task(
        asr_router.process_stream(stream_id, stop_event=stop_event),
        name=f"asr-{stream_id}",
    )
    _tasks[stream_id] = task
    logger.info("asr_router_spawned", stream_id=stream_id)


app = create_app()


def main() -> None:
    """Run the ASR service with Uvicorn."""
    settings = get_settings()
    uvicorn.run(
        "asr.main:app",
        host="0.0.0.0",
        port=8003,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
