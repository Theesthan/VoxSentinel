"""
Keyword rule and alert-channel configuration models for VoxSentinel.

Defines the Pydantic models for configurable keyword detection rules
(exact, fuzzy, regex) with severity levels and category groupings,
and for alert-channel configurations (Slack, webhooks, etc.).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from tg_common.models.alert import AlertType, Severity


def _utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class RuleMatchType(str, enum.Enum):
    """Keyword-rule matching mode."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    REGEX = "regex"


class ChannelType(str, enum.Enum):
    """Supported alert-channel types."""

    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    SMS = "sms"
    SIGNAL = "signal"


class KeywordRule(BaseModel):
    """A configurable keyword detection rule.

    Attributes:
        rule_id: Unique identifier.
        rule_set_name: Logical grouping name.
        keyword: Keyword, phrase, or regex pattern.
        match_type: Matching mode (exact/fuzzy/regex).
        fuzzy_threshold: Similarity threshold for fuzzy matching (0.0–1.0).
        severity: Alert severity when matched.
        category: Rule category (security, compliance, etc.).
        language: Language code (None = all languages).
        enabled: Whether this rule is active.
        created_at: Creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).
    """

    model_config = {"from_attributes": True}

    rule_id: UUID = Field(default_factory=uuid4, description="Unique identifier.")
    rule_set_name: str = Field(
        ...,
        max_length=255,
        description="Logical grouping name.",
    )
    keyword: str = Field(..., description="Keyword, phrase, or regex pattern.")
    match_type: RuleMatchType = Field(..., description="Matching mode.")
    fuzzy_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for fuzzy matching.",
    )
    severity: Severity = Field(default=Severity.MEDIUM, description="Alert severity when matched.")
    category: str = Field(
        default="general",
        max_length=100,
        description="Rule category.",
    )
    language: str | None = Field(
        default=None,
        max_length=10,
        description="Language code (None = all languages).",
    )
    enabled: bool = Field(default=True, description="Whether this rule is active.")
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="Creation timestamp (UTC).",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="Last update timestamp (UTC).",
    )


class AlertChannelConfig(BaseModel):
    """Configuration for an alert delivery channel.

    Attributes:
        channel_id: Unique identifier.
        channel_type: Channel type (websocket, slack, webhook, …).
        config: Channel-specific configuration (URL, token, etc.).
        min_severity: Minimum severity level to trigger this channel.
        alert_types: Alert types this channel receives.
        stream_ids: Stream UUIDs this channel is assigned to (None = all).
        enabled: Whether this channel is active.
        created_at: Creation timestamp (UTC).
    """

    model_config = {"from_attributes": True}

    channel_id: UUID = Field(default_factory=uuid4, description="Unique identifier.")
    channel_type: ChannelType = Field(..., description="Channel type.")
    config: dict[str, str] = Field(
        default_factory=dict,
        description="Channel-specific configuration.",
    )
    min_severity: Severity = Field(
        default=Severity.LOW,
        description="Minimum severity to trigger.",
    )
    alert_types: list[AlertType] = Field(
        default_factory=list,
        description="Alert types this channel receives.",
    )
    stream_ids: list[UUID] | None = Field(
        default=None,
        description="Stream UUIDs (None = all streams).",
    )
    enabled: bool = Field(default=True, description="Whether this channel is active.")
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="Creation timestamp (UTC).",
    )
