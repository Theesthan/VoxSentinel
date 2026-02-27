"""
VAD chunk classification processor for VoxSentinel.

Applies the Silero VAD model to each incoming audio chunk, classifies
it as speech or non-speech, and forwards only speech chunks to the
ASR pipeline. Emits vad_speech_ratio metrics per stream.
"""

from __future__ import annotations

import numpy as np
