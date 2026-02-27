"""Shared fixtures for API gateway tests."""

from __future__ import annotations

import os
import sys
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest

# Use *append* to avoid shadowing other services' conftests.
sys.path.append(str(Path(__file__).resolve().parent))

# ─── Mock heavy / native deps before application imports ───

# asyncpg — native PG driver; not needed in unit tests
sys.modules.setdefault("asyncpg", MagicMock(name="asyncpg"))

# websockets — optional native C extension
sys.modules.setdefault("websockets", MagicMock(name="websockets"))

# prometheus_client
sys.modules.setdefault("prometheus_client", MagicMock(name="prometheus_client"))

# elasticsearch — async wrapper
_es_mod = MagicMock(name="elasticsearch")
_async_es_cls = MagicMock(name="AsyncElasticsearch")
_es_mod.AsyncElasticsearch = _async_es_cls
sys.modules.setdefault("elasticsearch", _es_mod)

# redis.asyncio mock — prevent real connections
_redis_mod = MagicMock(name="redis")
_redis_async = MagicMock(name="redis.asyncio")
_redis_mod.asyncio = _redis_async
sys.modules.setdefault("redis", _redis_mod)
sys.modules.setdefault("redis.asyncio", _redis_async)

# structlog — keep it simple
sys.modules.setdefault("structlog", MagicMock(name="structlog"))

# Set env vars before any tg_common import.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_API_KEY", "test-api-key-1234")

# ─── Imports (after mocks) ───

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_db_session, get_es_client, get_redis
from api.routers import (
    alert_channels,
    alerts,
    audit,
    health,
    rules,
    search,
    streams,
    transcripts,
)

# ─── UUID helpers ─────────────────────────────────────────────

STREAM_ID = "12345678-1234-5678-1234-567812345678"
SESSION_ID = "87654321-4321-8765-4321-876543218765"
RULE_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ALERT_ID = "11111111-2222-3333-4444-555555555555"
SEGMENT_ID = "99999999-8888-7777-6666-555544443333"
CHANNEL_ID = "abcdefab-cdef-abcd-efab-cdefabcdefab"


# ─── Core fixtures ────────────────────────────────────────────


@pytest.fixture()
def mock_db() -> AsyncMock:
    """Async mock for ``AsyncSession``."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture()
def mock_redis_client() -> AsyncMock:
    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    return redis


@pytest.fixture()
def mock_es() -> AsyncMock:
    es = AsyncMock()
    es.search = AsyncMock(return_value={"hits": {"total": {"value": 0}, "hits": []}})
    es.ping = AsyncMock(return_value=True)
    es.close = AsyncMock()
    return es


def _build_app(
    mock_db: AsyncMock,
    mock_redis_client: AsyncMock,
    mock_es: AsyncMock,
) -> FastAPI:
    """Build a minimal FastAPI app with dependency overrides for testing."""
    app = FastAPI()

    # Override DI
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: mock_redis_client
    app.dependency_overrides[get_es_client] = lambda: mock_es

    # State (for health checks / WS routers that access app.state directly)
    app.state.redis = mock_redis_client
    app.state.es_client = mock_es
    app.state.db_session_factory = None

    # Register routers
    prefix = "/api/v1"
    app.include_router(streams.router, prefix=prefix)
    app.include_router(rules.router, prefix=prefix)
    app.include_router(alerts.router, prefix=prefix)
    app.include_router(alert_channels.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(transcripts.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)
    app.include_router(health.router)

    return app


@pytest.fixture()
def app(mock_db: AsyncMock, mock_redis_client: AsyncMock, mock_es: AsyncMock) -> FastAPI:
    return _build_app(mock_db, mock_redis_client, mock_es)


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-api-key-1234"}
