"""
Slack alert channel for VoxSentinel.

Sends formatted alert messages to configured Slack channels via
incoming webhook or Slack bot API.
"""

from __future__ import annotations

from datetime import timezone

import structlog
from slack_sdk.webhook.async_client import AsyncWebhookClient

from tg_common.models.alert import Alert

from .base import AlertChannel

logger = structlog.get_logger()


def _format_slack_blocks(alert: Alert) -> list[dict]:
    """Build Slack Block Kit blocks for *alert*.

    Format:
        *keyword*  |  stream_name  |  speaker  |  timestamp
        > surrounding context snippet …
    """
    ts = alert.created_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S UTC")

    header = (
        f"*{alert.matched_rule or alert.alert_type.value}*  |  "
        f"stream `{alert.stream_id}`  |  "
        f"speaker `{alert.speaker_id or 'unknown'}`  |  "
        f"`{ts_str}`"
    )
    context_snippet = alert.surrounding_context[:300] if alert.surrounding_context else "(no context)"
    blocks: list[dict] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"> {context_snippet}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"severity: *{alert.severity.value}*  |  "
                        f"match: {alert.match_type.value}  |  "
                        f"alert_id: `{alert.alert_id}`"
                    ),
                },
            ],
        },
    ]
    return blocks


class SlackChannel(AlertChannel):
    """Send formatted Slack messages via incoming webhook.

    Args:
        webhook_url: Slack incoming-webhook URL.
    """

    name: str = "slack"

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url
        self._client = AsyncWebhookClient(url=webhook_url)

    async def send(self, alert: Alert) -> bool:
        """Deliver *alert* to Slack.

        Returns:
            ``True`` on success (2xx), ``False`` otherwise.
        """
        blocks = _format_slack_blocks(alert)
        fallback_text = (
            f"Alert: {alert.matched_rule or alert.alert_type.value} "
            f"on stream {alert.stream_id}"
        )
        log = logger.bind(alert_id=str(alert.alert_id), channel="slack")
        try:
            response = await self._client.send(text=fallback_text, blocks=blocks)
            if response.status_code == 200:
                log.info("slack_delivered")
                return True
            log.warning("slack_non_200", status=response.status_code, body=response.body)
            return False
        except Exception as exc:  # noqa: BLE001
            log.error("slack_delivery_failed", error=str(exc))
            return False

    async def close(self) -> None:
        """No persistent resources to clean up."""
