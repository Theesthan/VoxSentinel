"""
Health check endpoint for VoxSentinel ingestion service.

Exposes a /health endpoint returning service status, active stream
count, and connectivity checks for downstream dependencies.
"""

from __future__ import annotations

from fastapi import APIRouter
