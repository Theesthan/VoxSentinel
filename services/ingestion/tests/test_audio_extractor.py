"""
Tests for the audio extractor module.

Validates audio decoding, resampling to 16 kHz mono PCM, and graceful
fallback from hardware to software decoding.
"""

from __future__ import annotations
