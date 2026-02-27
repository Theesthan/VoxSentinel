"""
Tests for the PII redaction module.

Validates Presidio entity detection and anonymization, placeholder
formatting, and redaction accuracy for various PII types.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nlp.pii_redactor import ENTITY_PLACEHOLDER_MAP, PiiRedactor, RedactionResult


class TestPiiRedactor:
    """Tests for PiiRedactor.redact()."""

    @pytest.fixture(autouse=True)
    def _setup_redactor(self) -> None:
        self.redactor = PiiRedactor()
        # Mock analyzer
        self.mock_analyzer = MagicMock()
        # Mock anonymizer
        self.mock_anonymizer = MagicMock()
        self.redactor._analyzer = self.mock_analyzer
        self.redactor._anonymizer = self.mock_anonymizer

    def _make_recognizer_result(
        self, entity_type: str, start: int, end: int, score: float = 0.95
    ) -> MagicMock:
        result = MagicMock()
        result.entity_type = entity_type
        result.start = start
        result.end = end
        result.score = score
        return result

    async def test_phone_number_redacted(self) -> None:
        text = "Call me at 555-123-4567"
        phone_result = self._make_recognizer_result("PHONE_NUMBER", 11, 23)
        self.mock_analyzer.analyze.return_value = [phone_result]

        anon_result = MagicMock()
        anon_result.text = "Call me at [PHONE]"
        self.mock_anonymizer.anonymize.return_value = anon_result

        result = await self.redactor.redact(text)
        assert result.redacted_text == "Call me at [PHONE]"
        assert "PHONE_NUMBER" in result.entities_found

    async def test_person_name_redacted(self) -> None:
        text = "My name is John Smith"
        person_result = self._make_recognizer_result("PERSON", 11, 21)
        self.mock_analyzer.analyze.return_value = [person_result]

        anon_result = MagicMock()
        anon_result.text = "My name is [PERSON]"
        self.mock_anonymizer.anonymize.return_value = anon_result

        result = await self.redactor.redact(text)
        assert result.redacted_text == "My name is [PERSON]"
        assert "PERSON" in result.entities_found

    async def test_email_redacted(self) -> None:
        text = "Email me at john@example.com"
        email_result = self._make_recognizer_result("EMAIL_ADDRESS", 12, 28)
        self.mock_analyzer.analyze.return_value = [email_result]

        anon_result = MagicMock()
        anon_result.text = "Email me at [EMAIL]"
        self.mock_anonymizer.anonymize.return_value = anon_result

        result = await self.redactor.redact(text)
        assert result.redacted_text == "Email me at [EMAIL]"
        assert "EMAIL_ADDRESS" in result.entities_found

    async def test_no_pii_returns_original(self) -> None:
        text = "The weather is nice today"
        self.mock_analyzer.analyze.return_value = []

        result = await self.redactor.redact(text)
        assert result.redacted_text == text
        assert result.entities_found == []

    async def test_empty_text_returns_empty(self) -> None:
        result = await self.redactor.redact("")
        assert result.redacted_text == ""
        assert result.entities_found == []

    async def test_whitespace_only_returns_as_is(self) -> None:
        result = await self.redactor.redact("   ")
        assert result.redacted_text == "   "
        assert result.entities_found == []

    async def test_multiple_entities(self) -> None:
        text = "John Smith called 555-1234"
        person_result = self._make_recognizer_result("PERSON", 0, 10)
        phone_result = self._make_recognizer_result("PHONE_NUMBER", 18, 26)
        self.mock_analyzer.analyze.return_value = [person_result, phone_result]

        anon_result = MagicMock()
        anon_result.text = "[PERSON] called [PHONE]"
        self.mock_anonymizer.anonymize.return_value = anon_result

        result = await self.redactor.redact(text)
        assert "[PERSON]" in result.redacted_text
        assert "[PHONE]" in result.redacted_text
        assert "PERSON" in result.entities_found
        assert "PHONE_NUMBER" in result.entities_found


class TestPiiReadiness:
    """Tests for PII redactor readiness."""

    def test_not_ready_before_load(self) -> None:
        redactor = PiiRedactor()
        assert redactor.is_ready is False

    def test_ready_after_mock_set(self) -> None:
        redactor = PiiRedactor()
        redactor._analyzer = MagicMock()
        redactor._anonymizer = MagicMock()
        assert redactor.is_ready is True


class TestEntityPlaceholderMap:
    """Tests for the placeholder mapping."""

    def test_phone_placeholder(self) -> None:
        assert ENTITY_PLACEHOLDER_MAP["PHONE_NUMBER"] == "[PHONE]"

    def test_person_placeholder(self) -> None:
        assert ENTITY_PLACEHOLDER_MAP["PERSON"] == "[PERSON]"

    def test_email_placeholder(self) -> None:
        assert ENTITY_PLACEHOLDER_MAP["EMAIL_ADDRESS"] == "[EMAIL]"

    def test_address_placeholder(self) -> None:
        assert ENTITY_PLACEHOLDER_MAP["LOCATION"] == "[ADDRESS]"

    def test_ssn_placeholder(self) -> None:
        assert ENTITY_PLACEHOLDER_MAP["US_SSN"] == "[SSN]"

