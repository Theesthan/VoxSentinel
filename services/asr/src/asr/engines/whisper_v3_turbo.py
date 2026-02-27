"""
Whisper V3 Turbo ASR engine implementation for VoxSentinel.

Self-hosted Whisper V3 Turbo inference using faster-whisper
(CTranslate2-based). Accepts audio chunks via WebSocket and
returns TranscriptToken objects in the unified format.
"""

from __future__ import annotations

from faster_whisper import WhisperModel
