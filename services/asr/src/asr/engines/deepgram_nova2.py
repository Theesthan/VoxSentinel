"""
Deepgram Nova-2 ASR engine implementation for VoxSentinel.

Connects to the Deepgram Nova-2 streaming API via WebSocket,
sends audio chunks, and returns partial/final TranscriptToken
objects with word-level timestamps and confidence scores.
"""

from __future__ import annotations

from deepgram import DeepgramClient
