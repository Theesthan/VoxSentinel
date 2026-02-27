"""
Shared Pydantic data models for VoxSentinel.

This package contains all cross-service data models including
streams, sessions, transcripts, alerts, keyword rules, and audit records.
"""

from tg_common.models.alert import (
    Alert,
    AlertType,
    KeywordMatchEvent,
    MatchType,
    SentimentEvent,
    Severity,
)
from tg_common.models.audit import AuditAnchor
from tg_common.models.keyword_rule import (
    AlertChannelConfig,
    ChannelType,
    KeywordRule,
    RuleMatchType,
)
from tg_common.models.stream import Session, SourceType, Stream, StreamStatus
from tg_common.models.transcript import (
    TranscriptSegment,
    TranscriptToken,
    WordTimestamp,
)

__all__ = [
    "Alert",
    "AlertChannelConfig",
    "AlertType",
    "AuditAnchor",
    "ChannelType",
    "KeywordMatchEvent",
    "KeywordRule",
    "MatchType",
    "RuleMatchType",
    "SentimentEvent",
    "Session",
    "Severity",
    "SourceType",
    "Stream",
    "StreamStatus",
    "TranscriptSegment",
    "TranscriptToken",
    "WordTimestamp",
]
