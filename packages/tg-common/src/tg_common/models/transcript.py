"""
Transcript data models for VoxSentinel.

Defines the Pydantic models for TranscriptToken (real-time ASR output)
and TranscriptSegment (stored finalized transcript with speaker, sentiment,
PII redaction status, and audit hash).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class WordTimestamp(BaseModel):
    """A single word with its timing and confidence from ASR output.

    Attributes:
        word: The transcribed word.
        start_ms: Start offset in milliseconds from session start.
        end_ms: End offset in milliseconds from session start.
        confidence: ASR confidence for this word (0.0–1.0).
    """

    model_config = {"from_attributes": True}

    word: str = Field(..., description="The transcribed word.")
    start_ms: int = Field(..., ge=0, description="Start offset in ms from session start.")
    end_ms: int = Field(..., ge=0, description="End offset in ms from session start.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="ASR confidence for this word.")


class TranscriptToken(BaseModel):
    """A real-time transcript token emitted by the ASR engine.

    This is the unified output format from all ASR backends, carrying partial
    or final transcript text with word-level timestamps.

    Attributes:
        text: Transcribed text for this token.
        is_final: Whether this is a finalized (non-partial) token.
        start_time: Token start timestamp (UTC).
        end_time: Token end timestamp (UTC).
        confidence: Overall ASR confidence (0.0–1.0).
        language: Detected language code (BCP-47).
        word_timestamps: Per-word timing and confidence list.
    """

    model_config = {"from_attributes": True}

    text: str = Field(..., description="Transcribed text for this token.")
    is_final: bool = Field(default=False, description="Whether this is a finalized token.")
    start_time: datetime = Field(..., description="Token start timestamp (UTC).")
    end_time: datetime = Field(..., description="Token end timestamp (UTC).")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall ASR confidence.")
    language: str = Field(default="en", max_length=10, description="Detected language code.")
    word_timestamps: list[WordTimestamp] = Field(
        default_factory=list,
        description="Per-word timing and confidence list.",
    )


class TranscriptSegment(BaseModel):
    """A finalized, stored transcript segment with full metadata.

    Attributes:
        segment_id: Unique identifier.
        session_id: Parent session UUID.
        stream_id: Parent stream UUID.
        speaker_id: Speaker label (e.g. ``SPEAKER_00``).
        start_time: Segment start (absolute UTC).
        end_time: Segment end (absolute UTC).
        start_offset_ms: Offset in ms from session start.
        end_offset_ms: Offset in ms from session start.
        text_redacted: PII-redacted transcript text.
        text_original: Original transcript text (restricted access).
        word_timestamps: Array of per-word timing objects.
        language: Detected language code.
        asr_backend: ASR engine used.
        asr_confidence: Overall confidence score.
        sentiment_label: Sentiment classification result.
        sentiment_score: Sentiment confidence score.
        intent_labels: Detected intent labels.
        pii_entities_found: PII entity types detected before redaction.
        segment_hash: SHA-256 audit hash.
        created_at: Storage timestamp (UTC).
    """

    model_config = {"from_attributes": True}

    segment_id: UUID = Field(default_factory=uuid4, description="Unique identifier.")
    session_id: UUID = Field(..., description="Parent session UUID.")
    stream_id: UUID = Field(..., description="Parent stream UUID.")
    speaker_id: str | None = Field(
        default=None,
        max_length=100,
        description="Speaker label.",
    )
    start_time: datetime = Field(..., description="Segment start (absolute UTC).")
    end_time: datetime = Field(..., description="Segment end (absolute UTC).")
    start_offset_ms: int = Field(default=0, ge=0, description="Offset in ms from session start.")
    end_offset_ms: int = Field(default=0, ge=0, description="Offset in ms from session start.")
    text_redacted: str = Field(default="", description="PII-redacted transcript text.")
    text_original: str | None = Field(
        default=None,
        description="Original transcript text (restricted access).",
    )
    word_timestamps: list[WordTimestamp] = Field(
        default_factory=list,
        description="Per-word timing objects.",
    )
    language: str = Field(default="en", max_length=10, description="Detected language code.")
    asr_backend: str = Field(
        default="deepgram_nova2",
        max_length=100,
        description="ASR engine used.",
    )
    asr_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score.",
    )
    sentiment_label: str | None = Field(
        default=None,
        max_length=20,
        description="Sentiment classification (positive/neutral/negative).",
    )
    sentiment_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Sentiment confidence score.",
    )
    intent_labels: list[str] = Field(
        default_factory=list,
        description="Detected intent labels.",
    )
    pii_entities_found: list[str] = Field(
        default_factory=list,
        description="PII entity types detected before redaction.",
    )
    segment_hash: str | None = Field(
        default=None,
        max_length=64,
        description="SHA-256 audit hash.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="Storage timestamp (UTC).",
    )
