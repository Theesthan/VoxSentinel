"""
Health check endpoint for VoxSentinel storage service.

Exposes a /health endpoint returning service status and connectivity
checks for PostgreSQL and Elasticsearch.
"""

from __future__ import annotations

from fastapi import APIRouter
