"""End-to-end test: Keyword detection triggering a Slack alert.

Verifies the complete flow: audio containing a monitored keyword is
ingested, transcribed, detected by NLP, and an alert is dispatched
to the configured Slack channel.
"""

import pytest


@pytest.mark.e2e
class TestKeywordAlertSlack:
    """E2E: Keyword detection to Slack alert delivery."""

    async def test_keyword_triggers_slack_notification(self) -> None:
        """Verify a keyword in audio triggers a Slack notification."""
        ...

    async def test_alert_contains_context_snippet(self) -> None:
        """Verify the Slack alert includes the surrounding transcript context."""
        ...

    async def test_alert_includes_severity_and_stream_info(self) -> None:
        """Verify alert metadata includes severity level and stream details."""
        ...
