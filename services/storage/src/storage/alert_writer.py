"""
Alert writer for VoxSentinel storage service.

Persists alert records to PostgreSQL with foreign key references
to triggering transcript segments and sessions.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
