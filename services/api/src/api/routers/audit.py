"""
Audit verification API router for VoxSentinel.

Endpoints for verifying transcript segment integrity via SHA-256
hashes, Merkle proofs, and audit anchor records.
"""

from __future__ import annotations

import hashlib
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session

try:
    from tg_common.db.orm_models import AuditAnchorORM, TranscriptSegmentORM
except ImportError:  # pragma: no cover
    AuditAnchorORM = None  # type: ignore[assignment,misc]
    TranscriptSegmentORM = None  # type: ignore[assignment,misc]

router = APIRouter(prefix="/audit", tags=["audit"])


def _hash_pair(a: str, b: str) -> str:
    combined = min(a, b) + max(a, b)
    return hashlib.sha256(combined.encode()).hexdigest()


def _build_merkle_proof(
    hashes: list[str], target_hash: str,
) -> tuple[list[dict[str, str]], str]:
    """Build Merkle proof for *target_hash* within *hashes*."""
    if not hashes:
        return [], ""

    idx: Optional[int] = None
    for i, h in enumerate(hashes):
        if h == target_hash:
            idx = i
            break
    if idx is None:
        return [], ""

    proof: list[dict[str, str]] = []
    layer = list(hashes)

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])

        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            parent = _hash_pair(layer[i], layer[i + 1])
            next_layer.append(parent)
            if i == idx or i + 1 == idx:
                sibling_pos = "right" if idx == i else "left"
                sibling_hash = layer[i + 1] if idx == i else layer[i]
                proof.append({"position": sibling_pos, "hash": sibling_hash})
                idx = i // 2
        layer = next_layer

    return proof, layer[0]


class AuditVerifyResponse(BaseModel):
    segment_id: str
    segment_hash: str
    anchor_id: Optional[int] = None
    merkle_root: Optional[str] = None
    merkle_proof: list[dict[str, str]] = []
    verified: bool = False
    anchored_at: Optional[str] = None


@router.get("/verify/{segment_id}", response_model=AuditVerifyResponse)
async def verify_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AuditVerifyResponse:
    # Fetch the segment.
    seg_result = await db.execute(
        select(TranscriptSegmentORM).where(
            TranscriptSegmentORM.segment_id == segment_id,
        ),
    )
    segment = seg_result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    seg_hash = segment.segment_hash or ""

    # Find the audit anchor that covers this segment.
    anchor_result = await db.execute(
        select(AuditAnchorORM).where(
            AuditAnchorORM.first_segment_id <= segment_id,
            AuditAnchorORM.last_segment_id >= segment_id,
        ),
    )
    anchor = anchor_result.scalar_one_or_none()

    if not anchor:
        return AuditVerifyResponse(
            segment_id=str(segment_id),
            segment_hash=seg_hash,
            verified=False,
        )

    # Get all segment hashes in the anchor range.
    range_result = await db.execute(
        select(TranscriptSegmentORM.segment_hash)
        .where(
            TranscriptSegmentORM.segment_id >= anchor.first_segment_id,
            TranscriptSegmentORM.segment_id <= anchor.last_segment_id,
        )
        .order_by(TranscriptSegmentORM.created_at.asc()),
    )
    all_hashes = [r[0] for r in range_result.all() if r[0]]

    proof, computed_root = _build_merkle_proof(all_hashes, seg_hash)
    verified = computed_root == anchor.merkle_root

    return AuditVerifyResponse(
        segment_id=str(segment_id),
        segment_hash=seg_hash,
        anchor_id=anchor.anchor_id,
        merkle_root=anchor.merkle_root,
        merkle_proof=proof,
        verified=verified,
        anchored_at=anchor.anchored_at.isoformat() if anchor.anchored_at else None,
    )
