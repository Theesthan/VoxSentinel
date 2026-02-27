"""
Alert service entry point for VoxSentinel.

Initializes the alert dispatch service, loads channel configurations,
subscribes to match/sentiment/compliance event streams, and exposes
health and metrics endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
