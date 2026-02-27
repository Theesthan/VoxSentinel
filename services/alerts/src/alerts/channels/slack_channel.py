"""
Slack alert channel for VoxSentinel.

Sends formatted alert messages to configured Slack channels via
incoming webhook or Slack bot API.
"""

from __future__ import annotations

from slack_sdk.webhook.async_client import AsyncWebhookClient
