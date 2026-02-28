"""
Tests for the streams API router.

Validates stream CRUD operations, input validation, and error
responses for the stream management endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

STREAM_ID = "12345678-1234-5678-1234-567812345678"
SESSION_ID = "87654321-4321-8765-4321-876543218765"


# ─── Helpers ──────────────────────────────────────────────────


def _make_stream_orm(**overrides):
    """Build a mock StreamORM instance."""
    defaults = dict(
        stream_id=uuid.UUID(STREAM_ID),
        name="Test Stream",
        source_type="sip",
        source_url="sip://10.0.0.1:5060",
        asr_backend="deepgram",
        asr_fallback_backend=None,
        language_override=None,
        vad_threshold=0.5,
        chunk_size_ms=20,
        status="active",
        session_id=uuid.UUID(SESSION_ID),
        metadata_=None,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ─── POST /api/v1/streams ────────────────────────────────────


class TestCreateStream:
    def test_create_stream_returns_201(self, client: TestClient, mock_db: AsyncMock):
        mock_db.refresh = AsyncMock()
        resp = client.post(
            "/api/v1/streams",
            json={
                "name": "My Stream",
                "source_type": "sip",
                "source_url": "sip://10.0.0.1:5060",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "stream_id" in data
        assert data["status"] == "active"
        assert "session_id" in data
        assert "created_at" in data

    def test_create_stream_calls_db_add_and_commit(
        self, client: TestClient, mock_db: AsyncMock,
    ):
        mock_db.refresh = AsyncMock()
        client.post(
            "/api/v1/streams",
            json={
                "name": "S1",
                "source_type": "rtp",
                "source_url": "rtp://host",
            },
        )
        assert mock_db.add.call_count >= 1
        mock_db.commit.assert_awaited()

    def test_create_stream_publishes_to_redis(
        self, client: TestClient, mock_db: AsyncMock, mock_redis_client: AsyncMock,
    ):
        mock_db.refresh = AsyncMock()
        client.post(
            "/api/v1/streams",
            json={
                "name": "S1",
                "source_type": "sip",
                "source_url": "sip://host",
            },
        )
        mock_redis_client.publish.assert_awaited()

    def test_create_stream_with_optional_fields(
        self, client: TestClient, mock_db: AsyncMock,
    ):
        mock_db.refresh = AsyncMock()
        resp = client.post(
            "/api/v1/streams",
            json={
                "name": "Full",
                "source_type": "sip",
                "source_url": "sip://host",
                "asr_backend": "whisper",
                "asr_fallback_backend": "deepgram",
                "language_override": "en",
                "vad_threshold": 0.7,
                "chunk_size_ms": 30,
                "keyword_rule_set_names": ["compliance"],
                "alert_channel_ids": [],
                "metadata": {"key": "val"},
            },
        )
        assert resp.status_code == 201

    def test_create_stream_missing_name_returns_422(self, client: TestClient):
        resp = client.post(
            "/api/v1/streams",
            json={"source_type": "sip", "source_url": "sip://x"},
        )
        assert resp.status_code == 422


# ─── GET /api/v1/streams ─────────────────────────────────────


class TestListStreams:
    def test_list_streams_empty(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/streams")
        assert resp.status_code == 200
        data = resp.json()
        assert data["streams"] == []
        assert data["total"] == 0

    def test_list_streams_returns_items(self, client: TestClient, mock_db: AsyncMock):
        s1 = _make_stream_orm(name="Stream A")
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [s1]
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/streams")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["streams"][0]["name"] == "Stream A"


# ─── GET /api/v1/streams/{stream_id} ────────────────────────


class TestGetStream:
    def test_get_stream_success(self, client: TestClient, mock_db: AsyncMock):
        stream = _make_stream_orm()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = stream
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(f"/api/v1/streams/{STREAM_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stream_id"] == STREAM_ID
        assert data["name"] == "Test Stream"

    def test_get_stream_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(f"/api/v1/streams/{STREAM_ID}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Stream not found"


# ─── PATCH /api/v1/streams/{stream_id} ──────────────────────


class TestUpdateStream:
    def test_update_stream_success(self, client: TestClient, mock_db: AsyncMock):
        stream = _make_stream_orm()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = stream
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.refresh = AsyncMock()

        resp = client.patch(
            f"/api/v1/streams/{STREAM_ID}",
            json={"name": "Updated"},
        )
        assert resp.status_code == 200
        assert stream.name == "Updated"

    def test_update_stream_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.patch(
            f"/api/v1/streams/{STREAM_ID}",
            json={"name": "Updated"},
        )
        assert resp.status_code == 404


# ─── DELETE /api/v1/streams/{stream_id} ──────────────────────


class TestDeleteStream:
    def test_delete_stream_success(
        self, client: TestClient, mock_db: AsyncMock, mock_redis_client: AsyncMock,
    ):
        stream = _make_stream_orm()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = stream
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.delete(f"/api/v1/streams/{STREAM_ID}")
        assert resp.status_code == 204
        mock_db.delete.assert_awaited()
        mock_redis_client.publish.assert_awaited()

    def test_delete_stream_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.delete(f"/api/v1/streams/{STREAM_ID}")
        assert resp.status_code == 404


# ─── POST /api/v1/streams/{stream_id}/pause|resume ──────────


class TestPauseResumeStream:
    def test_pause_stream(self, client: TestClient, mock_db: AsyncMock):
        stream = _make_stream_orm(status="active")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = stream
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.post(f"/api/v1/streams/{STREAM_ID}/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_resume_stream(self, client: TestClient, mock_db: AsyncMock):
        stream = _make_stream_orm(status="paused")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = stream
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.post(f"/api/v1/streams/{STREAM_ID}/resume")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_pause_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.post(f"/api/v1/streams/{STREAM_ID}/pause")
        assert resp.status_code == 404

    def test_resume_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.post(f"/api/v1/streams/{STREAM_ID}/resume")
        assert resp.status_code == 404

