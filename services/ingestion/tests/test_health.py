"""
Tests for the health check endpoint.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ingestion.health import router


@pytest.fixture()
def client() -> TestClient:
    """Create a test client with only the health router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "ingestion"
