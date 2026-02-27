"""
Diarization service entry point for VoxSentinel.

Initializes the diarization pipeline, loads the pyannote.audio model,
subscribes to audio streams, and exposes health and metrics endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
