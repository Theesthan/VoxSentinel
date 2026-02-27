"""initial schema

Revision ID: 5dc94ab43cad
Revises: 
Create Date: 2026-02-27 16:26:58.658028

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5dc94ab43cad'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Custom enum types
source_type_enum = sa.Enum(
    "rtsp", "hls", "dash", "webrtc", "sip", "file", "meeting_relay",
    name="source_type_enum",
)
stream_status_enum = sa.Enum(
    "active", "paused", "error", "stopped",
    name="stream_status_enum",
)
alert_type_enum = sa.Enum(
    "keyword", "sentiment", "compliance", "intent",
    name="alert_type_enum",
)
severity_enum = sa.Enum(
    "low", "medium", "high", "critical",
    name="severity_enum",
)
match_type_enum = sa.Enum(
    "exact", "fuzzy", "regex", "sentiment_threshold", "intent",
    name="match_type_enum",
)
rule_match_type_enum = sa.Enum(
    "exact", "fuzzy", "regex",
    name="rule_match_type_enum",
)
channel_type_enum = sa.Enum(
    "websocket", "webhook", "slack", "teams", "email", "sms", "signal",
    name="channel_type_enum",
)


def upgrade() -> None:
    # Create enum types
    source_type_enum.create(op.get_bind(), checkfirst=True)
    stream_status_enum.create(op.get_bind(), checkfirst=True)
    alert_type_enum.create(op.get_bind(), checkfirst=True)
    severity_enum.create(op.get_bind(), checkfirst=True)
    match_type_enum.create(op.get_bind(), checkfirst=True)
    rule_match_type_enum.create(op.get_bind(), checkfirst=True)
    channel_type_enum.create(op.get_bind(), checkfirst=True)

    # streams
    op.create_table(
        "streams",
        sa.Column("stream_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("asr_backend", sa.String(100), nullable=False, server_default="deepgram_nova2"),
        sa.Column("asr_fallback_backend", sa.String(100), nullable=True),
        sa.Column("language_override", sa.String(10), nullable=True),
        sa.Column("vad_threshold", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("chunk_size_ms", sa.Integer, nullable=False, server_default="280"),
        sa.Column("status", stream_status_enum, nullable=False, server_default="stopped"),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )

    # sessions
    op.create_table(
        "sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stream_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("streams.stream_id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("asr_backend_used", sa.String(100), nullable=False, server_default="deepgram_nova2"),
        sa.Column("total_segments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_alerts", sa.Integer, nullable=False, server_default="0"),
    )

    # transcript_segments
    op.create_table(
        "transcript_segments",
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("stream_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("streams.stream_id"), nullable=False),
        sa.Column("speaker_id", sa.String(100), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_offset_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("end_offset_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("text_redacted", sa.Text, nullable=False, server_default=""),
        sa.Column("text_original", sa.Text, nullable=True),
        sa.Column("word_timestamps", postgresql.JSONB, nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("asr_backend", sa.String(100), nullable=False, server_default="deepgram_nova2"),
        sa.Column("asr_confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("sentiment_label", sa.String(20), nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("intent_labels", postgresql.JSONB, nullable=True),
        sa.Column("pii_entities_found", postgresql.JSONB, nullable=True),
        sa.Column("segment_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # alerts
    op.create_table(
        "alerts",
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("stream_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("streams.stream_id"), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcript_segments.segment_id"), nullable=True),
        sa.Column("alert_type", alert_type_enum, nullable=False),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("matched_rule", sa.String(255), nullable=False, server_default=""),
        sa.Column("match_type", match_type_enum, nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("matched_text", sa.Text, nullable=False, server_default=""),
        sa.Column("surrounding_context", sa.Text, nullable=False, server_default=""),
        sa.Column("speaker_id", sa.String(100), nullable=True),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("sentiment_scores", postgresql.JSONB, nullable=True),
        sa.Column("asr_backend_used", sa.String(100), nullable=True),
        sa.Column("delivered_to", postgresql.JSONB, nullable=True),
        sa.Column("delivery_status", postgresql.JSONB, nullable=True),
        sa.Column("deduplicated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # keyword_rules
    op.create_table(
        "keyword_rules",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_set_name", sa.String(255), nullable=False),
        sa.Column("keyword", sa.Text, nullable=False),
        sa.Column("match_type", rule_match_type_enum, nullable=False),
        sa.Column("fuzzy_threshold", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("severity", severity_enum, nullable=False, server_default="medium"),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # alert_channel_configs
    op.create_table(
        "alert_channel_configs",
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_type", channel_type_enum, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("min_severity", severity_enum, nullable=False, server_default="low"),
        sa.Column("alert_types", postgresql.JSONB, nullable=True),
        sa.Column("stream_ids", postgresql.JSONB, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # audit_anchors (BIGSERIAL PK)
    op.create_table(
        "audit_anchors",
        sa.Column("anchor_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("merkle_root", sa.String(64), nullable=False),
        sa.Column("segment_count", sa.Integer, nullable=False),
        sa.Column("first_segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("audit_anchors")
    op.drop_table("alert_channel_configs")
    op.drop_table("keyword_rules")
    op.drop_table("alerts")
    op.drop_table("transcript_segments")
    op.drop_table("sessions")
    op.drop_table("streams")

    channel_type_enum.drop(op.get_bind(), checkfirst=True)
    rule_match_type_enum.drop(op.get_bind(), checkfirst=True)
    match_type_enum.drop(op.get_bind(), checkfirst=True)
    severity_enum.drop(op.get_bind(), checkfirst=True)
    alert_type_enum.drop(op.get_bind(), checkfirst=True)
    stream_status_enum.drop(op.get_bind(), checkfirst=True)
    source_type_enum.drop(op.get_bind(), checkfirst=True)
