"""
Structured logging setup for VoxSentinel.

Configures structlog for JSON-formatted structured logging across all
services. Every log line includes timestamp, level, service name, and
event. Per-stream context (stream_id, session_id) is bound at processing time.
"""

from __future__ import annotations

