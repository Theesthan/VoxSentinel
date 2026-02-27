"""
Ingestion service entry point for VoxSentinel.

Initializes the ingestion service, sets up stream connections,
starts the audio extraction pipeline, and exposes health and
metrics endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
