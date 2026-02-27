"""
Health check API router for VoxSentinel.

Aggregated health endpoint returning status of all backend services,
database, Elasticsearch, Redis, and ASR backends.
"""

from __future__ import annotations

from fastapi import APIRouter
