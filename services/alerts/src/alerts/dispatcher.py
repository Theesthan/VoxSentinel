"""
Central alert routing dispatcher for VoxSentinel.

Receives alert events from NLP/sentiment/compliance pipelines and
routes them to all configured channels based on severity, alert type,
and stream assignment.
"""

from __future__ import annotations

import structlog
