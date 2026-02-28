"""
Central alert routing dispatcher for VoxSentinel.

Receives alert events from NLP/sentiment/compliance pipelines and
routes them to all configured channels based on severity, alert type,
and stream assignment.

Flow
----
1. Subscribe to ``match_events:*`` and ``sentiment_events:*`` Redis
   pub/sub channels.
2. For each incoming event: check dedup → check throttle → build
   ``Alert`` Pydantic object → dispatch to all enabled channels →
   write to PostgreSQL alerts table.
3. Channels that return ``False`` on ``send()`` are queued for retry
   via Celery (see :mod:`alerts.retry`).
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from tg_common.models.alert import (
    Alert,
    AlertType,
    KeywordMatchEvent,
    MatchType,
    SentimentEvent,
    Severity,
)

from .channels.base import AlertChannel
from .throttle import AlertThrottle

logger = structlog.get_logger()


def _keyword_event_to_alert(event: KeywordMatchEvent) -> Alert:
    """Convert a :class:`KeywordMatchEvent` to an :class:`Alert`."""
    return Alert(
        session_id=event.session_id,
        stream_id=event.stream_id,
        alert_type=AlertType.KEYWORD,
        severity=Severity.HIGH,
        matched_rule=event.keyword,
        match_type=event.match_type,
        similarity_score=event.similarity_score,
        matched_text=event.matched_text,
        surrounding_context=event.surrounding_context,
        speaker_id=event.speaker_id,
    )


def _sentiment_event_to_alert(event: SentimentEvent) -> Alert:
    """Convert a :class:`SentimentEvent` to an :class:`Alert`."""
    return Alert(
        session_id=event.session_id,
        stream_id=event.stream_id,
        alert_type=AlertType.SENTIMENT,
        severity=Severity.MEDIUM,
        matched_rule=event.sentiment_label,
        match_type=MatchType.SENTIMENT_THRESHOLD,
        sentiment_scores={
            event.sentiment_label: event.sentiment_score,
        },
        speaker_id=event.speaker_id,
    )


class AlertDispatcher:
    """Orchestrates dedup, throttle, channel fan-out, and persistence.

    Args:
        throttle: :class:`AlertThrottle` instance.
        channels: List of enabled :class:`AlertChannel` implementations.
        alert_writer: Optional async callable that persists an Alert
                      (signature ``async (Alert) -> None``).  If *None*,
                      persistence is skipped (useful in tests).
        retry_enqueue: Optional callable to enqueue a failed delivery for
                       retry via Celery (``(Alert, str) -> None``).
    """

    def __init__(
        self,
        throttle: AlertThrottle,
        channels: list[AlertChannel],
        *,
        alert_writer: Any | None = None,
        retry_enqueue: Any | None = None,
    ) -> None:
        self.throttle = throttle
        self.channels = channels
        self._alert_writer = alert_writer
        self._retry_enqueue = retry_enqueue

    # ── event parsing ──

    @staticmethod
    def parse_event(channel_name: str, raw: str) -> Alert | None:
        """Deserialise a raw Redis pub/sub message into an :class:`Alert`.

        Args:
            channel_name: The Redis pub/sub channel the message arrived on.
            raw: JSON-serialised event string.

        Returns:
            An ``Alert`` or ``None`` if the message cannot be parsed.
        """
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("event_parse_failed", channel=channel_name)
            return None

        try:
            if channel_name.startswith("match_events"):
                event = KeywordMatchEvent(**data)
                return _keyword_event_to_alert(event)
            if channel_name.startswith("sentiment_events"):
                event_s = SentimentEvent(**data)
                return _sentiment_event_to_alert(event_s)
        except Exception as exc:  # noqa: BLE001
            logger.warning("event_model_error", channel=channel_name, error=str(exc))
        return None

    # ── dispatch pipeline ──

    async def dispatch(self, alert: Alert) -> bool:
        """Run the full dispatch pipeline for *alert*.

        Steps:
            1. Dedup check — skip if duplicate.
            2. Throttle check — skip if throttled.
            3. Fan-out to all enabled channels.
            4. Record alert in rate-limit window.
            5. Persist alert.

        Returns:
            ``True`` if the alert was dispatched to at least one channel.
        """
        stream_id = str(alert.stream_id)
        keyword = alert.matched_rule or alert.alert_type.value
        match_type = alert.match_type.value
        log = logger.bind(stream_id=stream_id, alert_id=str(alert.alert_id))

        # 1. Dedup
        if await self.throttle.is_duplicate(stream_id, keyword, match_type):
            log.info("alert_suppressed_dedup")
            alert.deduplicated = True
            return False

        # 2. Throttle
        if await self.throttle.is_throttled(stream_id):
            log.info("alert_suppressed_throttle")
            return False

        # 3. Fan-out
        delivered_to: list[str] = []
        delivery_status: dict[str, str] = {}

        for ch in self.channels:
            if not ch.enabled:
                continue
            try:
                ok = await ch.send(alert)
                if ok:
                    delivered_to.append(ch.name)
                    delivery_status[ch.name] = "delivered"
                else:
                    delivery_status[ch.name] = "failed"
                    if self._retry_enqueue is not None:
                        self._retry_enqueue(alert, ch.name)
            except Exception as exc:  # noqa: BLE001
                log.error("channel_send_error", channel=ch.name, error=str(exc))
                delivery_status[ch.name] = "error"
                if self._retry_enqueue is not None:
                    self._retry_enqueue(alert, ch.name)

        alert.delivered_to = delivered_to
        alert.delivery_status = delivery_status

        # 4. Record for rate-limit
        await self.throttle.record(stream_id)

        # 5. Persist
        if self._alert_writer is not None:
            try:
                await self._alert_writer(alert)
            except Exception as exc:  # noqa: BLE001
                log.error("alert_persist_failed", error=str(exc))

        log.info(
            "alert_dispatched",
            delivered_to=delivered_to,
            delivery_status=delivery_status,
        )
        return len(delivered_to) > 0

    # ── pub/sub listener ──

    async def listen(self, pubsub: Any) -> None:
        """Consume messages from a Redis ``PubSub`` and dispatch alerts.

        This is the main event loop — runs forever (or until the pubsub
        connection is closed / an ``asyncio.CancelledError`` is raised).

        Args:
            pubsub: An ``aioredis.client.PubSub`` already subscribed to
                    the desired channels.
        """
        log = logger.bind(component="dispatcher_listener")
        log.info("dispatcher_listening")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            channel_name: str = message.get("channel", "")
            raw: str = message.get("data", "")
            alert = self.parse_event(channel_name, raw)
            if alert is not None:
                await self.dispatch(alert)
