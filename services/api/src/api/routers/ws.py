"""
WebSocket endpoints for VoxSentinel API.

Provides real-time WebSocket streams for live transcript tokens,
alert events, and sentiment updates per stream and cross-stream.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket
