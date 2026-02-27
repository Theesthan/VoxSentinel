"""
pyannote.audio 3.x pipeline wrapper for VoxSentinel.

Loads and manages the pyannote.audio speaker diarization pipeline,
running on 0.5-second overlapping windows to identify speaker
segments with timestamps.
"""

from __future__ import annotations

from pyannote.audio import Pipeline
