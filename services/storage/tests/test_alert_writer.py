"""Tests for storage.alert_writer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from tg_common.models.alert import Alert, AlertType, MatchType, Severity


# ─── helpers ──────────────────────────────────────────────────────


def _make_alert(**overrides) -> Alert:
    defaults = dict(
        alert_id=uuid4(),
        session_id=UUID("87654321-4321-8765-4321-876543218765"),
        stream_id=UUID("12345678-1234-5678-1234-567812345678"),
        alert_type=AlertType.KEYWORD,
        severity=Severity.HIGH,
        matched_rule="gun",
        match_type=MatchType.EXACT,
        matched_text="he has a gun",
        surrounding_context="suspect says he has a gun near the entrance",
        speaker_id="SPEAKER_01",
    )
    defaults.update(overrides)
    return Alert(**defaults)


# ─── AlertWriter.write_alert ─────────────────────────────────────


class TestWriteAlert:
    async def test_creates_orm_and_commits(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert()

        result = await writer.write_alert(alert, db_session=mock_db_session)

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        assert result.alert_id == alert.alert_id
        assert result.alert_type == "keyword"
        assert result.severity == "high"

    async def test_enum_values_stored_as_strings(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert(
            alert_type=AlertType.SENTIMENT,
            severity=Severity.CRITICAL,
            match_type=MatchType.SENTIMENT_THRESHOLD,
        )

        result = await writer.write_alert(alert, db_session=mock_db_session)

        assert result.alert_type == "sentiment"
        assert result.severity == "critical"
        assert result.match_type == "sentiment_threshold"

    async def test_segment_id_nullable(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert(segment_id=None)

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.segment_id is None

    async def test_segment_id_set(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        seg_id = uuid4()
        alert = _make_alert(segment_id=seg_id)

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.segment_id == seg_id

    async def test_similarity_score_set(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert(
            match_type=MatchType.FUZZY,
            similarity_score=0.87,
        )

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.similarity_score == 0.87

    async def test_delivery_fields_persisted(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert(
            delivered_to=["websocket", "slack"],
            delivery_status={"websocket": "sent", "slack": "failed"},
        )

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.delivered_to == ["websocket", "slack"]
        assert result.delivery_status == {"websocket": "sent", "slack": "failed"}

    async def test_deduplicated_flag(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert(deduplicated=True)

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.deduplicated is True

    async def test_db_failure_raises_and_rolls_back(
        self, mock_db_session, mock_db_session_factory,
    ):
        from storage.alert_writer import AlertWriter

        mock_db_session.commit = AsyncMock(side_effect=RuntimeError("DB down"))
        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert()

        with pytest.raises(RuntimeError, match="DB down"):
            await writer.write_alert(alert, db_session=mock_db_session)

        mock_db_session.rollback.assert_awaited_once()

    async def test_creates_own_session_when_none(self, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        mock_session = mock_db_session_factory.return_value
        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert()

        result = await writer.write_alert(alert)

        mock_db_session_factory.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    async def test_sentiment_scores_json(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        scores = {"positive": 0.1, "negative": 0.8, "neutral": 0.1}
        alert = _make_alert(sentiment_scores=scores)

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.sentiment_scores == scores

    async def test_speaker_and_channel_fields(self, mock_db_session, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert(speaker_id="SPEAKER_02", channel="left")

        result = await writer.write_alert(alert, db_session=mock_db_session)
        assert result.speaker_id == "SPEAKER_02"
        assert result.channel == "left"


# ─── AlertWriter.handle_message ──────────────────────────────────


class TestHandleMessage:
    async def test_valid_json_written(self, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert()
        raw = alert.model_dump_json()

        result = await writer.handle_message(raw)
        assert result is not None
        assert result.alert_id == alert.alert_id

    async def test_invalid_json_returns_none(self, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        result = await writer.handle_message("NOT JSON {{{")
        assert result is None

    async def test_missing_fields_returns_none(self, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        result = await writer.handle_message(json.dumps({"matched_text": "hi"}))
        assert result is None

    async def test_bytes_input(self, mock_db_session_factory):
        from storage.alert_writer import AlertWriter

        writer = AlertWriter(session_factory=mock_db_session_factory)
        alert = _make_alert()
        raw = alert.model_dump_json().encode()

        result = await writer.handle_message(raw)
        assert result is not None
