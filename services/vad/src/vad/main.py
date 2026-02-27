"""
VAD service entry point for VoxSentinel.

Initializes the Voice Activity Detection service, loads the Silero VAD
model, subscribes to audio chunk streams, and exposes health and
metrics endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
