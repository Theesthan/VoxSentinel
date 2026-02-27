"""
ASR stream router for VoxSentinel.

Routes audio streams to the appropriate ASR engine based on
per-stream configuration, handling engine selection and
connection management.
"""

from __future__ import annotations

import structlog
