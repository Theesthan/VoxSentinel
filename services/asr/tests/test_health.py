"""
Tests for the ASR health check endpoint.

Validates the /health route returns correct status and engine readiness.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from asr.health import get_engine_status, router, set_engine_status, _engine_status


def _make_app():
    """Minimal FastAPI app with just the health router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return app


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def setup_method(self) -> None:
        """Reset engine status before each test."""
        _engine_status.clear()

    def teardown_method(self) -> None:
        _engine_status.clear()

    def test_health_no_engines_degraded(self) -> None:
        """Health is 'degraded' when no engines are registered."""
        client = TestClient(_make_app())
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["service"] == "asr"
        assert data["engines"] == {}

    def test_health_engine_ready(self) -> None:
        """Health is 'ok' when at least one engine is ready."""
        set_engine_status("deepgram_nova2", True)
        client = TestClient(_make_app())
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["engines"]["deepgram_nova2"] is True

    def test_health_engine_not_ready(self) -> None:
        """Health is 'degraded' when all engines are not ready."""
        set_engine_status("deepgram_nova2", False)
        client = TestClient(_make_app())
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "degraded"

    def test_set_and_get_engine_status(self) -> None:
        """set_engine_status and get_engine_status round-trip correctly."""
        set_engine_status("test_engine", True)
        status = get_engine_status()
        assert status == {"test_engine": True}

    def test_mixed_engine_status(self) -> None:
        """Health is 'ok' if at least one engine is ready."""
        set_engine_status("primary", True)
        set_engine_status("fallback", False)
        client = TestClient(_make_app())
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["engines"]["primary"] is True
        assert data["engines"]["fallback"] is False
