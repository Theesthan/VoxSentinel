"""
Async database connection management for VoxSentinel.

Provides SQLAlchemy async engine and session factory creation,
connection pooling configuration, and health check utilities
for the PostgreSQL/TimescaleDB backend.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tg_common.config import get_settings


def build_engine(dsn: str | None = None, pool_size: int | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Args:
        dsn: Database connection string.  Falls back to ``Settings.db_uri``.
        pool_size: Connection-pool size.  Falls back to ``Settings.db_pool_size``.

    Returns:
        A configured ``AsyncEngine`` instance.
    """
    settings = get_settings()
    return create_async_engine(
        dsn or settings.db_uri,
        pool_size=pool_size or settings.db_pool_size,
        echo=False,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to *engine*.

    Args:
        engine: The async engine to bind sessions to.

    Returns:
        An ``async_sessionmaker`` that produces ``AsyncSession`` instances.
    """
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── Module-level convenience instances ──

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the module-level async engine, creating it lazily.

    Returns:
        The shared ``AsyncEngine`` instance.
    """
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level session factory, creating it lazily.

    Returns:
        The shared ``async_sessionmaker`` instance.
    """
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = build_session_factory(get_engine())
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` and ensure it is closed afterwards.

    Designed for use as a FastAPI dependency or an ``async for`` context.

    Yields:
        An ``AsyncSession`` instance.
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def check_database_health() -> bool:
    """Execute a lightweight query to verify database connectivity.

    Returns:
        ``True`` if the database responds, ``False`` otherwise.
    """
    from sqlalchemy import text

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 – health check must not raise
        return False
