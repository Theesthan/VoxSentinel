"""
External speaker metadata handler for VoxSentinel.

Merges platform-provided speaker metadata (real names, roles) from
meeting platform APIs with auto-generated speaker labels
(SPEAKER_00, SPEAKER_01, etc.).
"""

from __future__ import annotations
