"""Tests for storage.health and storage.main."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        from storage.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "storage"


class TestCreateApp:
    def test_app_has_health_route(self):
        from storage.main import create_app

        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/health" in paths
