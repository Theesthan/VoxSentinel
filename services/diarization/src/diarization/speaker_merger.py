"""
Speaker-transcript merger for VoxSentinel.

Intersects speaker diarization segments with ASR word-level timestamps
to assign speaker_id labels per word and per transcript segment.
"""

from __future__ import annotations
