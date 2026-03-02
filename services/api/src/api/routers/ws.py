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
    """Accept raw PCM audio from browser microphone and transcribe via Deepgram.

    Protocol:
        1. Client opens WebSocket connection.
        2. Client sends binary PCM frames (16-bit LE mono @ 16000 Hz).
        3. Server relays audio to Deepgram's streaming WebSocket API.
        4. Server sends back JSON transcript tokens as they arrive.
        5. Keyword matching runs on each final transcript; matches are sent
           back and published to Redis match_events channel.
        6. Client closes connection to stop.
    """
    await ws.accept()

    import os
    api_key = os.getenv("TG_DEEPGRAM_API_KEY", "")
    if not api_key:
        await ws.send_text(json.dumps({"error": "TG_DEEPGRAM_API_KEY not configured"}))
        await ws.close(code=1011, reason="Deepgram API key not configured")
        return

    stream_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    redis = getattr(ws.app.state, "redis", None)
    db_session_factory = getattr(ws.app.state, "db_session_factory", None)

    # Load keyword rules for matching
    from api.routers.youtube import (
        _load_keyword_rules,
        _match_keywords,
        _publish_and_dispatch_alerts,
    )
    keyword_rules = await _load_keyword_rules(db_session_factory)

    # Send session info to client
    await ws.send_text(json.dumps({
        "type": "session_started",
        "stream_id": stream_id,
        "session_id": session_id,
    }))

    # Connect to Deepgram's streaming WebSocket API
    import websockets
    dg_url = (
        f"wss://api.deepgram.com/v1/listen"
        f"?model=nova-2&punctuate=true&smart_format=true"
        f"&encoding=linear16&sample_rate=16000&channels=1"
    )
    dg_headers = {"Authorization": f"Token {api_key}"}

    dg_ws = None
    relay_task = None

    try:
        dg_ws = await websockets.connect(dg_url, additional_headers=dg_headers)

        async def _relay_dg_to_client() -> None:
            """Read transcription results from Deepgram, run keyword matching,
            and send both transcript + alert events to browser."""
            try:
                async for message in dg_ws:
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                            # Extract transcript from Deepgram response
                            channel = data.get("channel", {})
                            alternatives = channel.get("alternatives", [])
                            if alternatives:
                                text = alternatives[0].get("transcript", "").strip()
                                is_final = data.get("is_final", False)
                                if text:
                                    token_msg = {
                                        "type": "transcript",
                                        "text": text,
                                        "is_final": is_final,
                                        "confidence": alternatives[0].get("confidence", 0),
                                        "speaker_id": None,
                                    }
                                    await ws.send_text(json.dumps(token_msg))

                                    # Also publish to Redis for transcript viewer
                                    if redis:
                                        await redis.publish(
                                            f"redacted_tokens:{stream_id}",
                                            json.dumps(token_msg),
                                        )

                                    # Keyword matching on final transcripts
                                    if is_final and keyword_rules:
                                        matches = _match_keywords(text, keyword_rules)
                                        if matches:
                                            # Send match events to the client
                                            for m in matches:
                                                alert_msg = {
                                                    "type": "keyword_match",
                                                    "keyword": m["keyword"],
                                                    "severity": m["severity"],
                                                    "match_type": m["match_type"],
                                                    "text": text,
                                                    "stream_id": stream_id,
                                                }
                                                await ws.send_text(json.dumps(alert_msg))

                                            # Publish to Redis + dispatch to channels
                                            await _publish_and_dispatch_alerts(
                                                matches, text,
                                                stream_id, session_id,
                                                stream_name="[Microphone]",
                                                redis=redis,
                                                db_session_factory=db_session_factory,
                                            )
                        except json.JSONDecodeError:
                            pass
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception:
                pass

        relay_task = asyncio.create_task(_relay_dg_to_client())

        # Main loop: receive audio from browser and forward to Deepgram
        while True:
            msg = await ws.receive()

            if msg.get("type") == "websocket.receive":
                if "bytes" in msg and msg["bytes"]:
                    # Forward raw PCM audio to Deepgram
                    try:
                        await dg_ws.send(msg["bytes"])
                    except Exception:
                        break
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
    except Exception as exc:
        try:
            await ws.send_text(json.dumps({"error": f"Mic stream error: {str(exc)[:100]}"}))
        except Exception:
            pass
    finally:
        if relay_task:
            relay_task.cancel()
            try:
                await relay_task
            except asyncio.CancelledError:
                pass
        if dg_ws:
            try:
                # Send close signal to Deepgram
                await dg_ws.send(json.dumps({"type": "CloseStream"}))
                await dg_ws.close()
            except Exception:
                pass
