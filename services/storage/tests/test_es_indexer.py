"""Tests for storage.es_indexer."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from tg_common.models.transcript import TranscriptSegment


# ─── helpers ──────────────────────────────────────────────────────


def _make_segment(**overrides) -> TranscriptSegment:
    defaults = dict(
        segment_id=uuid4(),
        session_id=UUID("87654321-4321-8765-4321-876543218765"),
        stream_id=UUID("12345678-1234-5678-1234-567812345678"),
        speaker_id="SPEAKER_00",
        start_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 12, 0, 5, tzinfo=timezone.utc),
        text_redacted="hello [REDACTED]",
        text_original="hello world",
        language="en",
        asr_backend="deepgram_nova2",
        asr_confidence=0.95,
        sentiment_label="neutral",
        sentiment_score=0.5,
    )
    defaults.update(overrides)
    return TranscriptSegment(**defaults)


# ─── ESIndexer.index_segment ─────────────────────────────────────


class TestIndexSegment:
    async def test_indexes_with_correct_fields(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)
        seg = _make_segment()

        resp = await indexer.index_segment(seg)

        mock_es_client.index.assert_awaited_once()
        call_kwargs = mock_es_client.index.call_args.kwargs
        assert call_kwargs["index"] == "transcripts"
        assert call_kwargs["id"] == str(seg.segment_id)

        doc = call_kwargs["document"]
        assert doc["segment_id"] == str(seg.segment_id)
        assert doc["session_id"] == str(seg.session_id)
        assert doc["stream_id"] == str(seg.stream_id)
        assert doc["speaker_id"] == "SPEAKER_00"
        assert doc["text"] == seg.text_redacted
        assert doc["sentiment_label"] == "neutral"
        assert doc["language"] == "en"

    async def test_text_is_redacted_not_original(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)
        seg = _make_segment(text_redacted="[REDACTED]", text_original="secret")

        await indexer.index_segment(seg)

        doc = mock_es_client.index.call_args.kwargs["document"]
        assert doc["text"] == "[REDACTED]"
        assert "secret" not in str(doc)

    async def test_timestamp_is_iso(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)
        ts = datetime(2025, 6, 15, 8, 30, 0, tzinfo=timezone.utc)
        seg = _make_segment(start_time=ts)

        await indexer.index_segment(seg)

        doc = mock_es_client.index.call_args.kwargs["document"]
        assert doc["timestamp"] == ts.isoformat()

    async def test_custom_index_name(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client, index_name="custom_idx")
        seg = _make_segment()

        await indexer.index_segment(seg)

        assert mock_es_client.index.call_args.kwargs["index"] == "custom_idx"

    async def test_returns_es_response(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        mock_es_client.index = AsyncMock(return_value={"result": "created", "_id": "x"})
        indexer = ESIndexer(mock_es_client)
        seg = _make_segment()

        resp = await indexer.index_segment(seg)
        assert resp["result"] == "created"

    async def test_speaker_id_none(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)
        seg = _make_segment(speaker_id=None)

        await indexer.index_segment(seg)

        doc = mock_es_client.index.call_args.kwargs["document"]
        assert doc["speaker_id"] is None


# ─── ESIndexer.ensure_index ──────────────────────────────────────


class TestEnsureIndex:
    async def test_creates_index_when_not_exists(self, mock_es_client):
        from storage.es_indexer import ESIndexer, INDEX_MAPPING

        mock_es_client.indices.exists = AsyncMock(return_value=False)
        indexer = ESIndexer(mock_es_client)

        await indexer.ensure_index()

        mock_es_client.indices.create.assert_awaited_once()
        call_kwargs = mock_es_client.indices.create.call_args.kwargs
        assert call_kwargs["index"] == "transcripts"
        assert call_kwargs["body"] == INDEX_MAPPING

    async def test_skips_when_already_exists(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        mock_es_client.indices.exists = AsyncMock(return_value=True)
        indexer = ESIndexer(mock_es_client)

        await indexer.ensure_index()

        mock_es_client.indices.create.assert_not_awaited()


# ─── ESIndexer.search ────────────────────────────────────────────


class TestSearch:
    async def test_basic_search(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)

        await indexer.search("bomb threat")

        mock_es_client.search.assert_awaited_once()
        call_kwargs = mock_es_client.search.call_args.kwargs
        assert call_kwargs["index"] == "transcripts"
        body = call_kwargs["body"]
        assert body["query"]["bool"]["must"][0]["match"]["text"]["query"] == "bomb threat"

    async def test_search_with_session_filter(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)

        await indexer.search("word", session_id="sess-123")

        body = mock_es_client.search.call_args.kwargs["body"]
        filters = body["query"]["bool"]["must"]
        assert any(f.get("term", {}).get("session_id") == "sess-123" for f in filters)

    async def test_search_with_stream_filter(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)

        await indexer.search("word", stream_id="strm-456")

        body = mock_es_client.search.call_args.kwargs["body"]
        filters = body["query"]["bool"]["must"]
        assert any(f.get("term", {}).get("stream_id") == "strm-456" for f in filters)

    async def test_search_size_param(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)

        await indexer.search("word", size=5)

        body = mock_es_client.search.call_args.kwargs["body"]
        assert body["size"] == 5

    async def test_search_highlight(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)

        await indexer.search("word")

        body = mock_es_client.search.call_args.kwargs["body"]
        assert "highlight" in body
        assert "text" in body["highlight"]["fields"]


# ─── ESIndexer.close ─────────────────────────────────────────────


class TestClose:
    async def test_close_delegates(self, mock_es_client):
        from storage.es_indexer import ESIndexer

        indexer = ESIndexer(mock_es_client)
        await indexer.close()
        mock_es_client.close.assert_awaited_once()
