"""
WebSocket client for VoxSentinel dashboard.

Connects to the VoxSentinel API WebSocket endpoints to receive
real-time transcript tokens, alert events, and sentiment updates
for the operator dashboard.
"""

from __future__ import annotations

import websockets
