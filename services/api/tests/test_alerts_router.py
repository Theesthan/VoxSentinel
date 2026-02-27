"""
Tests for the alerts API router.

Validates alert listing with filters and single-alert retrieval
for the alert monitoring endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

ALERT_ID = "11111111-2222-3333-4444-555555555555"
STREAM_ID = "12345678-1234-5678-1234-567812345678"
SESSION_ID = "87654321-4321-8765-4321-876543218765"
SEGMENT_ID = "99999999-8888-7777-6666-555544443333"


# ─── Helpers ──────────────────────────────────────────────────


def _make_alert_orm(**overrides):
    defaults = dict(
        alert_id=uuid.UUID(ALERT_ID),
        stream_id=uuid.UUID(STREAM_ID),
        session_id=uuid.UUID(SESSION_ID),
        segment_id=uuid.UUID(SEGMENT_ID),
        alert_type="keyword",
        severity="high",
        matched_rule="prohibited",
        match_type="exact",
        similarity_score=None,
        matched_text="prohibited word here",
        surrounding_context="context text",
        speaker_id="spk_0",
        channel=None,
        sentiment_scores=None,
        asr_backend_used="deepgram",
        delivered_to=None,
        delivery_status=None,
        deduplicated=False,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ─── GET /api/v1/alerts ──────────────────────────────────────


class TestListAlerts:
    def test_list_alerts_empty(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alerts"] == []
        assert data["total"] == 0

    def test_list_alerts_returns_items(self, client: TestClient, mock_db: AsyncMock):
        a1 = _make_alert_orm()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [a1]
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts")
        data = resp.json()
        assert data["total"] == 1
        assert data["alerts"][0]["alert_id"] == ALERT_ID
        assert data["alerts"][0]["severity"] == "high"

    def test_list_alerts_filter_by_stream_id(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts", params={"stream_id": STREAM_ID})
        assert resp.status_code == 200

    def test_list_alerts_filter_by_severity(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts", params={"severity": "critical"})
        assert resp.status_code == 200

    def test_list_alerts_filter_by_alert_type(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts", params={"alert_type": "keyword"})
        assert resp.status_code == 200

    def test_list_alerts_filter_by_date_range(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(
            "/api/v1/alerts",
            params={"from": "2025-01-01T00:00:00", "to": "2025-12-31T23:59:59"},
        )
        assert resp.status_code == 200

    def test_list_alerts_with_limit_offset(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts", params={"limit": 10, "offset": 5})
        assert resp.status_code == 200

    def test_list_alerts_summary_fields(self, client: TestClient, mock_db: AsyncMock):
        a = _make_alert_orm()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [a]
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/alerts")
        alert = resp.json()["alerts"][0]
        assert alert["matched_rule"] == "prohibited"
        assert alert["matched_text"] == "prohibited word here"
        assert alert["speaker_id"] == "spk_0"


# ─── GET /api/v1/alerts/{alert_id} ──────────────────────────


class TestGetAlert:
    def test_get_alert_success(self, client: TestClient, mock_db: AsyncMock):
        alert = _make_alert_orm()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = alert
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(f"/api/v1/alerts/{ALERT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alert_id"] == ALERT_ID
        assert data["session_id"] == SESSION_ID
        assert data["segment_id"] == SEGMENT_ID
        assert data["asr_backend_used"] == "deepgram"
        assert data["deduplicated"] is False

    def test_get_alert_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(f"/api/v1/alerts/{ALERT_ID}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Alert not found"

    def test_get_alert_full_fields(self, client: TestClient, mock_db: AsyncMock):
        alert = _make_alert_orm(
            similarity_score=0.95,
            channel="slack",
            sentiment_scores={"pos": 0.1, "neg": 0.8},
            delivered_to=["slack-channel"],
            delivery_status={"slack": "sent"},
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = alert
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(f"/api/v1/alerts/{ALERT_ID}")
        data = resp.json()
        assert data["similarity_score"] == 0.95
        assert data["channel"] == "slack"
        assert data["sentiment_scores"]["neg"] == 0.8
        assert data["delivered_to"] == ["slack-channel"]
        assert data["delivery_status"]["slack"] == "sent"
