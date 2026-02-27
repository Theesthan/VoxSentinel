"""
PII redaction module for VoxSentinel.

Uses Microsoft Presidio with spaCy and GLiNER recognizers to detect
and redact personally identifiable information from transcript text,
replacing entities with typed placeholders (e.g., [PERSON], [PHONE]).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = structlog.get_logger()

# Mapping from Presidio entity types to our typed placeholders
ENTITY_PLACEHOLDER_MAP: dict[str, str] = {
    "PERSON": "[PERSON]",
    "PHONE_NUMBER": "[PHONE]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "LOCATION": "[ADDRESS]",
    "ADDRESS": "[ADDRESS]",
    "CREDIT_CARD": "[CREDIT_CARD]",
    "US_SSN": "[SSN]",
    "US_BANK_NUMBER": "[ACCOUNT_ID]",
    "IBAN_CODE": "[ACCOUNT_ID]",
    "IP_ADDRESS": "[IP_ADDRESS]",
    # fallback for unknown entity types is handled in code
}

SUPPORTED_ENTITIES = list(ENTITY_PLACEHOLDER_MAP.keys())


@dataclass
class RedactionResult:
    """Output of PII redaction on a text segment.

    Attributes:
        redacted_text: The text with PII replaced by typed placeholders.
        entities_found: List of entity types that were detected.
    """

    redacted_text: str
    entities_found: list[str]


class PiiRedactor:
    """Presidio-based PII detection and anonymisation.

    Loads spaCy NLP engine for Presidio.  Inference is run via
    :func:`asyncio.to_thread` to keep the async event loop responsive.
    """

    def __init__(self) -> None:
        self._analyzer: AnalyzerEngine | None = None
        self._anonymizer: AnonymizerEngine | None = None

    # ── lifecycle ──

    def load(self) -> None:
        """Initialise the Presidio analyser and anonymiser engines."""
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()
        logger.info("pii_redactor_loaded")

    @property
    def is_ready(self) -> bool:
        """Whether engines have been loaded."""
        return self._analyzer is not None and self._anonymizer is not None

    # ── redaction ──

    async def redact(self, text: str, language: str = "en") -> RedactionResult:
        """Detect and redact PII from *text*.

        Args:
            text: The transcript text to scan.
            language: BCP-47 language code for analysis.

        Returns:
            A :class:`RedactionResult` with redacted text and entity types found.
        """
        if not self._analyzer or not self._anonymizer or not text.strip():
            return RedactionResult(redacted_text=text, entities_found=[])

        # Run analysis off the event loop
        results = await asyncio.to_thread(
            self._analyzer.analyze,
            text=text,
            language=language,
            entities=SUPPORTED_ENTITIES,
        )

        if not results:
            return RedactionResult(redacted_text=text, entities_found=[])

        # Build operator config for typed placeholders
        operators: dict[str, OperatorConfig] = {}
        entities_found: list[str] = []
        for r in results:
            placeholder = ENTITY_PLACEHOLDER_MAP.get(r.entity_type, f"[{r.entity_type}]")
            operators[r.entity_type] = OperatorConfig("replace", {"new_value": placeholder})
            if r.entity_type not in entities_found:
                entities_found.append(r.entity_type)

        # Anonymise
        anonymised = await asyncio.to_thread(
            self._anonymizer.anonymize,
            text=text,
            analyzer_results=results,
            operators=operators,
        )

        return RedactionResult(
            redacted_text=anonymised.text,
            entities_found=entities_found,
        )
