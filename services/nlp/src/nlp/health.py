"""
Health check endpoint for VoxSentinel NLP service.

Exposes a /health endpoint returning service status, model readiness,
and keyword rule count.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from nlp.keyword_engine import KeywordEngine
from nlp.pii_redactor import PiiRedactor
from nlp.sentiment_engine import SentimentEngine

router = APIRouter()

# Module-level references set by main.py at startup
_keyword_engine: KeywordEngine | None = None
_sentiment_engine: SentimentEngine | None = None
_pii_redactor: PiiRedactor | None = None


def configure(
    keyword_engine: KeywordEngine,
    sentiment_engine: SentimentEngine,
    pii_redactor: PiiRedactor,
) -> None:
    """Inject service references for the health endpoint."""
    global _keyword_engine, _sentiment_engine, _pii_redactor
    _keyword_engine = keyword_engine
    _sentiment_engine = sentiment_engine
    _pii_redactor = pii_redactor


@router.get("/health")
async def health() -> JSONResponse:
    """Return NLP service health status."""
    keyword_ready = _keyword_engine is not None and _keyword_engine.aho_index.is_ready
    sentiment_ready = _sentiment_engine is not None and _sentiment_engine.is_ready
    pii_ready = _pii_redactor is not None and _pii_redactor.is_ready

    all_ready = keyword_ready or True  # keywords may have 0 rules initially
    status_code = 200 if (sentiment_ready and pii_ready) else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "service": "nlp",
            "status": "healthy" if status_code == 200 else "degraded",
            "keyword_engine_ready": keyword_ready,
            "keyword_pattern_count": (
                _keyword_engine.aho_index.pattern_count if _keyword_engine else 0
            ),
            "sentiment_engine_ready": sentiment_ready,
            "pii_redactor_ready": pii_ready,
        },
    )
