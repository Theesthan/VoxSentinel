"""
Tests for the rules API router.

Validates keyword rule CRUD operations, hot-reload behavior, and
input validation for the rule management endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

RULE_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


# ─── Helpers ──────────────────────────────────────────────────


def _make_rule_orm(**overrides):
    defaults = dict(
        rule_id=uuid.UUID(RULE_ID),
        rule_set_name="compliance",
        keyword="prohibited",
        match_type="exact",
        fuzzy_threshold=None,
        severity="high",
        category="language",
        language="en",
        enabled=True,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ─── POST /api/v1/rules ─────────────────────────────────────


class TestCreateRule:
    def test_create_rule_returns_201(self, client: TestClient, mock_db: AsyncMock):
        mock_db.refresh = AsyncMock()
        resp = client.post(
            "/api/v1/rules",
            json={
                "rule_set_name": "compliance",
                "keyword": "bomb",
                "severity": "critical",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "rule_id" in data
        assert "created_at" in data

    def test_create_rule_calls_db_commit(self, client: TestClient, mock_db: AsyncMock):
        mock_db.refresh = AsyncMock()
        client.post(
            "/api/v1/rules",
            json={"rule_set_name": "demo", "keyword": "test", "severity": "low"},
        )
        mock_db.commit.assert_awaited()

    def test_create_rule_publishes_rules_updated(
        self, client: TestClient, mock_db: AsyncMock, mock_redis_client: AsyncMock,
    ):
        mock_db.refresh = AsyncMock()
        client.post(
            "/api/v1/rules",
            json={"rule_set_name": "demo", "keyword": "test"},
        )
        mock_redis_client.publish.assert_awaited()

    def test_create_rule_with_all_fields(self, client: TestClient, mock_db: AsyncMock):
        mock_db.refresh = AsyncMock()
        resp = client.post(
            "/api/v1/rules",
            json={
                "rule_set_name": "comp",
                "keyword": "fire",
                "match_type": "fuzzy",
                "fuzzy_threshold": 0.85,
                "severity": "medium",
                "category": "threat",
                "language": "en",
                "enabled": True,
            },
        )
        assert resp.status_code == 201

    def test_create_rule_missing_keyword_returns_422(self, client: TestClient):
        resp = client.post("/api/v1/rules", json={"rule_set_name": "comp"})
        assert resp.status_code == 422


# ─── GET /api/v1/rules ──────────────────────────────────────


class TestListRules:
    def test_list_rules_empty(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rules"] == []
        assert data["total"] == 0

    def test_list_rules_returns_items(self, client: TestClient, mock_db: AsyncMock):
        r1 = _make_rule_orm()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [r1]
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get("/api/v1/rules")
        data = resp.json()
        assert data["total"] == 1
        assert data["rules"][0]["keyword"] == "prohibited"

    def test_list_rules_with_filters(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.get(
            "/api/v1/rules",
            params={"rule_set_name": "compliance", "category": "language", "language": "en"},
        )
        assert resp.status_code == 200


# ─── PATCH /api/v1/rules/{rule_id} ──────────────────────────


class TestUpdateRule:
    def test_update_rule_success(
        self, client: TestClient, mock_db: AsyncMock, mock_redis_client: AsyncMock,
    ):
        rule = _make_rule_orm()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = rule
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.refresh = AsyncMock()

        resp = client.patch(
            f"/api/v1/rules/{RULE_ID}",
            json={"keyword": "updated_keyword"},
        )
        assert resp.status_code == 200
        mock_redis_client.publish.assert_awaited()

    def test_update_rule_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.patch(
            f"/api/v1/rules/{RULE_ID}",
            json={"keyword": "nope"},
        )
        assert resp.status_code == 404


# ─── DELETE /api/v1/rules/{rule_id} ─────────────────────────


class TestDeleteRule:
    def test_delete_rule_success(
        self, client: TestClient, mock_db: AsyncMock, mock_redis_client: AsyncMock,
    ):
        rule = _make_rule_orm()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = rule
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.delete(f"/api/v1/rules/{RULE_ID}")
        assert resp.status_code == 204
        mock_db.delete.assert_awaited()
        mock_redis_client.publish.assert_awaited()

    def test_delete_rule_not_found(self, client: TestClient, mock_db: AsyncMock):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = client.delete(f"/api/v1/rules/{RULE_ID}")
        assert resp.status_code == 404

