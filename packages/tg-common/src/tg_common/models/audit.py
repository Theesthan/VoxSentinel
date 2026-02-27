"""
Audit data model for VoxSentinel.

Defines the Pydantic model for cryptographic audit anchors, including
Merkle root hashes and segment range references used to verify
transcript integrity and non-tampering.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class AuditAnchor(BaseModel):
    """A Merkle-tree audit anchor covering a range of transcript segments.

    The ``audit_anchors`` table is append-only — the application role has no
    UPDATE or DELETE permission.

    Attributes:
        anchor_id: Auto-incrementing primary key (BIGSERIAL).
        merkle_root: SHA-256 Merkle root hash of covered segments.
        segment_count: Number of segments in this anchor batch.
        first_segment_id: UUID of the first covered segment.
        last_segment_id: UUID of the last covered segment.
        anchored_at: Timestamp when the anchor was created (UTC).
    """

    model_config = {"from_attributes": True}

    anchor_id: int | None = Field(
        default=None,
        description="Auto-incrementing primary key (assigned by the database).",
    )
    merkle_root: str = Field(
        ...,
        max_length=64,
        description="SHA-256 Merkle root hash.",
    )
    segment_count: int = Field(..., ge=1, description="Number of segments in this anchor.")
    first_segment_id: UUID = Field(..., description="First covered segment UUID.")
    last_segment_id: UUID = Field(..., description="Last covered segment UUID.")
    anchored_at: datetime = Field(
        default_factory=_utc_now,
        description="Anchor creation timestamp (UTC).",
    )
