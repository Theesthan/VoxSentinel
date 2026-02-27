"""
Async database connection management for VoxSentinel.

Provides SQLAlchemy async engine and session factory creation,
connection pooling configuration, and health check utilities
for the PostgreSQL/TimescaleDB backend.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
