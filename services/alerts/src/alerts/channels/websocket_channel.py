"""
WebSocket alert channel for VoxSentinel.

Pushes alert events to connected dashboard clients via WebSocket
connections in real time (<50 ms from event generation).
"""

from __future__ import annotations

import json
from typing import Any

import structlog
import websockets

from tg_common.models.alert import Alert

from .base import AlertChannel

logger = structlog.get_logger()


class WebSocketChannel(AlertChannel):
    """Broadcast alerts to dashboard clients over WebSocket.

    Maintains a per-``stream_id`` registry of connected WebSocket
    connections.  When an alert arrives, the channel serialises the
    ``Alert`` to JSON and sends it to every client watching that stream.
    Clients that have disconnected are silently removed from the registry.

    Attributes:
        name: Channel identifier used in delivery tracking.
    """

    name: str = "websocket"

    def __init__(self) -> None:
        # stream_id → set of open websocket connections
        self._clients: dict[str, set[Any]] = {}

    # ── client management ──

    def register(self, stream_id: str, ws: Any) -> None:
        """Add a WebSocket connection to the registry for *stream_id*.

        Args:
            stream_id: The stream the client wants to watch.
            ws: An open websocket connection object.
        """
        self._clients.setdefault(stream_id, set()).add(ws)
        logger.debug(
            "ws_client_registered",
            stream_id=stream_id,
            total=len(self._clients[stream_id]),
        )

    def unregister(self, stream_id: str, ws: Any) -> None:
        """Remove a WebSocket connection from the registry.

        Args:
            stream_id: Stream the client was watching.
            ws: The websocket connection to remove.
        """
        clients = self._clients.get(stream_id)
        if clients:
            clients.discard(ws)
            if not clients:
                del self._clients[stream_id]
        logger.debug("ws_client_unregistered", stream_id=stream_id)

    @property
    def clients(self) -> dict[str, set[Any]]:
        """Read-only view of the client registry."""
        return self._clients

    # ── delivery ──

    async def broadcast(self, stream_id: str, alert: Alert) -> int:
        """Send *alert* to all clients watching *stream_id*.

        Args:
            stream_id: Target stream.
            alert: The alert to broadcast.

        Returns:
            The number of clients the alert was successfully delivered to.
        """
        clients = self._clients.get(stream_id)
        if not clients:
            return 0

        payload = json.dumps(alert.model_dump(mode="json"))
        delivered = 0
        stale: list[Any] = []

        for ws in clients:
            try:
                await ws.send(payload)
                delivered += 1
            except (websockets.ConnectionClosed, OSError):
                stale.append(ws)

        # Prune disconnected clients.
        for ws in stale:
            clients.discard(ws)
        if not clients:
            self._clients.pop(stream_id, None)

        logger.info(
            "ws_broadcast_complete",
            stream_id=stream_id,
            delivered=delivered,
            stale_removed=len(stale),
        )
        return delivered

    async def send(self, alert: Alert) -> bool:
        """Send *alert* to all clients watching the alert's stream.

        Implements the :class:`AlertChannel` interface.

        Returns:
            ``True`` if at least one client received the alert,
            ``False`` otherwise.
        """
        stream_id = str(alert.stream_id)
        delivered = await self.broadcast(stream_id, alert)
        return delivered > 0

    async def close(self) -> None:
        """Clear the client registry (connections are not closed here)."""
        self._clients.clear()
