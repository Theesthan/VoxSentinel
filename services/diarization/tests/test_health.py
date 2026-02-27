"""Tests for diarization.health module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from diarization.health import configure, router


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_503_when_not_configured(self) -> None:
        configure(None)  # type: ignore[arg-type]
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 503
        assert resp.json()["pipeline_ready"] is False

    def test_returns_503_when_pipeline_not_ready(self) -> None:
        pipeline = MagicMock()
        pipeline.is_ready = False
        configure(pipeline)
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 503

    def test_returns_200_when_pipeline_ready(self) -> None:
        pipeline = MagicMock()
        pipeline.is_ready = True
        configure(pipeline)
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pipeline_ready"] is True
        assert body["status"] == "ok"

    def test_response_includes_service_name(self) -> None:
        pipeline = MagicMock()
        pipeline.is_ready = True
        configure(pipeline)
        client = _make_client()
        resp = client.get("/health")
        assert resp.json()["service"] == "diarization"
