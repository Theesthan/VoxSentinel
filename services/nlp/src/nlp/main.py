"""
NLP service entry point for VoxSentinel.

Initializes the NLP service, loads keyword rules, ML models, and
PII recognizers, subscribes to transcript token streams, and
exposes health and metrics endpoints.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI

from tg_common.config import get_settings
from tg_common.messaging.redis_client import RedisClient
from tg_common.models import TranscriptToken

from nlp import health
from nlp.keyword_engine import KeywordEngine
from nlp.pii_redactor import PiiRedactor
from nlp.rule_loader import RuleLoader
from nlp.sentiment_engine import SentimentEngine

logger = structlog.get_logger()

# ── service singletons (set during lifespan) ──
_keyword_engine: KeywordEngine | None = None
_sentiment_engine: SentimentEngine | None = None
_pii_redactor: PiiRedactor | None = None
_rule_loader: RuleLoader | None = None
_redis: RedisClient | None = None


async def _process_token(
    token: TranscriptToken,
    stream_id: str,
    session_id: str,
    redis: RedisClient,
    keyword_engine: KeywordEngine,
    sentiment_engine: SentimentEngine,
    pii_redactor: PiiRedactor,
) -> None:
    """Run keyword, sentiment, and PII pipelines in parallel on a final token."""
    if not token.is_final or not token.text.strip():
        return

    # Compute stream-relative offsets in seconds
    start_s = token.start_time.timestamp()
    end_s = token.end_time.timestamp()

    from uuid import UUID

    sid = UUID(stream_id)
    sess_id = UUID(session_id)

    # Launch all three pipelines concurrently
    keyword_task = asyncio.create_task(
        asyncio.to_thread(
            keyword_engine.detect,
            token.text,
            start_s,
            end_s,
            sid,
            sess_id,
        )
    )
    sentiment_task = asyncio.create_task(
        sentiment_engine.classify(
            token.text,
            end_s,
            sid,
            sess_id,
        )
    )
    pii_task = asyncio.create_task(
        pii_redactor.redact(token.text)
    )

    # Await results
    keyword_events, (sentiment_result, escalation_event), pii_result = await asyncio.gather(
        keyword_task, sentiment_task, pii_task
    )

    # Publish keyword match events
    for evt in keyword_events:
        await redis.publish(
            f"match_events:{stream_id}",
            evt.model_dump(mode="json"),
        )

    # Publish sentiment escalation events
    if escalation_event is not None:
        await redis.publish(
            f"sentiment_events:{stream_id}",
            escalation_event.model_dump(mode="json"),
        )

    # Publish redacted text for downstream storage
    await redis.xadd(
        f"redacted_tokens:{stream_id}",
        {
            "text_original": token.text,
            "text_redacted": pii_result.redacted_text,
            "entities_found": json.dumps(pii_result.entities_found),
            "sentiment_label": sentiment_result.label.lower(),
            "sentiment_score": str(sentiment_result.score),
            "start_time": token.start_time.isoformat(),
            "end_time": token.end_time.isoformat(),
        },
    )


async def _consume_stream(
    stream_key: str,
    stream_id: str,
    session_id: str,
    redis: RedisClient,
    keyword_engine: KeywordEngine,
    sentiment_engine: SentimentEngine,
    pii_redactor: PiiRedactor,
) -> None:
    """Consume transcript tokens from a Redis stream and process them."""
    last_id = "0"
    while True:
        try:
            entries = await redis.xread({stream_key: last_id}, count=10, block=1000)
            for _stream, messages in entries:
                for msg_id, fields in messages:
                    last_id = msg_id
                    try:
                        token_data = json.loads(fields.get("data", "{}"))
                        token = TranscriptToken.model_validate(token_data)
                        await _process_token(
                            token,
                            stream_id,
                            session_id,
                            redis,
                            keyword_engine,
                            sentiment_engine,
                            pii_redactor,
                        )
                    except Exception:
                        logger.exception(
                            "token_processing_error",
                            stream_id=stream_id,
                            msg_id=msg_id,
                        )
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("stream_consume_error", stream_key=stream_key)
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: initialise engines and Redis, then clean up."""
    global _keyword_engine, _sentiment_engine, _pii_redactor, _rule_loader, _redis

    logger.info("nlp_service_starting")

    # Init engines
    _keyword_engine = KeywordEngine()
    _sentiment_engine = SentimentEngine()
    _pii_redactor = PiiRedactor()

    # Load ML models
    _sentiment_engine.load_model()
    _pii_redactor.load()

    # Connect Redis
    _redis = RedisClient()
    await _redis.connect()

    # Start rule loader
    _rule_loader = RuleLoader(_keyword_engine)
    await _rule_loader.start()

    # Configure health endpoint
    health.configure(_keyword_engine, _sentiment_engine, _pii_redactor)

    logger.info("nlp_service_ready")
    yield

    # Shutdown
    logger.info("nlp_service_stopping")
    if _rule_loader:
        await _rule_loader.stop()
    if _redis:
        await _redis.close()
    logger.info("nlp_service_stopped")


app = FastAPI(title="VoxSentinel NLP Service", lifespan=lifespan)
app.include_router(health.router)


if __name__ == "__main__":
    uvicorn.run(
        "nlp.main:app",
        host="0.0.0.0",
        port=8004,
        log_level="info",
    )
