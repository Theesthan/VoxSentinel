"""Tests for storage.transcript_writer."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from tg_common.models.transcript import TranscriptSegment, WordTimestamp


# ─── helpers ──────────────────────────────────────────────────────


def _make_segment(**overrides) -> TranscriptSegment:
    defaults = dict(
        segment_id=uuid4(),
        session_id=UUID("87654321-4321-8765-4321-876543218765"),
        stream_id=UUID("12345678-1234-5678-1234-567812345678"),
        speaker_id="SPEAKER_00",
        start_time=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 12, 0, 5, tzinfo=timezone.utc),
        start_offset_ms=0,
        end_offset_ms=5000,
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


# ─── compute_segment_hash ─────────────────────────────────────────


class TestComputeSegmentHash:
    def test_deterministic(self):
        from storage.transcript_writer import compute_segment_hash

        sid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        sess = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h1 = compute_segment_hash(sid, "text", ts, sess)
        h2 = compute_segment_hash(sid, "text", ts, sess)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_text_different_hash(self):
        from storage.transcript_writer import compute_segment_hash

        sid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        sess = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h1 = compute_segment_hash(sid, "text_a", ts, sess)
        h2 = compute_segment_hash(sid, "text_b", ts, sess)
        assert h1 != h2

    def test_matches_raw_sha256(self):
        from storage.transcript_writer import compute_segment_hash

        sid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        sess = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        payload = f"{sid}original{ts}{sess}"
        expected = hashlib.sha256(payload.encode()).hexdigest()
        assert compute_segment_hash(sid, "original", ts, sess) == expected


# ─── TranscriptWriter.write_segment ──────────────────────────────


class TestWriteSegment:
    async def test_creates_orm_and_commits(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment()

        result = await writer.write_segment(seg, db_session=mock_db_session)

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        assert result.segment_id == seg.segment_id
        assert result.text_redacted == seg.text_redacted
        assert result.text_original == seg.text_original
        assert result.segment_hash is not None
        assert len(result.segment_hash) == 64

    async def test_hash_uses_original_text(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter, compute_segment_hash

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment(text_original="secret", text_redacted="[REDACTED]")

        result = await writer.write_segment(seg, db_session=mock_db_session)

        expected = compute_segment_hash(
            seg.segment_id,
            "secret",
            seg.start_time,
            seg.session_id,
        )
        assert result.segment_hash == expected

    async def test_hash_falls_back_to_redacted_if_no_original(
        self, mock_db_session, mock_db_session_factory,
    ):
        from storage.transcript_writer import TranscriptWriter, compute_segment_hash

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment(text_original=None, text_redacted="redacted")

        result = await writer.write_segment(seg, db_session=mock_db_session)

        expected = compute_segment_hash(
            seg.segment_id,
            "redacted",
            seg.start_time,
            seg.session_id,
        )
        assert result.segment_hash == expected

    async def test_calls_es_indexer_after_write(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        mock_indexer = AsyncMock()
        mock_indexer.index_segment = AsyncMock()
        writer = TranscriptWriter(
            session_factory=mock_db_session_factory,
            es_indexer=mock_indexer,
        )
        seg = _make_segment()

        await writer.write_segment(seg, db_session=mock_db_session)

        mock_indexer.index_segment.assert_awaited_once()
        call_args = mock_indexer.index_segment.call_args
        assert call_args[0][0] is seg

    async def test_es_failure_does_not_rollback_db(
        self, mock_db_session, mock_db_session_factory,
    ):
        from storage.transcript_writer import TranscriptWriter

        mock_indexer = AsyncMock()
        mock_indexer.index_segment = AsyncMock(side_effect=RuntimeError("ES down"))
        writer = TranscriptWriter(
            session_factory=mock_db_session_factory,
            es_indexer=mock_indexer,
        )
        seg = _make_segment()

        # Should NOT raise — ES error is logged, not propagated.
        result = await writer.write_segment(seg, db_session=mock_db_session)
        assert result is not None
        mock_db_session.commit.assert_awaited_once()

    async def test_db_failure_raises_and_rolls_back(
        self, mock_db_session, mock_db_session_factory,
    ):
        from storage.transcript_writer import TranscriptWriter

        mock_db_session.commit = AsyncMock(side_effect=RuntimeError("DB down"))
        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment()

        with pytest.raises(RuntimeError, match="DB down"):
            await writer.write_segment(seg, db_session=mock_db_session)

        mock_db_session.rollback.assert_awaited_once()

    async def test_word_timestamps_serialized(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        wts = [WordTimestamp(word="hello", start_ms=0, end_ms=500, confidence=0.9)]
        seg = _make_segment(word_timestamps=wts)

        result = await writer.write_segment(seg, db_session=mock_db_session)
        assert result.word_timestamps is not None
        assert len(result.word_timestamps) == 1
        assert result.word_timestamps[0]["word"] == "hello"

    async def test_empty_word_timestamps(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment(word_timestamps=[])

        result = await writer.write_segment(seg, db_session=mock_db_session)
        assert result.word_timestamps is None  # empty list → None

    async def test_creates_own_session_when_none_provided(self, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        mock_session = mock_db_session_factory.return_value
        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment()

        result = await writer.write_segment(seg)

        mock_db_session_factory.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    async def test_sentiment_fields_persisted(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment(sentiment_label="negative", sentiment_score=0.92)

        result = await writer.write_segment(seg, db_session=mock_db_session)
        assert result.sentiment_label == "negative"
        assert result.sentiment_score == 0.92

    async def test_pii_entities_persisted(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment(pii_entities_found=["EMAIL", "PHONE"])

        result = await writer.write_segment(seg, db_session=mock_db_session)
        assert result.pii_entities_found == ["EMAIL", "PHONE"]

    async def test_intent_labels_persisted(self, mock_db_session, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment(intent_labels=["escalation", "complaint"])

        result = await writer.write_segment(seg, db_session=mock_db_session)
        assert result.intent_labels == ["escalation", "complaint"]


# ─── TranscriptWriter.handle_message ─────────────────────────────


class TestHandleMessage:
    async def test_valid_json_written(self, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment()
        raw = seg.model_dump_json()

        result = await writer.handle_message(raw)
        assert result is not None
        assert result.segment_id == seg.segment_id

    async def test_invalid_json_returns_none(self, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        result = await writer.handle_message("NOT JSON {{{")
        assert result is None

    async def test_missing_fields_returns_none(self, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        result = await writer.handle_message(json.dumps({"text_redacted": "hi"}))
        assert result is None

    async def test_bytes_input(self, mock_db_session_factory):
        from storage.transcript_writer import TranscriptWriter

        writer = TranscriptWriter(session_factory=mock_db_session_factory)
        seg = _make_segment()
        raw = seg.model_dump_json().encode()

        result = await writer.handle_message(raw)
        assert result is not None
