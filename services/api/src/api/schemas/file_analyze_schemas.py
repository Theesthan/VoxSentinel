"""
File Analyze API schemas for VoxSentinel.

Pydantic request/response models for the asynchronous file analysis
pipeline — upload, status polling, and result retrieval.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileAnalyzeSubmitResponse(BaseModel):
    job_id: UUID
    stream_id: UUID
    session_id: UUID
    status: str = "processing"
    file_name: str
    created_at: datetime


class FileAnalyzeKeywordHit(BaseModel):
    keyword: str
    match_type: str
    severity: str


class FileAnalyzeSegment(BaseModel):
    segment_id: UUID
    speaker_id: str | None = None
    start_offset_ms: int = 0
    end_offset_ms: int = 0
    text: str = ""
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    confidence: float = 0.0
    keywords_matched: list[FileAnalyzeKeywordHit] = Field(default_factory=list)


class FileAnalyzeAlert(BaseModel):
    alert_id: UUID
    alert_type: str
    severity: str
    matched_rule: str | None = None
    match_type: str | None = None
    matched_text: str | None = None
    speaker_id: str | None = None
    surrounding_context: str | None = None
    timestamp_offset_ms: int = 0


class FileAnalyzeSummary(BaseModel):
    total_segments: int = 0
    total_alerts: int = 0
    sentiments: dict[str, int] = Field(default_factory=dict)
    speakers_detected: int = 0
    languages_detected: list[str] = Field(default_factory=list)


class FileAnalyzeStatusResponse(BaseModel):
    job_id: UUID
    status: str
    progress_pct: int = 0
    file_name: str
    stream_id: UUID | None = None
    session_id: UUID | None = None
    duration_seconds: float | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    transcript: list[FileAnalyzeSegment] = Field(default_factory=list)
    alerts: list[FileAnalyzeAlert] = Field(default_factory=list)
    summary: FileAnalyzeSummary | None = None


class FileAnalyzeJobSummary(BaseModel):
    job_id: UUID
    status: str
    file_name: str
    duration_seconds: float | None = None
    total_alerts: int = 0
    created_at: datetime
    completed_at: datetime | None = None


class FileAnalyzeListResponse(BaseModel):
    jobs: list[FileAnalyzeJobSummary]
    total: int
