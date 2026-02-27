"""
Alert API schemas for VoxSentinel.

Pydantic request/response models for alert retrieval, including
alert list responses with delivery status tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AlertSummary(BaseModel):
    alert_id: UUID
    stream_id: UUID
    stream_name: str | None = None
    alert_type: str
    severity: str
    matched_rule: str | None = None
    match_type: str | None = None
    matched_text: str | None = None
    speaker_id: str | None = None
    surrounding_context: str | None = None
    created_at: datetime | None = None
    delivery_status: dict[str, str] | None = None


class AlertListResponse(BaseModel):
    alerts: list[AlertSummary]
    total: int


class AlertDetailResponse(BaseModel):
    alert_id: UUID
    session_id: UUID
    stream_id: UUID
    segment_id: UUID | None = None
    alert_type: str
    severity: str
    matched_rule: str | None = None
    match_type: str | None = None
    similarity_score: float | None = None
    matched_text: str | None = None
    surrounding_context: str | None = None
    speaker_id: str | None = None
    channel: str | None = None
    sentiment_scores: dict[str, float] | None = None
    asr_backend_used: str | None = None
    delivered_to: list[str] | None = None
    delivery_status: dict[str, str] | None = None
    deduplicated: bool = False
    created_at: datetime | None = None


class AlertChannelCreateRequest(BaseModel):
    channel_type: str = Field(...)
    config: dict[str, Any] = Field(default_factory=dict)
    min_severity: str = Field(default="low")
    alert_types: list[str] | None = None
    stream_ids: list[str] | None = None
    enabled: bool = Field(default=True)


class AlertChannelCreateResponse(BaseModel):
    channel_id: UUID
    created_at: datetime | None = None


class AlertChannelSummary(BaseModel):
    channel_id: UUID
    channel_type: str
    config: dict[str, Any] | None = None
    min_severity: str | None = None
    alert_types: list[str] | None = None
    stream_ids: list[str] | None = None
    enabled: bool = True
    created_at: datetime | None = None


class AlertChannelListResponse(BaseModel):
    channels: list[AlertChannelSummary]
    total: int


class AlertChannelUpdateRequest(BaseModel):
    config: dict[str, Any] | None = None
    min_severity: str | None = None
    alert_types: list[str] | None = None
    stream_ids: list[str] | None = None
    enabled: bool | None = None
