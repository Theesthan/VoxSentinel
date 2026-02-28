"""
Tests for the health check API router.

Validates the aggregated health endpoint response shape
and service status reporting.
"""

from __future__ import annotations


from fastapi.testclient import TestClient


class TestHealthCheck:
    def test_health_returns_200(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_shape(self, client: TestClient):
        resp = client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "services" in data
        assert isinstance(data["services"], dict)

    def test_health_not_configured_services(self, client: TestClient):
        resp = client.get("/health")
        data = resp.json()
        # In test mode no real connections exist; services report not_configured
        for svc_name in ["database", "redis", "elasticsearch"]:
            assert svc_name in data["services"]

    def test_health_overall_status(self, client: TestClient):
        resp = client.get("/health")
        data = resp.json()
        # With no real backends, all are "not_configured" => overall "healthy"
        assert data["status"] in ("healthy", "degraded")
