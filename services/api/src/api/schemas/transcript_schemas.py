"""
Transcript API schemas for VoxSentinel.

Pydantic request/response models for transcript segment retrieval,
including time-range and speaker-filtered queries.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TranscriptSegmentResponse(BaseModel):
    segment_id: UUID
    speaker_id: str | None
    start_time: datetime
    end_time: datetime
    text: str
    sentiment_label: str | None
    sentiment_score: float | None
    language: str
    confidence: float


class TranscriptResponse(BaseModel):
    session_id: UUID
    segments: list[TranscriptSegmentResponse]
    total: int
