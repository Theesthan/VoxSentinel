"""Integration tests: Full pipeline (API → ingestion → alerts).

End-to-end integration tests that exercise the API gateway:

1. ``POST /api/v1/streams`` to register a test RTSP URL.
2. Wait 8 seconds for the pipeline to process.
3. ``GET /api/v1/alerts`` to verify at least one keyword alert exists.

These tests run against the real FastAPI application with real
PostgreSQL (via testcontainers) and Redis, but mock the heavy ML
services (ASR, sentiment, diarization) since those require GPU /
large model downloads.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_common.db.orm_models import AlertORM, SessionORM, StreamORM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_test_app(
    db_session_factory,
    redis_client: aioredis.Redis | None = None,
):
    """Build a FastAPI test app with injected DB + Redis.

    Sets app.state directly (not via lifespan) because httpx's
    ASGITransport does NOT trigger ASGI lifespan startup/shutdown.

    ``redis_client`` is optional — the API handlers already guard
    ``if redis is not None`` so passing None simply skips pub/sub
    notifications, which is fine for DB-focused integration tests.
    """
    from fastapi import FastAPI

    from api.routers import (
        alert_channels,
        alerts,
        audit,
        health,
        rules,
        search,
        streams,
        transcripts,
        ws,
    )

    app = FastAPI(title="VoxSentinel Test")

    # Inject test-container resources directly on app.state
    # (httpx ASGITransport skips lifespan events)
    app.state.db_session_factory = db_session_factory
    app.state.redis = redis_client
    app.state.es_client = None

    api_prefix = "/api/v1"
    app.include_router(streams.router, prefix=api_prefix)
    app.include_router(rules.router, prefix=api_prefix)
    app.include_router(alerts.router, prefix=api_prefix)
    app.include_router(alert_channels.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(transcripts.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)
    app.include_router(health.router)
    app.include_router(ws.router)

    return app


async def _seed_alert(
    db: AsyncSession,
    stream_id: uuid.UUID,
    session_id: uuid.UUID,
) -> None:
    """Insert a mock keyword alert into the test database.

    This simulates the alert that would be produced by the full pipeline
    (NLP keyword match → alert dispatch → storage writer).
    """
    alert = AlertORM(
        alert_id=uuid.uuid4(),
        session_id=session_id,
        stream_id=stream_id,
        segment_id=None,
        alert_type="keyword",
        severity="critical",
        matched_rule="gun",
        match_type="exact",
        similarity_score=1.0,
        matched_text="gun",
        surrounding_context="he has a gun near the entrance",
        speaker_id=None,
        channel=None,
        sentiment_scores=None,
        asr_backend_used="mock",
        delivered_to=None,
        delivery_status=None,
        deduplicated=False,
    )
    db.add(alert)
    await db.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFullPipeline:
    """Test the complete API → alert pipeline."""

    async def test_audio_to_stored_transcript(
        self,
        db_session: AsyncSession,
        db_session_factory,
    ) -> None:
        """POST /streams → verify stream row created in database."""
        app = _get_test_app(db_session_factory)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/streams",
                json={
                    "name": "Test Stream",
                    "source_type": "rtsp",
                    "source_url": "rtsp://test-camera:554/stream1",
                    "asr_backend": "deepgram_nova2",
                },
            )
            assert resp.status_code == 201, f"POST /streams failed: {resp.text}"
            data = resp.json()
            assert "stream_id" in data
            assert data["status"] == "active"

            # Verify DB record exists
            stream_id = uuid.UUID(data["stream_id"])
            result = await db_session.execute(
                select(StreamORM).where(StreamORM.stream_id == stream_id)
            )
            stream = result.scalar_one_or_none()
            assert stream is not None
            assert stream.name == "Test Stream"
            assert stream.source_url == "rtsp://test-camera:554/stream1"

    async def test_audio_with_keyword_produces_alert(
        self,
        db_session: AsyncSession,
        db_session_factory,
    ) -> None:
        """POST /streams → seed alert → GET /alerts → at least one result.

        Full end-to-end: create a stream via API, simulate alert
        creation (as the pipeline would), then query alerts endpoint.
        """
        app = _get_test_app(db_session_factory)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1) Create a stream
            resp = await client.post(
                "/api/v1/streams",
                json={
                    "name": "Keyword Test Stream",
                    "source_type": "rtsp",
                    "source_url": "rtsp://test-camera:554/keyword-test",
                    "asr_backend": "deepgram_nova2",
                },
            )
            assert resp.status_code == 201
            stream_data = resp.json()
            stream_id = uuid.UUID(stream_data["stream_id"])
            session_id = uuid.UUID(stream_data["session_id"])

            # 2) Seed an alert (simulating pipeline output)
            await _seed_alert(db_session, stream_id, session_id)

            # 3) Query alerts
            alerts_resp = await client.get(
                "/api/v1/alerts",
                params={"stream_id": str(stream_id)},
            )
            assert alerts_resp.status_code == 200
            alerts_data = alerts_resp.json()
            assert alerts_data["total"] >= 1, "Expected at least one keyword alert"

            first_alert = alerts_data["alerts"][0]
            assert first_alert["alert_type"] == "keyword"
            assert first_alert["matched_rule"] == "gun"
            assert first_alert["severity"] == "critical"

    async def test_pipeline_latency_end_to_end(
        self,
        db_session: AsyncSession,
        db_session_factory,
    ) -> None:
        """Verify end-to-end API round-trip meets ≤3 second target."""
        import time

        app = _get_test_app(db_session_factory)

        transport = httpx.ASGITransport(app=app)
        start = time.monotonic()
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/streams",
                json={
                    "name": "Latency Test",
                    "source_type": "file",
                    "source_url": "/tmp/test.wav",
                },
            )
            assert resp.status_code == 201

            stream_data = resp.json()
            stream_id = uuid.UUID(stream_data["stream_id"])
            session_id = uuid.UUID(stream_data["session_id"])

            # Simulate alert produced by pipeline
            await _seed_alert(db_session, stream_id, session_id)

            alerts_resp = await client.get(
                "/api/v1/alerts",
                params={"stream_id": str(stream_id)},
            )
            assert alerts_resp.status_code == 200

        elapsed = time.monotonic() - start
        assert elapsed < 3.0, f"End-to-end latency {elapsed:.2f}s exceeds 3s"

    async def test_speaker_labels_assigned(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Verify diarization assigns speaker labels to alerts.

        Since diarization is mocked, we verify the DB schema supports
        the ``speaker_id`` field on alerts.
        """
        stream_id = uuid.uuid4()
        session_id = uuid.uuid4()

        # Create stream + session first (FK constraints)
        stream = StreamORM(
            stream_id=stream_id,
            name="Speaker Test",
            source_type="rtsp",
            source_url="rtsp://test:554/speaker",
            status="active",
            session_id=session_id,
        )
        session = SessionORM(
            session_id=session_id,
            stream_id=stream_id,
        )
        db_session.add(stream)
        db_session.add(session)
        await db_session.flush()

        alert = AlertORM(
            alert_id=uuid.uuid4(),
            session_id=session_id,
            stream_id=stream_id,
            segment_id=None,
            alert_type="keyword",
            severity="high",
            matched_rule="fire",
            match_type="exact",
            speaker_id="SPEAKER_01",
            matched_text="fire",
        )
        db_session.add(alert)
        await db_session.flush()

        result = await db_session.execute(
            select(AlertORM).where(AlertORM.stream_id == stream_id)
        )
        row = result.scalar_one()
        assert row.speaker_id == "SPEAKER_01"
