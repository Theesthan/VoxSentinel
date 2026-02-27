"""
Tests for the Slack alert channel.

Validates Slack message formatting, webhook delivery, and bot API
integration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tg_common.models.alert import Alert, AlertType, MatchType, Severity
from alerts.channels.slack_channel import SlackChannel, _format_slack_blocks


_TEST_WEBHOOK_URL = "https://hooks.slack.com/services/T00/B00/xxx"


# ── formatting ──


class TestSlackFormatting:
    """Tests for Slack Block Kit message formatting."""

    def test_format_includes_keyword_in_bold(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        header = blocks[0]["text"]["text"]
        assert "*gun*" in header

    def test_format_includes_stream_id(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        header = blocks[0]["text"]["text"]
        assert str(sample_alert.stream_id) in header

    def test_format_includes_speaker(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        header = blocks[0]["text"]["text"]
        assert "SPEAKER_01" in header

    def test_format_includes_timestamp(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        header = blocks[0]["text"]["text"]
        assert "UTC" in header

    def test_format_includes_context_snippet(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        context_block = blocks[1]["text"]["text"]
        assert "gun near the entrance" in context_block

    def test_format_truncates_long_context(self, sample_alert) -> None:
        sample_alert.surrounding_context = "x" * 500
        blocks = _format_slack_blocks(sample_alert)
        context_block = blocks[1]["text"]["text"]
        # Max 300 chars + "> " prefix
        assert len(context_block) <= 310

    def test_format_handles_missing_context(self, stream_id, session_id) -> None:
        alert = Alert(
            session_id=session_id,
            stream_id=stream_id,
            alert_type=AlertType.KEYWORD,
            severity=Severity.HIGH,
            matched_rule="bomb",
            match_type=MatchType.EXACT,
            surrounding_context="",
        )
        blocks = _format_slack_blocks(alert)
        assert "(no context)" in blocks[1]["text"]["text"]

    def test_format_severity_in_context_element(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        ctx = blocks[2]["elements"][0]["text"]
        assert "high" in ctx

    def test_format_match_type_in_context_element(self, sample_alert) -> None:
        blocks = _format_slack_blocks(sample_alert)
        ctx = blocks[2]["elements"][0]["text"]
        assert "exact" in ctx

    def test_format_uses_alert_type_when_no_keyword(self, stream_id, session_id) -> None:
        alert = Alert(
            session_id=session_id,
            stream_id=stream_id,
            alert_type=AlertType.SENTIMENT,
            severity=Severity.MEDIUM,
            matched_rule="",
            match_type=MatchType.SENTIMENT_THRESHOLD,
        )
        blocks = _format_slack_blocks(alert)
        header = blocks[0]["text"]["text"]
        assert "*sentiment*" in header

    def test_format_unknown_speaker(self, stream_id, session_id) -> None:
        alert = Alert(
            session_id=session_id,
            stream_id=stream_id,
            alert_type=AlertType.KEYWORD,
            severity=Severity.LOW,
            matched_rule="test",
            match_type=MatchType.EXACT,
            speaker_id=None,
        )
        blocks = _format_slack_blocks(alert)
        header = blocks[0]["text"]["text"]
        assert "unknown" in header


# ── send ──


class TestSlackSend:
    """Tests for Slack webhook delivery."""

    async def test_send_returns_true_on_200(self, sample_alert) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        ch._client.send = AsyncMock(return_value=mock_resp)

        result = await ch.send(sample_alert)
        assert result is True

    async def test_send_returns_false_on_non_200(self, sample_alert) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.body = "invalid_token"
        ch._client.send = AsyncMock(return_value=mock_resp)

        result = await ch.send(sample_alert)
        assert result is False

    async def test_send_returns_false_on_exception(self, sample_alert) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        ch._client.send = AsyncMock(side_effect=RuntimeError("network"))

        result = await ch.send(sample_alert)
        assert result is False

    async def test_send_passes_blocks_to_client(self, sample_alert) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        ch._client.send = AsyncMock(return_value=mock_resp)

        await ch.send(sample_alert)
        call_kwargs = ch._client.send.call_args.kwargs
        assert "blocks" in call_kwargs
        assert isinstance(call_kwargs["blocks"], list)

    async def test_send_passes_fallback_text(self, sample_alert) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        ch._client.send = AsyncMock(return_value=mock_resp)

        await ch.send(sample_alert)
        call_kwargs = ch._client.send.call_args.kwargs
        assert "gun" in call_kwargs["text"]


# ── metadata ──


class TestSlackMeta:
    """Tests for channel metadata."""

    def test_channel_name(self) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        assert ch.name == "slack"

    async def test_close_does_not_raise(self) -> None:
        ch = SlackChannel(webhook_url=_TEST_WEBHOOK_URL)
        await ch.close()

