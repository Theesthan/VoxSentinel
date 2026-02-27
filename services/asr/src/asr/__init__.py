"""
VoxSentinel ASR Engine Abstraction Layer.

Provides a unified interface for routing audio chunks to pluggable
ASR backends (Deepgram Nova-2, Whisper V3 Turbo, etc.) and emitting
standardized TranscriptToken streams.
"""
