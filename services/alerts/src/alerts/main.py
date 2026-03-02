"""
Alert service entry point for VoxSentinel.

Initializes the alert dispatch service, loads channel configurations,
subscribes to match/sentiment/compliance event streams, and exposes
health and metrics endpoints.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import Counter, make_asgi_app

from .health import router as health_router
from .dispatcher import AlertDispatcher
from .throttle import AlertThrottle
from .channels.websocket_channel import WebSocketChannel
from .channels.webhook_channel import WebhookChannel
from .channels.slack_channel import SlackChannel

logger = structlog.get_logger()

# ── Prometheus metrics ──
alerts_dispatched_total = Counter(
    "alerts_dispatched_total",
    "Total alerts dispatched by the alert service",
    ["channel", "severity"],
)
alerts_dispatch_errors_total = Counter(
    "alerts_dispatch_errors_total",
    "Total alert dispatch failures",
    ["channel"],
)

# ── Service-level singletons ──
_dispatcher: AlertDispatcher | None = None
_listener_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle for the alerts service."""
    global _dispatcher, _listener_task

    logger.info("alerts_service_starting")

    # ── Connect Redis ──
    import redis.asyncio as aioredis

    redis_url = os.getenv("TG_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    redis = aioredis.from_url(redis_url, decode_responses=True)
    app.state.redis = redis

    # ── Build channels ──
    channels = []
    ws_channel = WebSocketChannel()
    ws_channel.enabled = True
    channels.append(ws_channel)

    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        wh_channel = WebhookChannel(url=webhook_url)
        wh_channel.enabled = True
        channels.append(wh_channel)

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook_url:
        slack_ch = SlackChannel(webhook_url=slack_webhook_url)
        slack_ch.enabled = True
        channels.append(slack_ch)

    # ── Build throttle + dispatcher ──
    throttle = AlertThrottle(
        redis,
        max_per_minute=int(os.getenv("ALERT_MAX_PER_MINUTE", "30")),
        dedup_ttl_s=int(os.getenv("ALERT_DEDUP_TTL_S", "10")),
    )

    _dispatcher = AlertDispatcher(
        throttle=throttle,
        channels=channels,
    )

    # ── Subscribe to Redis pub/sub and start listener ──
    pubsub = redis.pubsub()
    await pubsub.psubscribe("match_events:*", "sentiment_events:*")
    _listener_task = asyncio.create_task(_dispatcher.listen(pubsub))
    logger.info("alerts_dispatcher_listening", channels=[ch.name for ch in channels])

    yield

    # ── Shutdown ──
    logger.info("alerts_service_stopping")
    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass

    for ch in channels:
        try:
            await ch.close()
        except Exception:
            pass

    await redis.close()
    logger.info("alerts_service_stopped")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="VoxSentinel Alerts Service", lifespan=lifespan)
    app.include_router(health_router)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8006,
        reload=False,
    )
