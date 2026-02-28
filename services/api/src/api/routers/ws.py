"""
WebSocket endpoints for VoxSentinel API.

Provides real-time WebSocket streams for live transcript tokens,
alert events, and sentiment updates per stream and cross-stream.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


async def _redis_listener(
    ws: WebSocket, redis: Any, channels: list[str],
) -> None:
    """Subscribe to Redis pub/sub *channels* and forward JSON to *ws*."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(*channels)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await ws.send_text(data)
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()


@router.websocket("/ws/streams/{stream_id}/transcript")
async def stream_transcript(
    ws: WebSocket,
    stream_id: UUID,
) -> None:
    await ws.accept()
    redis = getattr(ws.app.state, "redis", None)
    if redis is None:
        await ws.close(code=1011, reason="Redis unavailable")
        return

    channels = [
        f"enriched_tokens:{stream_id}",
        f"match_events:{stream_id}",
    ]
    listener = asyncio.create_task(_redis_listener(ws, redis, channels))
    try:
        while True:
            # Keep connection alive; client may send pings.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:
            pass


@router.websocket("/ws/alerts")
async def live_alerts(ws: WebSocket) -> None:
    await ws.accept()
    redis = getattr(ws.app.state, "redis", None)
    if redis is None:
        await ws.close(code=1011, reason="Redis unavailable")
        return

    # Subscribe to all match_events channels.
    pubsub = redis.pubsub()
    await pubsub.psubscribe("match_events:*")
    listener_task: asyncio.Task[None] | None = None

    async def _forward() -> None:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await ws.send_text(data)

    listener_task = asyncio.create_task(_forward())
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if listener_task:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
        await pubsub.punsubscribe("match_events:*")
        await pubsub.close()
