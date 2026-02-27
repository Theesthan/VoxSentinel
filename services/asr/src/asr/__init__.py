"""
VoxSentinel ASR Engine Abstraction Layer.

Provides a unified interface for routing audio chunks to pluggable
ASR backends (Deepgram Nova-2, Whisper V3 Turbo, etc.) and emitting
standardized TranscriptToken streams.
"""

from asr.engine_base import ASREngine
from asr.engine_registry import (
    clear_registry,
    get_engine_class,
    list_engines,
    register_engine,
)
from asr.failover import ASRCircuitBreaker, ASRFailoverManager

__all__ = [
    "ASRCircuitBreaker",
    "ASREngine",
    "ASRFailoverManager",
    "clear_registry",
    "get_engine_class",
    "list_engines",
    "register_engine",
]
