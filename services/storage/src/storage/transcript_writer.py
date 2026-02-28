"""
Transcript writer for VoxSentinel storage service.

Writes finalized transcript segments to PostgreSQL/TimescaleDB as
time-series records partitioned by day, handling both redacted and
restricted-access original text storage.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tg_common.db.orm_models import TranscriptSegmentORM
from tg_common.models.transcript import TranscriptSegment

logger = structlog.get_logger(__name__)


def compute_segment_hash(
    segment_id: UUID,
    text_original: str,
    start_time: datetime,
    session_id: UUID,
) -> str:
    """Compute SHA-256 audit hash for a transcript segment.

    The hash covers ``segment_id + text_original + start_time + session_id``
    encoded as UTF-8.
    """
    payload = f"{segment_id}{text_original}{start_time}{session_id}"
    return hashlib.sha256(payload.encode()).hexdigest()


class TranscriptWriter:
    """Persists transcript segments to PostgreSQL.

    Parameters
    ----------
    session_factory:
        Async callable returning an ``AsyncSession``.
    es_indexer:
        Optional Elasticsearch indexer; ``index_segment`` is called after
        each successful DB write.
    """

    def __init__(
        self,
        session_factory: Callable[..., Any],
        es_indexer: Any | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._es_indexer = es_indexer

    async def write_segment(
        self,
        segment: TranscriptSegment,
        *,
        db_session: AsyncSession | None = None,
    ) -> TranscriptSegmentORM:
        """Write a finalised transcript segment to the database.

        If *db_session* is ``None`` the writer creates one via its factory.

        Returns the ORM instance that was persisted.
        """
        seg_hash = compute_segment_hash(
            segment.segment_id,
            segment.text_original or segment.text_redacted,
            segment.start_time,
            segment.session_id,
        )

        word_ts_raw: list[dict[str, Any]] | None = None
        if segment.word_timestamps:
            word_ts_raw = [wt.model_dump() for wt in segment.word_timestamps]

        orm_obj = TranscriptSegmentORM(
            segment_id=segment.segment_id,
            session_id=segment.session_id,
            stream_id=segment.stream_id,
            speaker_id=segment.speaker_id,
            start_time=segment.start_time,
            end_time=segment.end_time,
            start_offset_ms=segment.start_offset_ms,
            end_offset_ms=segment.end_offset_ms,
            text_redacted=segment.text_redacted,
            text_original=segment.text_original,
            word_timestamps=word_ts_raw,
            language=segment.language,
            asr_backend=segment.asr_backend,
            asr_confidence=segment.asr_confidence,
            sentiment_label=segment.sentiment_label,
            sentiment_score=segment.sentiment_score,
            intent_labels=segment.intent_labels or [],
            pii_entities_found=segment.pii_entities_found or [],
            segment_hash=seg_hash,
        )

        own_session = db_session is None
        session: AsyncSession = db_session or self._session_factory()
        try:
            session.add(orm_obj)
            await session.commit()
            logger.info(
                "segment_written",
                segment_id=str(segment.segment_id),
                stream_id=str(segment.stream_id),
            )
        except Exception:
            await session.rollback()
            logger.exception("segment_write_failed", segment_id=str(segment.segment_id))
            raise
        finally:
            if own_session:
                await session.close()

        # Index in Elasticsearch after successful DB commit.
        if self._es_indexer is not None:
            try:
                await self._es_indexer.index_segment(segment, seg_hash)
            except Exception:
                logger.exception(
                    "es_index_failed",
                    segment_id=str(segment.segment_id),
                )

        return orm_obj

    async def handle_message(self, raw: str | bytes) -> TranscriptSegmentORM | None:
        """Parse a JSON message from Redis into a segment and persist it.

        Returns ``None`` when the message cannot be parsed.
        """
        try:
            data = json.loads(raw)
            segment = TranscriptSegment(**data)
        except Exception:
            logger.exception("transcript_parse_failed")
            return None
        return await self.write_segment(segment)
