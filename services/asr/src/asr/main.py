"""
ASR service entry point for VoxSentinel.

Initializes the ASR engine registry, loads configured backends,
subscribes to speech chunk streams from VAD, and exposes health
and metrics endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
