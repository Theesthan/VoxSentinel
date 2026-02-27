"""
Transcript writer for VoxSentinel storage service.

Writes finalized transcript segments to PostgreSQL/TimescaleDB as
time-series records partitioned by day, handling both redacted and
restricted-access original text storage.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
