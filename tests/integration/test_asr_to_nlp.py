"""Integration tests: ASR -> NLP pipeline.

Verifies that transcript segments emitted by the ASR service are correctly
received by the NLP service for keyword detection, sentiment analysis,
intent classification, and PII redaction.
"""

import pytest


@pytest.mark.integration
class TestASRToNLP:
    """Test ASR-to-NLP data flow."""

    async def test_transcript_reaches_nlp(self) -> None:
        """Verify transcript segments from ASR are consumed by NLP."""
        ...

    async def test_keyword_detection_on_transcript(self) -> None:
        """Verify NLP detects keywords in transcript segments."""
        ...

    async def test_pii_redaction_applied(self) -> None:
        """Verify PII is redacted before downstream propagation."""
        ...
