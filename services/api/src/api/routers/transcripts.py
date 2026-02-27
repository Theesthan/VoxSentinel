"""
Transcript retrieval API router for VoxSentinel.

Endpoints for fetching transcript segments by session with time range
and speaker filtering.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db_session
from api.schemas.transcript_schemas import (
    TranscriptResponse,
    TranscriptSegmentResponse,
)

from tg_common.db.orm_models import TranscriptSegmentORM

router = APIRouter(tags=["transcripts"])


@router.get(
    "/sessions/{session_id}/transcript",
    response_model=TranscriptResponse,
)
async def get_transcript(
    session_id: _uuid.UUID,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    speaker_id: str | None = Query(default=None),
    db: Any = Depends(get_db_session),
) -> TranscriptResponse:
    if db is None:
        return TranscriptResponse(session_id=session_id, segments=[], total=0)

    from sqlalchemy import select

    stmt = (
        select(TranscriptSegmentORM)
        .where(TranscriptSegmentORM.session_id == session_id)
        .order_by(TranscriptSegmentORM.start_time.asc())
    )
    if from_time is not None:
        stmt = stmt.where(TranscriptSegmentORM.start_time >= from_time)
    if to_time is not None:
        stmt = stmt.where(TranscriptSegmentORM.end_time <= to_time)
    if speaker_id is not None:
        stmt = stmt.where(TranscriptSegmentORM.speaker_id == speaker_id)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    segments = [
        TranscriptSegmentResponse(
            segment_id=s.segment_id,
            speaker_id=s.speaker_id,
            start_time=s.start_time,
            end_time=s.end_time,
            text=s.text_redacted,
            sentiment_label=s.sentiment_label,
            sentiment_score=s.sentiment_score,
            language=s.language,
            confidence=s.asr_confidence,
        )
        for s in rows
    ]
    return TranscriptResponse(
        session_id=session_id,
        segments=segments,
        total=len(segments),
    )
