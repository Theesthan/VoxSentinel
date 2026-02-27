"""
Stream connection manager for VoxSentinel ingestion service.

Manages the lifecycle of RTSP, HLS, DASH, and file-based stream
connections. Handles connection setup, teardown, and status tracking
for multiple concurrent streams.
"""

from __future__ import annotations

import structlog
