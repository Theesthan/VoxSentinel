"""
Health check endpoint for VoxSentinel ASR service.

Exposes a /health endpoint returning service status and connectivity
checks for all configured ASR backends.
"""

from __future__ import annotations

from fastapi import APIRouter
