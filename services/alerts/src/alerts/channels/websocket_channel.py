"""
WebSocket alert channel for VoxSentinel.

Pushes alert events to connected dashboard clients via WebSocket
connections in real time (<50 ms from event generation).
"""

from __future__ import annotations

import websockets
