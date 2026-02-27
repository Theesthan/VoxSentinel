"""
Tests for the WebSocket alert channel.

Validates real-time alert push to connected clients and connection
lifecycle management.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from alerts.channels.websocket_channel import WebSocketChannel


# ── registration ──


class TestWebSocketRegistration:
    """Client registration / unregistration tests."""

    def test_register_adds_client(self, stream_id: str) -> None:
        ch = WebSocketChannel()
        ws = MagicMock()
        ch.register(stream_id, ws)
        assert ws in ch.clients[stream_id]

    def test_register_multiple_clients_same_stream(self, stream_id: str) -> None:
        ch = WebSocketChannel()
        ws1, ws2 = MagicMock(), MagicMock()
        ch.register(stream_id, ws1)
        ch.register(stream_id, ws2)
        assert len(ch.clients[stream_id]) == 2

    def test_unregister_removes_client(self, stream_id: str) -> None:
        ch = WebSocketChannel()
        ws = MagicMock()
        ch.register(stream_id, ws)
        ch.unregister(stream_id, ws)
        assert stream_id not in ch.clients

    def test_unregister_nonexistent_client_no_error(self, stream_id: str) -> None:
        ch = WebSocketChannel()
        ch.unregister(stream_id, MagicMock())  # should not raise

    def test_unregister_leaves_other_clients(self, stream_id: str) -> None:
        ch = WebSocketChannel()
        ws1, ws2 = MagicMock(), MagicMock()
        ch.register(stream_id, ws1)
        ch.register(stream_id, ws2)
        ch.unregister(stream_id, ws1)
        assert ws2 in ch.clients[stream_id]
        assert ws1 not in ch.clients[stream_id]


# ── broadcast ──


class TestWebSocketBroadcast:
    """Test alert broadcast to connected clients."""

    async def test_broadcast_sends_to_all_clients(self, stream_id: str, sample_alert) -> None:
        ch = WebSocketChannel()
        ws1, ws2 = AsyncMock(), AsyncMock()
        ch.register(stream_id, ws1)
        ch.register(stream_id, ws2)

        count = await ch.broadcast(stream_id, sample_alert)
        assert count == 2
        ws1.send.assert_awaited_once()
        ws2.send.assert_awaited_once()

    async def test_broadcast_returns_zero_when_no_clients(
        self, stream_id: str, sample_alert
    ) -> None:
        ch = WebSocketChannel()
        count = await ch.broadcast(stream_id, sample_alert)
        assert count == 0

    async def test_broadcast_removes_stale_connections(
        self, stream_id: str, sample_alert
    ) -> None:
        import websockets

        ch = WebSocketChannel()
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send.side_effect = websockets.ConnectionClosed(None, None)
        ch.register(stream_id, good_ws)
        ch.register(stream_id, bad_ws)

        count = await ch.broadcast(stream_id, sample_alert)
        assert count == 1
        assert bad_ws not in ch.clients.get(stream_id, set())

    async def test_broadcast_payload_is_valid_json(
        self, stream_id: str, sample_alert
    ) -> None:
        ch = WebSocketChannel()
        ws = AsyncMock()
        ch.register(stream_id, ws)

        await ch.broadcast(stream_id, sample_alert)
        raw = ws.send.call_args[0][0]
        data = json.loads(raw)
        assert data["matched_rule"] == "gun"
        assert data["alert_type"] == "keyword"

    async def test_broadcast_removes_stream_key_when_all_stale(
        self, stream_id: str, sample_alert
    ) -> None:
        import websockets

        ch = WebSocketChannel()
        bad_ws = AsyncMock()
        bad_ws.send.side_effect = websockets.ConnectionClosed(None, None)
        ch.register(stream_id, bad_ws)

        await ch.broadcast(stream_id, sample_alert)
        assert stream_id not in ch.clients


# ── send (AlertChannel interface) ──


class TestWebSocketSend:
    """Test the AlertChannel.send interface method."""

    async def test_send_returns_true_when_clients_exist(
        self, stream_id: str, sample_alert
    ) -> None:
        ch = WebSocketChannel()
        ch.register(str(sample_alert.stream_id), AsyncMock())
        assert await ch.send(sample_alert) is True

    async def test_send_returns_false_when_no_clients(self, sample_alert) -> None:
        ch = WebSocketChannel()
        assert await ch.send(sample_alert) is False


# ── close ──


class TestWebSocketClose:
    """Test resource cleanup."""

    async def test_close_clears_registry(self, stream_id: str) -> None:
        ch = WebSocketChannel()
        ch.register(stream_id, AsyncMock())
        await ch.close()
        assert len(ch.clients) == 0

