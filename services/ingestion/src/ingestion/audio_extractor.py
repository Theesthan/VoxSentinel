"""
Audio extraction module for VoxSentinel ingestion service.

Uses FFmpeg via PyAV bindings to decode audio from video/audio streams,
resample to 16 kHz mono PCM, and handle hardware-accelerated decoding
(NVDEC) when available with graceful CPU fallback.
"""

from __future__ import annotations

import av
import numpy as np
