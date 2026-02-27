"""
Tests for tg-common shared data models.

Validates Pydantic model serialization, deserialization, validation
constraints, and ORM compatibility for all shared data models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from tg_common.models.alert import (
    Alert,
    AlertType,
    KeywordMatchEvent,
    MatchType,
    SentimentEvent,
    Severity,
)
from tg_common.models.audit import AuditAnchor
from tg_common.models.keyword_rule import (
    AlertChannelConfig,
    ChannelType,
    KeywordRule,
    RuleMatchType,
)
from tg_common.models.stream import Session, SourceType, Stream, StreamStatus
from tg_common.models.transcript import (
    TranscriptSegment,
    TranscriptToken,
    WordTimestamp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_UUID = uuid.uuid4()


# ===========================================================================
# Stream model tests
# ===========================================================================


class TestStream:

    def test_minimal_creation(self) -> None:
        s = Stream(name="test", source_type="rtsp", source_url="rtsp://a")
        assert s.name == "test"
        assert s.source_type == SourceType.RTSP
        assert s.stream_id is not None

    def test_default_status(self) -> None:
        s = Stream(name="s", source_type="hls", source_url="http://x")
        assert s.status == StreamStatus.STOPPED

    def test_invalid_source_type(self) -> None:
        with pytest.raises(ValidationError):
            Stream(name="s", source_type="bad_type", source_url="x")

    def test_invalid_vad_threshold(self) -> None:
        with pytest.raises(ValidationError):
            Stream(name="s", source_type="rtsp", source_url="x", vad_threshold=2.0)

    def test_missing_required_name(self) -> None:
        with pytest.raises(ValidationError):
            Stream(source_type="rtsp", source_url="x")  # type: ignore[call-arg]

    def test_missing_required_source_url(self) -> None:
        with pytest.raises(ValidationError):
            Stream(name="s", source_type="rtsp")  # type: ignore[call-arg]

    def test_all_source_types(self) -> None:
        for st in SourceType:
            s = Stream(name="t", source_type=st.value, source_url="x")
            assert s.source_type == st

    def test_metadata_field(self) -> None:
        s = Stream(name="s", source_type="file", source_url="f.wav", metadata={"k": "v"})
        assert s.metadata == {"k": "v"}


# ===========================================================================
# Session model tests
# ===========================================================================


class TestSession:

    def test_minimal_creation(self) -> None:
        s = Session(stream_id=_UUID)
        assert s.stream_id == _UUID
        assert s.total_segments == 0

    def test_missing_stream_id(self) -> None:
        with pytest.raises(ValidationError):
            Session()  # type: ignore[call-arg]

    def test_invalid_uuid(self) -> None:
        with pytest.raises(ValidationError):
            Session(stream_id="not-a-uuid")


# ===========================================================================
# TranscriptSegment model tests
# ===========================================================================


class TestTranscriptSegment:

    def _make(self, **kw) -> TranscriptSegment:  # type: ignore[no-untyped-def]
        defaults = dict(
            session_id=_UUID,
            stream_id=_UUID,
            start_time=_NOW,
            end_time=_NOW,
            text_redacted="hello",
        )
        defaults.update(kw)
        return TranscriptSegment(**defaults)

    def test_minimal_creation(self) -> None:
        seg = self._make()
        assert seg.text_redacted == "hello"
        assert seg.language == "en"

    def test_missing_session_id(self) -> None:
        with pytest.raises(ValidationError):
            TranscriptSegment(
                stream_id=_UUID, start_time=_NOW, end_time=_NOW, text_redacted="x"
            )  # type: ignore[call-arg]

    def test_text_redacted_has_default(self) -> None:
        seg = TranscriptSegment(
            session_id=_UUID, stream_id=_UUID, start_time=_NOW, end_time=_NOW,
        )
        assert seg.text_redacted == ""

    def test_confidence_bounds(self) -> None:
        seg = self._make(asr_confidence=0.99)
        assert seg.asr_confidence == pytest.approx(0.99)

    def test_word_timestamps_list(self) -> None:
        wt = [WordTimestamp(word="hi", start_ms=0, end_ms=100, confidence=0.9)]
        seg = self._make(word_timestamps=wt)
        assert len(seg.word_timestamps) == 1
        assert seg.word_timestamps[0].word == "hi"


class TestWordTimestamp:

    def test_valid(self) -> None:
        w = WordTimestamp(word="hello", start_ms=0, end_ms=100, confidence=0.95)
        assert w.word == "hello"

    def test_missing_word(self) -> None:
        with pytest.raises(ValidationError):
            WordTimestamp(start_ms=0, end_ms=100, confidence=0.9)  # type: ignore[call-arg]


class TestTranscriptToken:

    def test_valid(self) -> None:
        t = TranscriptToken(
            text="hello world", is_final=True,
            start_time=_NOW, end_time=_NOW, confidence=0.9,
        )
        assert t.is_final is True

    def test_defaults(self) -> None:
        t = TranscriptToken(
            text="x", is_final=False,
            start_time=_NOW, end_time=_NOW, confidence=0.5,
        )
        assert t.language == "en"
        assert t.word_timestamps == []


# ===========================================================================
# Alert model tests
# ===========================================================================


class TestAlert:

    def _make(self, **kw) -> Alert:  # type: ignore[no-untyped-def]
        defaults = dict(
            session_id=_UUID,
            stream_id=_UUID,
            alert_type="keyword",
            severity="high",
            match_type="exact",
        )
        defaults.update(kw)
        return Alert(**defaults)

    def test_minimal_creation(self) -> None:
        a = self._make()
        assert a.alert_type == AlertType.KEYWORD
        assert a.severity == Severity.HIGH

    def test_invalid_alert_type(self) -> None:
        with pytest.raises(ValidationError):
            self._make(alert_type="nonexistent")

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            self._make(severity="extreme")

    def test_invalid_match_type(self) -> None:
        with pytest.raises(ValidationError):
            self._make(match_type="wildcard")

    def test_missing_session_id(self) -> None:
        with pytest.raises(ValidationError):
            Alert(
                stream_id=_UUID, alert_type="keyword",
                severity="low", match_type="exact",
            )  # type: ignore[call-arg]

    def test_all_alert_types(self) -> None:
        for at in AlertType:
            a = self._make(alert_type=at.value)
            assert a.alert_type == at

    def test_deduplicated_default_false(self) -> None:
        assert self._make().deduplicated is False


class TestKeywordMatchEvent:

    def test_valid(self) -> None:
        e = KeywordMatchEvent(
            keyword="bomb", match_type="exact", matched_text="bomb",
            stream_id=_UUID, session_id=_UUID, timestamp=_NOW,
        )
        assert e.keyword == "bomb"

    def test_missing_keyword(self) -> None:
        with pytest.raises(ValidationError):
            KeywordMatchEvent(
                match_type="exact", matched_text="x",
                stream_id=_UUID, session_id=_UUID, timestamp=_NOW,
            )  # type: ignore[call-arg]


class TestSentimentEvent:

    def test_valid(self) -> None:
        e = SentimentEvent(
            stream_id=_UUID, session_id=_UUID, timestamp=_NOW,
            sentiment_label="negative", sentiment_score=0.8,
        )
        assert e.sentiment_score == pytest.approx(0.8)


# ===========================================================================
# KeywordRule model tests
# ===========================================================================


class TestKeywordRule:

    def test_minimal_creation(self) -> None:
        r = KeywordRule(rule_set_name="default", keyword="threat", match_type="exact")
        assert r.keyword == "threat"
        assert r.severity == Severity.MEDIUM

    def test_invalid_match_type(self) -> None:
        with pytest.raises(ValidationError):
            KeywordRule(rule_set_name="s", keyword="x", match_type="wild")

    def test_fuzzy_threshold_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            KeywordRule(
                rule_set_name="s", keyword="x", match_type="fuzzy",
                fuzzy_threshold=1.5,
            )

    def test_enabled_default(self) -> None:
        r = KeywordRule(rule_set_name="s", keyword="k", match_type="regex")
        assert r.enabled is True

    def test_all_match_types(self) -> None:
        for mt in RuleMatchType:
            r = KeywordRule(rule_set_name="s", keyword="k", match_type=mt.value)
            assert r.match_type == mt


class TestAlertChannelConfig:

    def test_minimal_creation(self) -> None:
        c = AlertChannelConfig(channel_type="slack", config={"webhook": "http://x"})
        assert c.channel_type == ChannelType.SLACK

    def test_invalid_channel_type(self) -> None:
        with pytest.raises(ValidationError):
            AlertChannelConfig(channel_type="pigeon", config={})

    def test_enabled_default(self) -> None:
        c = AlertChannelConfig(channel_type="webhook", config={})
        assert c.enabled is True

    def test_all_channel_types(self) -> None:
        for ct in ChannelType:
            c = AlertChannelConfig(channel_type=ct.value, config={})
            assert c.channel_type == ct


# ===========================================================================
# AuditAnchor model tests
# ===========================================================================


class TestAuditAnchor:

    def test_minimal_creation(self) -> None:
        a = AuditAnchor(
            merkle_root="a" * 64,
            segment_count=10,
            first_segment_id=_UUID,
            last_segment_id=_UUID,
        )
        assert a.segment_count == 10
        assert a.anchor_id is None  # BIGSERIAL, set by DB

    def test_missing_merkle_root(self) -> None:
        with pytest.raises(ValidationError):
            AuditAnchor(
                segment_count=5,
                first_segment_id=_UUID,
                last_segment_id=_UUID,
            )  # type: ignore[call-arg]

    def test_invalid_segment_uuid(self) -> None:
        with pytest.raises(ValidationError):
            AuditAnchor(
                merkle_root="x" * 64,
                segment_count=1,
                first_segment_id="not-uuid",
                last_segment_id=_UUID,
            )


# ===========================================================================
# Enum value tests
# ===========================================================================


class TestEnums:

    def test_source_type_values(self) -> None:
        assert set(e.value for e in SourceType) == {
            "rtsp", "hls", "dash", "webrtc", "sip", "file", "meeting_relay",
        }

    def test_alert_type_values(self) -> None:
        assert set(e.value for e in AlertType) == {
            "keyword", "sentiment", "compliance", "intent",
        }

    def test_severity_order(self) -> None:
        expected = ["low", "medium", "high", "critical"]
        actual = [e.value for e in Severity]
        assert actual == expected

    def test_channel_type_completeness(self) -> None:
        assert len(ChannelType) == 7
