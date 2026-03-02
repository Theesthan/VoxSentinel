"""
WebSocket endpoints for VoxSentinel API.

Provides real-time WebSocket streams for live transcript tokens,
alert events, sentiment updates per stream, and browser microphone
audio ingestion.
"""

from __future__ import annotations

import asyncio
import json
import uuid
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
        f"redacted_tokens:{stream_id}",
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


@router.websocket("/ws/mic")
async def mic_stream(ws: WebSocket) -> None:
    """Accept raw PCM audio from browser microphone and push through pipeline.

    Protocol:
        1. Client sends initial JSON config: ``{"sample_rate": 16000, "asr_backend": "deepgram_nova2"}``
        2. Client sends binary PCM frames (16-bit LE mono @ configured sample_rate).
        3. Server replies with JSON transcript tokens as they arrive from ASR.
        4. Client sends ``{"action": "stop"}`` to end the session.

    Audio is pushed to ``audio_chunks:{stream_id}`` Redis stream so the
    existing VAD → ASR → NLP pipeline processes it identically to RTSP/file inputs.
    """
    await ws.accept()
    redis = getattr(ws.app.state, "redis", None)
    if redis is None:
        await ws.close(code=1011, reason="Redis unavailable")
        return

    # Wait for initial config message
    try:
        config_raw = await ws.receive_text()
        config = json.loads(config_raw)
    except Exception:
        await ws.close(code=1008, reason="Expected JSON config as first message")
        return

    sample_rate = config.get("sample_rate", 16000)
    asr_backend = config.get("asr_backend", "deepgram_nova2")

    stream_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Notify pipeline about the new mic stream
    await redis.publish(
        "stream_started",
        json.dumps({
            "stream_id": stream_id,
            "session_id": session_id,
            "source_type": "mic",
            "source_url": "browser_mic",
            "asr_backend": asr_backend,
            "sample_rate": sample_rate,
        }),
    )

    # Register in active streams
    await redis.sadd(
        "active_streams",
        json.dumps({"stream_id": stream_id, "session_id": session_id}),
    )

    # Send stream_id back to client so they can track it
    await ws.send_text(json.dumps({
        "type": "session_started",
        "stream_id": stream_id,
        "session_id": session_id,
    }))

    # Subscribe to enriched tokens for this stream to relay back to client
    pubsub = redis.pubsub()
    await pubsub.subscribe(
        f"enriched_tokens:{stream_id}",
        f"match_events:{stream_id}",
    )

    async def _relay_results() -> None:
        """Forward enriched tokens from Redis back to the WebSocket client."""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    await ws.send_text(data)
        except (asyncio.CancelledError, Exception):
            pass

    relay_task = asyncio.create_task(_relay_results())

    # Main loop: receive audio frames or control messages
    chunk_seq = 0
    try:
        while True:
            msg = await ws.receive()

            if msg.get("type") == "websocket.receive":
                # Binary = audio data
                if "bytes" in msg and msg["bytes"]:
                    audio_data = msg["bytes"]
                    await redis.xadd(
                        f"audio_chunks:{stream_id}",
                        {
                            "data": audio_data.decode("latin-1") if isinstance(audio_data, bytes) else audio_data,
                            "seq": str(chunk_seq),
                            "session_id": session_id,
                        },
                        maxlen=5000,
                    )
                    chunk_seq += 1

                # Text = control message
                elif "text" in msg and msg["text"]:
                    try:
                        ctrl = json.loads(msg["text"])
                        if ctrl.get("action") == "stop":
                            break
                    except json.JSONDecodeError:
                        pass
            elif msg.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    finally:
        relay_task.cancel()
        try:
            await relay_task
        except asyncio.CancelledError:
            pass
        await pubsub.unsubscribe(
            f"enriched_tokens:{stream_id}",
            f"match_events:{stream_id}",
        )
        await pubsub.close()

        # Remove from active streams and signal completion
        await redis.srem(
            "active_streams",
            json.dumps({"stream_id": stream_id, "session_id": session_id}),
        )
        await redis.publish(
            "stream_stopped",
            json.dumps({"stream_id": stream_id, "session_id": session_id}),
        )
