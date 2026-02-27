"""
Transcript data model for VoxSentinel.

Defines the Pydantic models for TranscriptToken (real-time ASR output)
and TranscriptSegment (stored finalized transcript with speaker, sentiment,
PII redaction status, and audit hash).
"""

from __future__ import annotations

from pydantic import BaseModel
