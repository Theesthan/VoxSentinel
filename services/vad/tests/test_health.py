"""Unit tests for ``vad.health`` endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vad import health


@pytest.fixture()
def client() -> TestClient:
    """Build a TestClient wrapping only the health router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


class TestHealthEndpoint:
    """GET /health returns service status + model readiness."""

    def test_degraded_when_model_not_loaded(self, client: TestClient) -> None:
        health.set_model_loaded(False)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["service"] == "vad"
        assert body["model_loaded"] is False

    def test_ok_when_model_loaded(self, client: TestClient) -> None:
        health.set_model_loaded(True)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model_loaded"] is True

    def test_set_model_loaded_toggles(self) -> None:
        health.set_model_loaded(False)
        assert health._vad_model_loaded is False
        health.set_model_loaded(True)
        assert health._vad_model_loaded is True
