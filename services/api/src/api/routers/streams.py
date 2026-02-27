"""
Stream management API router for VoxSentinel.

CRUD endpoints for creating, reading, updating, deleting, pausing,
and resuming audio streams.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_db_session, get_redis
from api.schemas.stream_schemas import (
    StreamCreateRequest,
    StreamCreateResponse,
    StreamDetailResponse,
    StreamListResponse,
    StreamSummary,
    StreamUpdateRequest,
)

from tg_common.db.orm_models import SessionORM, StreamORM

router = APIRouter(prefix="/streams", tags=["streams"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.post("", status_code=201, response_model=StreamCreateResponse)
async def create_stream(
    body: StreamCreateRequest,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> StreamCreateResponse:
    stream_id = _uuid.uuid4()
    session_id = _uuid.uuid4()
    now = _utc_now()

    stream = StreamORM(
        stream_id=stream_id,
        name=body.name,
        source_type=body.source_type,
        source_url=body.source_url,
        asr_backend=body.asr_backend,
        asr_fallback_backend=body.asr_fallback_backend,
        language_override=body.language_override,
        vad_threshold=body.vad_threshold,
        chunk_size_ms=body.chunk_size_ms,
        status="active",
        session_id=session_id,
        metadata_=body.metadata,
    )
    session = SessionORM(
        session_id=session_id,
        stream_id=stream_id,
        asr_backend_used=body.asr_backend,
    )
    if db is not None:
        db.add(stream)
        db.add(session)
        await db.commit()

    if redis is not None:
        await redis.publish(
            "stream_started",
            {"stream_id": str(stream_id), "session_id": str(session_id)},
        )

    return StreamCreateResponse(
        stream_id=stream_id,
        status="active",
        session_id=session_id,
        created_at=now,
    )


@router.get("", response_model=StreamListResponse)
async def list_streams(db: Any = Depends(get_db_session)) -> StreamListResponse:
    if db is None:
        return StreamListResponse(streams=[], total=0)

    from sqlalchemy import select

    result = await db.execute(select(StreamORM))
    rows = result.scalars().all()
    streams = [
        StreamSummary(
            stream_id=s.stream_id,
            name=s.name,
            status=s.status,
            source_type=s.source_type,
            asr_backend=s.asr_backend,
            session_id=s.session_id,
            created_at=s.created_at,
        )
        for s in rows
    ]
    return StreamListResponse(streams=streams, total=len(streams))


@router.get("/{stream_id}", response_model=StreamDetailResponse)
async def get_stream(stream_id: _uuid.UUID, db: Any = Depends(get_db_session)) -> Any:
    if db is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    from sqlalchemy import select

    result = await db.execute(
        select(StreamORM).where(StreamORM.stream_id == stream_id),
    )
    stream = result.scalar_one_or_none()
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    return StreamDetailResponse(
        stream_id=stream.stream_id,
        name=stream.name,
        status=stream.status,
        source_type=stream.source_type,
        source_url=stream.source_url,
        asr_backend=stream.asr_backend,
        asr_fallback_backend=stream.asr_fallback_backend,
        language_override=stream.language_override,
        vad_threshold=stream.vad_threshold,
        chunk_size_ms=stream.chunk_size_ms,
        session_id=stream.session_id,
        created_at=stream.created_at,
        updated_at=stream.updated_at,
        metadata=stream.metadata_,
    )


@router.patch("/{stream_id}", response_model=StreamDetailResponse)
async def update_stream(
    stream_id: _uuid.UUID,
    body: StreamUpdateRequest,
    db: Any = Depends(get_db_session),
) -> Any:
    if db is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    from sqlalchemy import select

    result = await db.execute(
        select(StreamORM).where(StreamORM.stream_id == stream_id),
    )
    stream = result.scalar_one_or_none()
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "metadata":
            setattr(stream, "metadata_", value)
        else:
            setattr(stream, field, value)
    await db.commit()

    return await get_stream(stream_id, db)


@router.delete("/{stream_id}", status_code=204)
async def delete_stream(
    stream_id: _uuid.UUID,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> None:
    if db is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    from sqlalchemy import select

    result = await db.execute(
        select(StreamORM).where(StreamORM.stream_id == stream_id),
    )
    stream = result.scalar_one_or_none()
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    await db.delete(stream)
    await db.commit()

    if redis is not None:
        await redis.publish("stream_stopped", {"stream_id": str(stream_id)})


@router.post("/{stream_id}/pause", status_code=200)
async def pause_stream(
    stream_id: _uuid.UUID,
    db: Any = Depends(get_db_session),
) -> dict[str, str]:
    if db is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    from sqlalchemy import select

    result = await db.execute(
        select(StreamORM).where(StreamORM.stream_id == stream_id),
    )
    stream = result.scalar_one_or_none()
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    stream.status = "paused"
    await db.commit()
    return {"status": "paused"}


@router.post("/{stream_id}/resume", status_code=200)
async def resume_stream(
    stream_id: _uuid.UUID,
    db: Any = Depends(get_db_session),
) -> dict[str, str]:
    if db is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    from sqlalchemy import select

    result = await db.execute(
        select(StreamORM).where(StreamORM.stream_id == stream_id),
    )
    stream = result.scalar_one_or_none()
    if stream is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    stream.status = "active"
    await db.commit()
    return {"status": "active"}
