"""
Search API schemas for VoxSentinel.

Pydantic request/response models for full-text search queries
and highlighted search result responses.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    search_type: str = Field(default="fuzzy")
    stream_ids: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    speaker_id: str | None = None
    language: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class SearchHit(BaseModel):
    segment_id: str
    session_id: str
    stream_id: str
    stream_name: str | None = None
    speaker_id: str | None = None
    timestamp: str
    text: str
    sentiment_label: str | None = None
    score: float | None = None


class SearchResponse(BaseModel):
    results: list[SearchHit]
    total: int
