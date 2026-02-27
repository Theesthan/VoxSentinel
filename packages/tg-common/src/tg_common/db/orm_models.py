"""
SQLAlchemy ORM models for VoxSentinel.

Defines the database table mappings for streams, sessions, transcript
segments, alerts, keyword rules, alert channel configurations, and
audit anchors using SQLAlchemy 2.0 declarative style with
``MappedColumn`` / ``mapped_column``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    """Return timezone-aware UTC now for server defaults."""
    return datetime.now(timezone.utc)


# ── Base class ──


class Base(DeclarativeBase):
    """Declarative base for all VoxSentinel ORM models."""


# ── Enum values (mirroring Pydantic enums) ──

SOURCE_TYPE_ENUM = Enum(
    "rtsp", "hls", "dash", "webrtc", "sip", "file", "meeting_relay",
    name="source_type_enum",
)
STREAM_STATUS_ENUM = Enum(
    "active", "paused", "error", "stopped",
    name="stream_status_enum",
)
ALERT_TYPE_ENUM = Enum(
    "keyword", "sentiment", "compliance", "intent",
    name="alert_type_enum",
)
SEVERITY_ENUM = Enum(
    "low", "medium", "high", "critical",
    name="severity_enum",
)
MATCH_TYPE_ENUM = Enum(
    "exact", "fuzzy", "regex", "sentiment_threshold", "intent",
    name="match_type_enum",
)
RULE_MATCH_TYPE_ENUM = Enum(
    "exact", "fuzzy", "regex",
    name="rule_match_type_enum",
)
CHANNEL_TYPE_ENUM = Enum(
    "websocket", "webhook", "slack", "teams", "email", "sms", "signal",
    name="channel_type_enum",
)


# ── ORM models ──


class StreamORM(Base):
    """ORM model for the ``streams`` table."""

    __tablename__ = "streams"

    stream_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(SOURCE_TYPE_ENUM, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    asr_backend: Mapped[str] = mapped_column(String(100), nullable=False, default="deepgram_nova2")
    asr_fallback_backend: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language_override: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vad_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    chunk_size_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=280)
    status: Mapped[str] = mapped_column(
        STREAM_STATUS_ENUM, nullable=False, default="stopped",
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now,
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True,
    )

    # Relationships
    sessions: Mapped[list[SessionORM]] = relationship(
        back_populates="stream", cascade="all, delete-orphan",
    )


class SessionORM(Base):
    """ORM model for the ``sessions`` table."""

    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    stream_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("streams.stream_id"), nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    asr_backend_used: Mapped[str] = mapped_column(
        String(100), nullable=False, default="deepgram_nova2",
    )
    total_segments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_alerts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    stream: Mapped[StreamORM] = relationship(back_populates="sessions")
    segments: Mapped[list[TranscriptSegmentORM]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
    )
    alerts: Mapped[list[AlertORM]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
    )


class TranscriptSegmentORM(Base):
    """ORM model for the ``transcript_segments`` table."""

    __tablename__ = "transcript_segments"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False,
    )
    stream_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("streams.stream_id"), nullable=False,
    )
    speaker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    start_offset_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    end_offset_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    text_redacted: Mapped[str] = mapped_column(Text, nullable=False, default="")
    text_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_timestamps: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    asr_backend: Mapped[str] = mapped_column(
        String(100), nullable=False, default="deepgram_nova2",
    )
    asr_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    intent_labels: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    pii_entities_found: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    segment_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )

    # Relationships
    session: Mapped[SessionORM] = relationship(back_populates="segments")
    alerts: Mapped[list[AlertORM]] = relationship(
        back_populates="segment", cascade="all, delete-orphan",
    )


class AlertORM(Base):
    """ORM model for the ``alerts`` table."""

    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False,
    )
    stream_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("streams.stream_id"), nullable=False,
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transcript_segments.segment_id"),
        nullable=True,
    )
    alert_type: Mapped[str] = mapped_column(ALERT_TYPE_ENUM, nullable=False)
    severity: Mapped[str] = mapped_column(SEVERITY_ENUM, nullable=False)
    matched_rule: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    match_type: Mapped[str] = mapped_column(MATCH_TYPE_ENUM, nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    surrounding_context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    speaker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sentiment_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    asr_backend_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivered_to: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    delivery_status: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    deduplicated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )

    # Relationships
    session: Mapped[SessionORM] = relationship(back_populates="alerts")
    segment: Mapped[TranscriptSegmentORM | None] = relationship(back_populates="alerts")


class KeywordRuleORM(Base):
    """ORM model for the ``keyword_rules`` table."""

    __tablename__ = "keyword_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    rule_set_name: Mapped[str] = mapped_column(String(255), nullable=False)
    keyword: Mapped[str] = mapped_column(Text, nullable=False)
    match_type: Mapped[str] = mapped_column(RULE_MATCH_TYPE_ENUM, nullable=False)
    fuzzy_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    severity: Mapped[str] = mapped_column(SEVERITY_ENUM, nullable=False, default="medium")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now,
    )


class AlertChannelConfigORM(Base):
    """ORM model for the ``alert_channel_configs`` table."""

    __tablename__ = "alert_channel_configs"

    channel_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    channel_type: Mapped[str] = mapped_column(CHANNEL_TYPE_ENUM, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    min_severity: Mapped[str] = mapped_column(SEVERITY_ENUM, nullable=False, default="low")
    alert_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    stream_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )


class AuditAnchorORM(Base):
    """ORM model for the append-only ``audit_anchors`` table."""

    __tablename__ = "audit_anchors"

    anchor_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True,
    )
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_segment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False,
    )
    last_segment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False,
    )
    anchored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now,
    )
