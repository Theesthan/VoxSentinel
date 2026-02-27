"""Integration tests: NLP -> Alerts pipeline.

Verifies that NLP match events (keyword hits, sentiment spikes, intent flags)
are correctly dispatched to the Alert service and throttled according to rules.
"""

import pytest


@pytest.mark.integration
class TestNLPToAlerts:
    """Test NLP-to-Alerts data flow."""

    async def test_keyword_match_triggers_alert(self) -> None:
        """Verify a keyword match event triggers an alert dispatch."""
        ...

    async def test_sentiment_spike_triggers_alert(self) -> None:
        """Verify a negative sentiment spike triggers an alert."""
        ...

    async def test_alert_throttling_prevents_duplicates(self) -> None:
        """Verify alert throttle prevents rapid-fire duplicate alerts."""
        ...
