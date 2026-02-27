"""
Abstract base class for alert channels in VoxSentinel.

Defines the AlertChannel interface that all channel implementations
must follow, ensuring consistent delivery semantics and error handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

from tg_common.models.alert import Alert

logger = structlog.get_logger()


class AlertChannel(ABC):
    """Base class every alert delivery channel must implement.

    Subclasses override :meth:`send` to deliver an alert payload to their
    specific transport (WebSocket, HTTP webhook, Slack, etc.).

    Attributes:
        name: Human-readable channel name used in logs and delivery tracking.
        enabled: Runtime flag — ``False`` disables delivery without removing
                 the channel from the dispatcher's registry.
    """

    name: str = "base"
    enabled: bool = True

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Deliver *alert* to the channel's backend.

        Args:
            alert: Fully-populated Alert Pydantic model.

        Returns:
            ``True`` if delivery succeeded, ``False`` otherwise (the
            dispatcher will queue the alert for retry via Celery).
        """

    async def close(self) -> None:
        """Release any resources held by the channel (override if needed)."""
