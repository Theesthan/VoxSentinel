"""
Alert retrieval API router for VoxSentinel.

Endpoints for listing and retrieving alert records with filtering
by stream, alert type, severity, and time range.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas.alert_schemas import (
    AlertDetailResponse,
    AlertListResponse,
    AlertSummary,
)

try:
    from tg_common.db.orm_models import AlertORM
except ImportError:  # pragma: no cover
    AlertORM = None  # type: ignore[assignment,misc]

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    stream_id: Optional[UUID] = Query(None),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> AlertListResponse:
    stmt = select(AlertORM)
    if stream_id:
        stmt = stmt.where(AlertORM.stream_id == stream_id)
    if alert_type:
        stmt = stmt.where(AlertORM.alert_type == alert_type)
    if severity:
        stmt = stmt.where(AlertORM.severity == severity)
    if date_from:
        stmt = stmt.where(AlertORM.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AlertORM.created_at <= date_to)

    stmt = stmt.order_by(AlertORM.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    alerts = [
        AlertSummary(
            alert_id=str(r.alert_id),
            stream_id=str(r.stream_id),
            stream_name=None,
            alert_type=str(r.alert_type),
            severity=str(r.severity),
            matched_rule=r.matched_rule,
            match_type=str(r.match_type) if r.match_type else None,
            matched_text=r.matched_text,
            speaker_id=r.speaker_id,
            surrounding_context=r.surrounding_context,
            created_at=r.created_at.isoformat() if r.created_at else None,
            delivery_status=r.delivery_status,
        )
        for r in rows
    ]
    return AlertListResponse(alerts=alerts, total=len(alerts))


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AlertDetailResponse:
    result = await db.execute(
        select(AlertORM).where(AlertORM.alert_id == alert_id),
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertDetailResponse(
        alert_id=str(row.alert_id),
        stream_id=str(row.stream_id),
        session_id=str(row.session_id),
        segment_id=str(row.segment_id) if row.segment_id else None,
        alert_type=str(row.alert_type),
        severity=str(row.severity),
        matched_rule=row.matched_rule,
        match_type=str(row.match_type) if row.match_type else None,
        similarity_score=row.similarity_score,
        matched_text=row.matched_text,
        surrounding_context=row.surrounding_context,
        speaker_id=row.speaker_id,
        channel=row.channel,
        sentiment_scores=row.sentiment_scores,
        asr_backend_used=row.asr_backend_used,
        delivered_to=row.delivered_to,
        delivery_status=row.delivery_status,
        deduplicated=row.deduplicated,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )
