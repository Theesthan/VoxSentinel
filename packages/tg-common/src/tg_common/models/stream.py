"""
Stream data model for VoxSentinel.

Defines the Pydantic model representing an audio/video stream source,
including its configuration for ASR backend, VAD threshold, and metadata.
"""

from __future__ import annotations

from pydantic import BaseModel
