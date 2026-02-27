"""
Silero VAD wrapper for VoxSentinel.

Loads and manages the Silero VAD model (via torch.hub or pip),
providing a simple interface for speech/non-speech classification
of audio chunks with configurable confidence thresholds.
"""

from __future__ import annotations

import torch
