"""
Alert writer for VoxSentinel storage service.

Persists alert records to PostgreSQL with foreign key references
to triggering transcript segments and sessions.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tg_common.db.orm_models import AlertORM
from tg_common.models.alert import Alert

logger = structlog.get_logger(__name__)


class AlertWriter:
    """Persists dispatched alerts to PostgreSQL.

    Parameters
    ----------
    session_factory:
        Async callable returning an ``AsyncSession``.
    """

    def __init__(self, session_factory: Callable[..., Any]) -> None:
        self._session_factory = session_factory

    async def write_alert(
        self,
        alert: Alert,
        *,
        db_session: AsyncSession | None = None,
    ) -> AlertORM:
        """Persist a single alert to the database.

        If *db_session* is ``None`` the writer creates one via its factory.
        """
        orm_obj = AlertORM(
            alert_id=alert.alert_id,
            session_id=alert.session_id,
            stream_id=alert.stream_id,
            segment_id=alert.segment_id,
            alert_type=alert.alert_type.value,
            severity=alert.severity.value,
            matched_rule=alert.matched_rule,
            match_type=alert.match_type.value,
            similarity_score=alert.similarity_score,
            matched_text=alert.matched_text,
            surrounding_context=alert.surrounding_context,
            speaker_id=alert.speaker_id,
            channel=alert.channel,
            sentiment_scores=alert.sentiment_scores,
            asr_backend_used=alert.asr_backend_used,
            delivered_to=alert.delivered_to,
            delivery_status=alert.delivery_status,
            deduplicated=alert.deduplicated,
        )

        own_session = db_session is None
        session: AsyncSession = db_session or self._session_factory()
        try:
            session.add(orm_obj)
            await session.commit()
            logger.info(
                "alert_written",
                alert_id=str(alert.alert_id),
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
            )
        except Exception:
            await session.rollback()
            logger.exception("alert_write_failed", alert_id=str(alert.alert_id))
            raise
        finally:
            if own_session:
                await session.close()

        return orm_obj

    async def handle_message(self, raw: str | bytes) -> AlertORM | None:
        """Parse a JSON message from Redis into an ``Alert`` and persist.

        Returns ``None`` when the payload cannot be parsed.
        """
        try:
            data = json.loads(raw)
            alert = Alert(**data)
        except Exception:
            logger.exception("alert_parse_failed")
            return None
        return await self.write_alert(alert)
