"""Shared fixtures for storage service tests."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Use *append* to avoid shadowing other services' conftests.
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

# ─── Mock heavy deps before any application code is imported ───

# elasticsearch — heavy C extension; mock entirely
_es_mod = MagicMock(name="elasticsearch")
_async_es_cls = MagicMock(name="AsyncElasticsearch")
_es_mod.AsyncElasticsearch = _async_es_cls
sys.modules.setdefault("elasticsearch", _es_mod)

# asyncpg — native driver; not needed in unit tests
sys.modules.setdefault("asyncpg", MagicMock(name="asyncpg"))

# prometheus_client — lightweight but not needed for biz-logic tests
sys.modules.setdefault("prometheus_client", MagicMock(name="prometheus_client"))

# Set env vars before any tg_common import.
os.environ.setdefault("TG_DB_URI", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("TG_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TG_API_HOST", "127.0.0.1")
os.environ.setdefault("TG_API_PORT", "8000")
os.environ.setdefault("TG_API_KEY", "test-key")


# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def stream_id() -> str:
    return "12345678-1234-5678-1234-567812345678"


@pytest.fixture()
def session_id() -> str:
    return "87654321-4321-8765-4321-876543218765"


@pytest.fixture()
def mock_db_session() -> AsyncMock:
    """Async mock standing in for a ``AsyncSession``."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture()
def mock_db_session_factory(mock_db_session: AsyncMock):
    """Factory that always returns the same mock session."""
    return MagicMock(return_value=mock_db_session)


@pytest.fixture()
def mock_es_client() -> AsyncMock:
    """Async mock standing in for ``AsyncElasticsearch``."""
    es = AsyncMock()
    es.index = AsyncMock(return_value={"result": "created", "_id": "test"})
    es.search = AsyncMock(return_value={"hits": {"total": {"value": 0}, "hits": []}})
    es.indices = AsyncMock()
    es.indices.exists = AsyncMock(return_value=False)
    es.indices.create = AsyncMock()
    es.close = AsyncMock()
    return es


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """Async mock standing in for ``redis.asyncio.Redis``."""
    redis = AsyncMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    redis.publish = AsyncMock(return_value=1)
    redis.subscribe = AsyncMock()
    redis.health_check = AsyncMock(return_value=True)
    return redis
