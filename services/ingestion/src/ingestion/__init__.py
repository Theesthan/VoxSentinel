"""
VoxSentinel Ingestion Service.

Handles audio extraction from external sources (RTSP, HLS, DASH, files),
normalizes audio to 16 kHz mono PCM, and produces timestamped chunks
for downstream VAD and ASR processing.
"""

from __future__ import annotations

from ingestion.audio_extractor import extract_audio
from ingestion.chunk_producer import AudioChunk, produce_chunks
from ingestion.health import router as health_router
from ingestion.reconnection import ReconnectionFailed, with_reconnection
from ingestion.stream_manager import StreamManager

__all__ = [
    "AudioChunk",
    "ReconnectionFailed",
    "StreamManager",
    "extract_audio",
    "health_router",
    "produce_chunks",
    "with_reconnection",
]
