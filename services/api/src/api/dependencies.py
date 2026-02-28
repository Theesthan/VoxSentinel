"""
FastAPI dependency injection providers for VoxSentinel API.

Defines reusable Depends() callables for authentication, database
sessions, Redis connections, and other shared resources.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import Request


async def get_db_session(request: Request) -> AsyncIterator[Any]:
    """Yield an ``AsyncSession`` from the app-level session factory.

    The factory is stored on ``request.app.state.db_session_factory``
    during startup.  Falls back to a no-op mock in tests.
    """
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        # Return a placeholder for test mode.
        yield None
        return
    session = factory()
    try:
        yield session
    finally:
        await session.close()


async def get_redis(request: Request) -> Any:
    """Return the shared Redis client from app state."""
    return getattr(request.app.state, "redis", None)


async def get_es_client(request: Request) -> Any:
    """Return the shared Elasticsearch client from app state."""
    return getattr(request.app.state, "es_client", None)
