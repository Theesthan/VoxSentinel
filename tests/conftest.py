"""Shared pytest fixtures for integration and end-to-end tests.

Provides common fixtures for database connections, Redis clients,
Elasticsearch clients, test audio data, and service health-check
utilities used across integration and e2e test suites.
"""

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for the API gateway during integration tests."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def redis_url() -> str:
    """Redis connection URL for integration tests."""
    return "redis://localhost:6379/0"


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    """PostgreSQL DSN for integration tests."""
    return "postgresql+asyncpg://tguser:tgpass@localhost:5432/transcriptguard"


@pytest.fixture(scope="session")
def elasticsearch_url() -> str:
    """Elasticsearch URL for integration tests."""
    return "http://localhost:9200"
