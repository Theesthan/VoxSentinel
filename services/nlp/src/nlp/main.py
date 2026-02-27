"""
NLP service entry point for VoxSentinel.

Initializes the NLP service, loads keyword rules, ML models, and
PII recognizers, subscribes to transcript token streams, and
exposes health and metrics endpoints.
"""

from __future__ import annotations

import asyncio

import structlog
import uvicorn
