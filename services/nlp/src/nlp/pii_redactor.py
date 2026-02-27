"""
PII redaction module for VoxSentinel.

Uses Microsoft Presidio with spaCy and GLiNER recognizers to detect
and redact personally identifiable information from transcript text,
replacing entities with typed placeholders (e.g., [PERSON], [PHONE]).
"""

from __future__ import annotations

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
