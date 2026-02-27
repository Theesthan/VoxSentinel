"""
Stream API schemas for VoxSentinel.

Pydantic request/response models for stream CRUD operations,
including create, update, and list responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StreamCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    source_type: str = Field(...)
    source_url: str = Field(...)
    asr_backend: str = Field(default="deepgram_nova2", max_length=100)
    asr_fallback_backend: str | None = Field(default=None, max_length=100)
    language_override: str | None = Field(default=None, max_length=10)
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    chunk_size_ms: int = Field(default=280, ge=20)
    keyword_rule_set_names: list[str] = Field(default_factory=list)
    alert_channel_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default=None)


class StreamCreateResponse(BaseModel):
    stream_id: UUID
    status: str
    session_id: UUID
    created_at: datetime


class StreamSummary(BaseModel):
    stream_id: UUID
    name: str
    status: str
    source_type: str
    asr_backend: str
    session_id: UUID | None
    created_at: datetime


class StreamListResponse(BaseModel):
    streams: list[StreamSummary]
    total: int


class StreamDetailResponse(BaseModel):
    stream_id: UUID
    name: str
    status: str
    source_type: str
    source_url: str
    asr_backend: str
    asr_fallback_backend: str | None
    language_override: str | None
    vad_threshold: float
    chunk_size_ms: int
    session_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None


class StreamUpdateRequest(BaseModel):
    name: str | None = None
    source_url: str | None = None
    asr_backend: str | None = None
    asr_fallback_backend: str | None = None
    language_override: str | None = None
    vad_threshold: float | None = None
    chunk_size_ms: int | None = None
    metadata: dict[str, Any] | None = None
