"""
Abstract base class for ASR engine backends in VoxSentinel.

Defines the ASREngine interface that all backends must implement,
including the stream_audio method that accepts audio chunks and
yields unified TranscriptToken objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
