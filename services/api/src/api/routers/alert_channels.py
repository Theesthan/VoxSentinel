"""
Alert channel configuration API router for VoxSentinel.

CRUD endpoints for managing alert delivery channel configurations
(WebSocket, webhook, Slack, etc.).
"""

from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas.alert_schemas import (
    AlertChannelCreateRequest,
    AlertChannelCreateResponse,
    AlertChannelListResponse,
    AlertChannelSummary,
    AlertChannelUpdateRequest,
)

try:
    from tg_common.db.orm_models import AlertChannelConfigORM
except ImportError:  # pragma: no cover
    AlertChannelConfigORM = None  # type: ignore[assignment,misc]

router = APIRouter(prefix="/alert-channels", tags=["alert-channels"])


@router.post("", response_model=AlertChannelCreateResponse, status_code=201)
async def create_alert_channel(
    body: AlertChannelCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AlertChannelCreateResponse:
    channel_id = uuid.uuid4()
    row = AlertChannelConfigORM(
        channel_id=channel_id,
        channel_type=body.channel_type,
        config=body.config,
        min_severity=body.min_severity,
        alert_types=body.alert_types,
        stream_ids=body.stream_ids,
        enabled=body.enabled if body.enabled is not None else True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return AlertChannelCreateResponse(
        channel_id=str(channel_id),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("", response_model=AlertChannelListResponse)
async def list_alert_channels(
    channel_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> AlertChannelListResponse:
    stmt = select(AlertChannelConfigORM)
    if channel_type:
        stmt = stmt.where(AlertChannelConfigORM.channel_type == channel_type)
    if enabled is not None:
        stmt = stmt.where(AlertChannelConfigORM.enabled == enabled)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    channels = [
        AlertChannelSummary(
            channel_id=str(r.channel_id),
            channel_type=str(r.channel_type),
            config=r.config,
            min_severity=str(r.min_severity) if r.min_severity else None,
            alert_types=r.alert_types,
            stream_ids=r.stream_ids,
            enabled=r.enabled,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
    return AlertChannelListResponse(channels=channels, total=len(channels))


@router.patch("/{channel_id}", response_model=AlertChannelSummary)
async def update_alert_channel(
    channel_id: UUID,
    body: AlertChannelUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AlertChannelSummary:
    result = await db.execute(
        select(AlertChannelConfigORM).where(
            AlertChannelConfigORM.channel_id == channel_id,
        ),
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert channel not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(row, key, val)
    await db.commit()
    await db.refresh(row)

    return AlertChannelSummary(
        channel_id=str(row.channel_id),
        channel_type=str(row.channel_type),
        config=row.config,
        min_severity=str(row.min_severity) if row.min_severity else None,
        alert_types=row.alert_types,
        stream_ids=row.stream_ids,
        enabled=row.enabled,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.delete("/{channel_id}", status_code=204)
async def delete_alert_channel(
    channel_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    result = await db.execute(
        select(AlertChannelConfigORM).where(
            AlertChannelConfigORM.channel_id == channel_id,
        ),
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Alert channel not found")
    await db.delete(row)
    await db.commit()
