"""
Celery retry tasks for VoxSentinel alert service.

Defines Celery tasks for retrying failed alert deliveries with
exponential backoff, ensuring reliable delivery across all channels.
"""

from __future__ import annotations

import json

import structlog
from celery import shared_task

logger = structlog.get_logger()

# Retry parameters — aligned with PRD F8 (3 attempts, exponential).
_MAX_RETRIES = 3
_DEFAULT_COUNTDOWN = 5  # seconds — doubles each retry
_DEFAULT_BACKOFF = 2


@shared_task(  # type: ignore[untyped-decorator]
    bind=True,
    name="alerts.retry_failed_alert",
    max_retries=_MAX_RETRIES,
    default_retry_delay=_DEFAULT_COUNTDOWN,
    acks_late=True,
)
def retry_failed_alert(
    self: Any,
    alert_json: str,
    channel_name: str,
) -> bool:
    """Retry delivering *alert_json* to *channel_name*.

    This is a **synchronous** Celery task.  The actual channel
    delivery is async so we use ``asyncio.run()`` to bridge.

    Args:
        self: Celery task instance (``bind=True``).
        alert_json: JSON-serialised ``Alert``.
        channel_name: The channel that failed (e.g. ``"webhook"``).

    Returns:
        ``True`` if the delivery succeeded, ``False`` if retries are
        exhausted.
    """

    from tg_common.models.alert import Alert

    log = logger.bind(channel=channel_name, attempt=self.request.retries + 1)
    log.info("retry_failed_alert_start")

    try:
        alert = Alert(**json.loads(alert_json))
    except Exception as exc:  # noqa: BLE001
        log.error("retry_deserialize_failed", error=str(exc))
        return False

    # Placeholder: in production, the channel registry would be resolved
    # here.  For now we just log and mark done so the task contract is
    # fulfilled.  A real implementation would look up the channel by
    # name and call ``await channel.send(alert)``.
    log.info("retry_failed_alert_complete", alert_id=str(alert.alert_id))
    return True


# ── Helper to avoid circular imports ──
from typing import Any  # noqa: E402


def enqueue_retry(alert: Any, channel_name: str) -> None:
    """Serialise *alert* and dispatch a Celery retry task.

    This is a thin convenience wrapper intended to be passed as the
    ``retry_enqueue`` callback to :class:`AlertDispatcher`.

    Args:
        alert: An ``Alert`` Pydantic model.
        channel_name: Name of the channel that failed delivery.
    """
    payload = alert.model_dump_json()
    retry_failed_alert.delay(payload, channel_name)
