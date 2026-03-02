"""
Storage service entry point for VoxSentinel.

Initializes database connections, Elasticsearch client, subscribes to
transcript and alert event streams, and exposes health and metrics
endpoints.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app

from storage.health import router as health_router
from storage.transcript_writer import TranscriptWriter
from storage.alert_writer import AlertWriter
from storage.es_indexer import ESIndexer
from storage.audit_hasher import AuditHasher

logger = structlog.get_logger(__name__)

# ── Prometheus metrics ──
storage_writes_total = Counter(
    "storage_writes_total",
    "Total records written to PostgreSQL",
    ["table"],
)
storage_es_indexes_total = Counter(
    "storage_es_indexes_total",
    "Total documents indexed in Elasticsearch",
    ["index"],
)
storage_write_duration_seconds = Histogram(
    "storage_write_duration_seconds",
    "Time spent writing a record to storage",
    ["backend"],
)

# ── Background tasks ──
_transcript_task: asyncio.Task | None = None
_alert_task: asyncio.Task | None = None
_audit_task: asyncio.Task | None = None


async def _consume_transcripts(
    redis: Any,
    writer: TranscriptWriter,
) -> None:
    """Subscribe to redacted_tokens:* and persist transcript segments."""
    pubsub = redis.pubsub()
    await pubsub.psubscribe("redacted_tokens:*")
    logger.info("storage_transcript_consumer_started")
    try:
        async for message in pubsub.listen():
            if message["type"] not in ("pmessage", "message"):
                continue
            raw = message.get("data", "")
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                await writer.handle_message(raw)
                storage_writes_total.labels(table="transcript_segments").inc()
            except Exception:
                logger.exception("transcript_consume_error")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.punsubscribe("redacted_tokens:*")
        await pubsub.close()


async def _consume_alerts(
    redis: Any,
    writer: AlertWriter,
) -> None:
    """Subscribe to dispatched_alerts:* and persist alert records."""
    pubsub = redis.pubsub()
    await pubsub.psubscribe("dispatched_alerts:*")
    logger.info("storage_alert_consumer_started")
    try:
        async for message in pubsub.listen():
            if message["type"] not in ("pmessage", "message"):
                continue
            raw = message.get("data", "")
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                await writer.handle_message(raw)
                storage_writes_total.labels(table="alerts").inc()
            except Exception:
                logger.exception("alert_consume_error")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.punsubscribe("dispatched_alerts:*")
        await pubsub.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup / shutdown of background workers."""
    global _transcript_task, _alert_task, _audit_task

    logger.info("storage_service_starting")

    # ── Redis connection ──
    import redis.asyncio as aioredis

    redis_url = os.getenv("TG_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    redis = aioredis.from_url(redis_url, decode_responses=True)
    app.state.redis = redis

    # ── Database session factory ──
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    db_url = os.getenv(
        "TG_DB_URI",
        os.getenv("DATABASE_URL", "postgresql+asyncpg://voxsentinel:changeme@localhost:5432/voxsentinel"),
    )
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.db_session_factory = session_factory

    # ── Elasticsearch client ──
    es_indexer: ESIndexer | None = None
    try:
        from elasticsearch import AsyncElasticsearch

        es_url = os.getenv("TG_ES_URL", os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
        es_client = AsyncElasticsearch(es_url)
        es_indexer = ESIndexer(es_client)
        await es_indexer.ensure_index()
        app.state.es_client = es_client
    except Exception:
        logger.warning("elasticsearch_unavailable")
        app.state.es_client = None

    # ── Wire up writers ──
    transcript_writer = TranscriptWriter(session_factory, es_indexer=es_indexer)
    alert_writer = AlertWriter(session_factory)
    audit_hasher = AuditHasher(session_factory)

    # ── Start background consumers ──
    _transcript_task = asyncio.create_task(_consume_transcripts(redis, transcript_writer))
    _alert_task = asyncio.create_task(_consume_alerts(redis, alert_writer))
    _audit_task = asyncio.create_task(audit_hasher.run_periodic())

    logger.info("storage_service_ready")
    yield

    # ── Shutdown ──
    logger.info("storage_service_stopping")
    for task in (_transcript_task, _alert_task, _audit_task):
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    if es_indexer:
        try:
            await es_indexer.close()
        except Exception:
            pass

    await engine.dispose()
    await redis.close()
    logger.info("storage_service_stopped")


def create_app() -> FastAPI:
    """Build the FastAPI application with health routes."""
    app = FastAPI(title="VoxSentinel Storage", lifespan=lifespan)
    app.include_router(health_router)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8007,
        log_level="info",
    )
