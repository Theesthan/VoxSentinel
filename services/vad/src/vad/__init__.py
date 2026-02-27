"""
VoxSentinel VAD (Voice Activity Detection) Service.

Applies Silero VAD to incoming audio chunks to classify speech vs.
non-speech segments, dropping silent chunks to reduce downstream
ASR processing load and cost.
"""
from __future__ import annotations

from vad.health import router as health_router
from vad.silero_vad import SileroVADModel
from vad.vad_processor import VADProcessor

__all__ = [
    "SileroVADModel",
    "VADProcessor",
    "health_router",
]