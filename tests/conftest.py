"""Shared pytest fixtures for integration and end-to-end tests.

Provides common fixtures for database connections, Redis clients,
Elasticsearch clients, test audio data, and service health-check
utilities used across integration and e2e test suites.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for the API gateway during integration tests."""
    return "http://localhost:8000"
