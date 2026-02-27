"""
Storage service entry point for VoxSentinel.

Initializes database connections, Elasticsearch client, subscribes to
transcript and alert event streams, and exposes health and metrics
endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
