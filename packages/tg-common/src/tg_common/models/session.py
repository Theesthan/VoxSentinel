"""
Session data model for VoxSentinel.

Defines the Pydantic model representing a stream session — a continuous
recording period tied to a stream, tracking ASR backend used, segment
counts, and alert counts.
"""

from __future__ import annotations

from pydantic import BaseModel
