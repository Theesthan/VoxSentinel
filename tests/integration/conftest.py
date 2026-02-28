"""
Integration test fixtures for VoxSentinel.

Uses ``testcontainers`` to spin up disposable PostgreSQL, Redis, and
Elasticsearch containers before the test session.  Provides async
fixtures for database sessions, Redis clients, and ES clients.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


# ---------------------------------------------------------------------------
# Container fixtures (session-scoped — one per test run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    """Start a disposable PostgreSQL 16 container for the test session.

    Uses a TCP connect wait strategy instead of the default ``docker exec``
    approach, which can trigger ``500 Internal Server Error`` on Docker
    Desktop for Windows (named-pipe transport).
    """
    import socket
    import time

    pg = PostgresContainer(
        image="postgres:16-alpine",
        username="voxsentinel",
        password="testpass",
        dbname="voxsentinel_test",
    )
    # Disable the built-in wait strategy so we do our own
    pg._connect = lambda: None  # type: ignore[assignment]
    pg.start()

    # Wait for TCP connectivity + successful psycopg2 SELECT 1
    host = pg.get_container_host_ip()
    port = int(pg.get_exposed_port(5432))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            import psycopg2

            conn = psycopg2.connect(
                host="127.0.0.1",
                port=port,
                user="voxsentinel",
                password="testpass",
                dbname="voxsentinel_test",
                connect_timeout=3,
            )
            conn.close()
            break  # Container is ready
        except Exception:
            time.sleep(0.5)
    else:
        pg.stop()
        raise TimeoutError("PostgreSQL container did not become ready in 60s")

    yield pg
    pg.stop()


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    """Start a disposable Redis container for the test session.

    Uses a direct TCP-based readiness check instead of the default
    ``docker exec`` approach for Docker Desktop compatibility.
    """
    import time

    r = RedisContainer(image="redis:7-alpine")
    r._connect = lambda: None  # type: ignore[assignment]
    r.start()

    host = r.get_container_host_ip()
    port = int(r.get_exposed_port(6379))
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            import redis as _redis

            client = _redis.Redis(host="127.0.0.1", port=port, socket_connect_timeout=2)
            client.ping()
            client.close()
            break
        except Exception:
            time.sleep(0.5)
    else:
        r.stop()
        raise TimeoutError("Redis container did not become ready in 30s")

    yield r
    r.stop()


@pytest.fixture(scope="session")
def elasticsearch_container() -> Iterator[ElasticSearchContainer]:
    """Start a disposable Elasticsearch 8 container for the test session."""
    with ElasticSearchContainer(
        image="docker.elastic.co/elasticsearch/elasticsearch:8.13.0",
    ) as es:
        # Wait until ES is truly ready
        import time
        import urllib.request

        url = es.get_url()
        for _ in range(60):
            try:
                req = urllib.request.urlopen(f"{url}/_cluster/health?wait_for_status=yellow&timeout=2s")
                if req.status == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        yield es


# ---------------------------------------------------------------------------
# Connection-string fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_dsn(postgres_container: PostgresContainer) -> str:
    """Return the async SQLAlchemy DSN for the test PostgreSQL."""
    # testcontainers gives us a psycopg2-style URL; convert to asyncpg
    url = postgres_container.get_connection_url()
    async_url = url.replace("psycopg2", "asyncpg").replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    # Force IPv4 — Docker Desktop on Windows may not expose on IPv6 (::1)
    async_url = async_url.replace("://localhost:", "://127.0.0.1:")
    # Disable SSL — testcontainer PostgreSQL doesn't have SSL configured
    sep = "&" if "?" in async_url else "?"
    return f"{async_url}{sep}ssl=disable"


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    """Return the Redis connection URL for the test container."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def elasticsearch_url(elasticsearch_container: ElasticSearchContainer) -> str:
    """Return the Elasticsearch HTTP URL for the test container."""
    return elasticsearch_container.get_url()


# ---------------------------------------------------------------------------
# Database schema creation (replaces Alembic for test reliability)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _run_migrations(postgres_dsn: str) -> None:
    """Create all tables directly using SQLAlchemy metadata.

    Uses a synchronous psycopg2 engine to avoid asyncio.run() conflicts
    that arise when Alembic's env.py runs async migrations.  Retries
    the connection to handle transient container startup delays.
    """
    import time

    from sqlalchemy import create_engine

    from tg_common.db.orm_models import Base

    # Convert asyncpg URL to sync psycopg2 URL
    sync_dsn = postgres_dsn.replace("+asyncpg", "+psycopg2")
    # Remove ssl=disable for psycopg2 (uses sslmode param instead)
    if "?ssl=disable" in sync_dsn:
        sync_dsn = sync_dsn.replace("?ssl=disable", "?sslmode=disable")
    elif "&ssl=disable" in sync_dsn:
        sync_dsn = sync_dsn.replace("&ssl=disable", "&sslmode=disable")

    # Retry up to 10 times (container may need extra stabilization)
    last_err = None
    for attempt in range(10):
        try:
            engine = create_engine(sync_dsn)
            Base.metadata.create_all(engine)
            engine.dispose()
            break
        except Exception as exc:
            last_err = exc
            time.sleep(1)
    else:
        raise RuntimeError(
            f"Failed to create tables after 10 retries: {last_err}"
        ) from last_err

    # Also set env var so tg_common.config picks up the test DB
    os.environ["TG_DB_URI"] = postgres_dsn


# ---------------------------------------------------------------------------
# Async engine & session fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_engine(
    postgres_dsn: str, _run_migrations: None
) -> AsyncIterator[AsyncEngine]:
    """Create a per-test async engine and dispose it afterwards.

    A fresh engine per test prevents ``ConnectionResetError`` on
    Windows where pytest-asyncio creates a new event loop for each
    test function and stale asyncpg connections from a session-scoped
    engine reference the old (closed) loop.

    ``NullPool`` ensures no connections linger between queries.
    """
    engine = create_async_engine(
        postgres_dsn,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a per-test session factory bound to the test engine."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a per-test ``AsyncSession`` and roll back afterwards."""
    async with db_session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Redis client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def redis_client(redis_url: str) -> AsyncIterator[aioredis.Redis]:
    """Yield a per-test async Redis client and flush the DB afterwards."""
    r = aioredis.from_url(redis_url, decode_responses=True)
    yield r
    await r.flushdb()
    await r.aclose()


# ---------------------------------------------------------------------------
# Elasticsearch client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def es_client(elasticsearch_url: str) -> AsyncIterator:
    """Yield a per-test async Elasticsearch client."""
    from elasticsearch import AsyncElasticsearch

    client = AsyncElasticsearch(elasticsearch_url)
    yield client
    # Clean up any indices created during the test
    await client.indices.delete(index="_all", ignore_unavailable=True)
    await client.close()


# ---------------------------------------------------------------------------
# Test audio fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_audio_path() -> Path:
    """Path to the test audio WAV with known keywords ('fire', 'help')."""
    p = Path(__file__).resolve().parents[1] / "fixtures" / "test_audio_keywords.wav"
    if not p.exists():
        pytest.skip(
            f"Test audio not found at {p}. "
            "Run: python scripts/generate_test_audio.py"
        )
    return p
