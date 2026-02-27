"""
Tests for the search API router.

Validates full-text search queries, result highlighting, and
Elasticsearch integration for the search endpoint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

STREAM_ID = "12345678-1234-5678-1234-567812345678"
SESSION_ID = "87654321-4321-8765-4321-876543218765"
SEGMENT_ID = "99999999-8888-7777-6666-555544443333"


# ─── Helpers ──────────────────────────────────────────────────


def _es_response(hits_list=None, total=0):
    """Build a minimal Elasticsearch response dict."""
    if hits_list is None:
        hits_list = []
    return {
        "hits": {
            "total": {"value": total},
            "hits": hits_list,
        },
    }


def _es_hit(text="hello world", highlight_text=None, score=1.5):
    h = {
        "_score": score,
        "_source": {
            "segment_id": SEGMENT_ID,
            "session_id": SESSION_ID,
            "stream_id": STREAM_ID,
            "stream_name": "Test Stream",
            "speaker_id": "spk_0",
            "timestamp": "2025-01-01T00:00:00Z",
            "text": text,
            "sentiment_label": "neutral",
        },
    }
    if highlight_text:
        h["highlight"] = {"text": [highlight_text]}
    return h


# ─── POST /api/v1/search ────────────────────────────────────


class TestSearchTranscripts:
    def test_search_basic_query(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(
            return_value=_es_response(
                hits_list=[_es_hit(text="hello world")],
                total=1,
            ),
        )

        resp = client.post(
            "/api/v1/search",
            json={"query": "hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["text"] == "hello world"

    def test_search_with_highlight(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(
            return_value=_es_response(
                hits_list=[_es_hit(text="hello world", highlight_text="<em>hello</em> world")],
                total=1,
            ),
        )

        resp = client.post("/api/v1/search", json={"query": "hello"})
        data = resp.json()
        assert "<em>hello</em>" in data["results"][0]["text"]

    def test_search_phrase_type(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(return_value=_es_response(total=0))

        resp = client.post(
            "/api/v1/search",
            json={"query": "exact phrase", "search_type": "phrase"},
        )
        assert resp.status_code == 200
        # Verify ES was called with match_phrase
        call_kwargs = mock_es.search.call_args
        body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body")
        must = body["query"]["bool"]["must"]
        assert any("match_phrase" in clause for clause in must)

    def test_search_regex_type(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(return_value=_es_response(total=0))

        resp = client.post(
            "/api/v1/search",
            json={"query": "hel.*", "search_type": "regex"},
        )
        assert resp.status_code == 200
        call_kwargs = mock_es.search.call_args
        body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body")
        must = body["query"]["bool"]["must"]
        assert any("regexp" in clause for clause in must)

    def test_search_with_filters(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(return_value=_es_response(total=0))

        resp = client.post(
            "/api/v1/search",
            json={
                "query": "test",
                "stream_ids": [STREAM_ID],
                "speaker_id": "spk_0",
                "language": "en",
                "date_from": "2025-01-01T00:00:00",
                "date_to": "2025-12-31T23:59:59",
                "limit": 20,
                "offset": 5,
            },
        )
        assert resp.status_code == 200

    def test_search_empty_results(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(return_value=_es_response(total=0))

        resp = client.post("/api/v1/search", json={"query": "nonexistent"})
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_es_none_returns_empty(
        self, client: TestClient, app, mock_db: AsyncMock,
    ):
        """When ES is None the endpoint should return an empty result."""
        from api.dependencies import get_es_client
        app.dependency_overrides[get_es_client] = lambda: None

        resp = client.post("/api/v1/search", json={"query": "anything"})
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_missing_query_returns_422(self, client: TestClient):
        resp = client.post("/api/v1/search", json={})
        assert resp.status_code == 422

    def test_search_result_fields(self, client: TestClient, mock_es: AsyncMock):
        mock_es.search = AsyncMock(
            return_value=_es_response(
                hits_list=[_es_hit(score=2.7)],
                total=1,
            ),
        )
        resp = client.post("/api/v1/search", json={"query": "hello"})
        hit = resp.json()["results"][0]
        assert hit["segment_id"] == SEGMENT_ID
        assert hit["session_id"] == SESSION_ID
        assert hit["stream_id"] == STREAM_ID
        assert hit["stream_name"] == "Test Stream"
        assert hit["speaker_id"] == "spk_0"
        assert hit["score"] == 2.7
        assert hit["sentiment_label"] == "neutral"

    def test_search_total_as_plain_int(self, client: TestClient, mock_es: AsyncMock):
        """Handle ES returning total as a plain int (older format)."""
        mock_es.search = AsyncMock(
            return_value={"hits": {"total": 3, "hits": []}},
        )
        resp = client.post("/api/v1/search", json={"query": "x"})
        assert resp.json()["total"] == 3

