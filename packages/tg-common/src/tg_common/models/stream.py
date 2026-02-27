"""
Stream and Session data models for VoxSentinel.

Defines the Pydantic models representing an audio/video stream source
(including ASR backend, VAD threshold, and metadata) and its associated
sessions — continuous recording periods tied to a stream.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class SourceType(str, enum.Enum):
    """Supported audio/video source types."""

    RTSP = "rtsp"
    HLS = "hls"
    DASH = "dash"
    WEBRTC = "webrtc"
    SIP = "sip"
    FILE = "file"
    MEETING_RELAY = "meeting_relay"


class StreamStatus(str, enum.Enum):
    """Current operational status of a stream."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


def _utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class Stream(BaseModel):
    """An audio/video stream source with its processing configuration.

    Attributes:
        stream_id: Unique identifier.
        name: Human-readable name.
        source_type: Input source type.
        source_url: Connection URL or file path.
        asr_backend: Selected ASR engine identifier.
        asr_fallback_backend: Fallback ASR engine.
        language_override: Force language (None = auto-detect).
        vad_threshold: VAD confidence threshold (0.0–1.0).
        chunk_size_ms: Audio chunk size in milliseconds (default 280).
        status: Current operational status.
        session_id: Current active session UUID.
        created_at: Creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).
        metadata: Additional key-value metadata.
    """

    model_config = {"from_attributes": True}

    stream_id: UUID = Field(default_factory=uuid4, description="Unique identifier.")
    name: str = Field(..., max_length=255, description="Human-readable name.")
    source_type: SourceType = Field(..., description="Input source type.")
    source_url: str = Field(..., description="Connection URL or file path.")
    asr_backend: str = Field(
        default="deepgram_nova2",
        max_length=100,
        description="Selected ASR engine identifier.",
    )
    asr_fallback_backend: str | None = Field(
        default=None,
        max_length=100,
        description="Fallback ASR engine.",
    )
    language_override: str | None = Field(
        default=None,
        max_length=10,
        description="Force language (None = auto-detect).",
    )
    vad_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="VAD confidence threshold.",
    )
    chunk_size_ms: int = Field(
        default=280,
        gt=0,
        description="Audio chunk size in milliseconds.",
    )
    status: StreamStatus = Field(
        default=StreamStatus.STOPPED,
        description="Current operational status.",
    )
    session_id: UUID | None = Field(default=None, description="Current active session UUID.")
    created_at: datetime = Field(default_factory=_utc_now, description="Creation timestamp (UTC).")
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="Last update timestamp (UTC).",
    )
    metadata: dict[str, str | int | float | bool] | None = Field(
        default=None,
        description="Additional key-value metadata.",
    )

    @model_validator(mode="after")
    def _ensure_utc_timestamps(self) -> Stream:
        """Ensure all timestamps carry UTC timezone info."""
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
        return self


class Session(BaseModel):
    """A continuous recording period tied to a stream.

    Attributes:
        session_id: Unique identifier for this session.
        stream_id: Parent stream UUID.
        started_at: Session start timestamp (UTC).
        ended_at: Session end timestamp (None if still active).
        asr_backend_used: ASR backend used for this session.
        total_segments: Count of transcript segments.
        total_alerts: Count of alerts generated.
    """

    model_config = {"from_attributes": True}

    session_id: UUID = Field(default_factory=uuid4, description="Unique session identifier.")
    stream_id: UUID = Field(..., description="Parent stream UUID.")
    started_at: datetime = Field(
        default_factory=_utc_now,
        description="Session start timestamp (UTC).",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Session end timestamp (None if still active).",
    )
    asr_backend_used: str = Field(
        default="deepgram_nova2",
        max_length=100,
        description="ASR backend used for this session.",
    )
    total_segments: int = Field(default=0, ge=0, description="Count of transcript segments.")
    total_alerts: int = Field(default=0, ge=0, description="Count of alerts generated.")
