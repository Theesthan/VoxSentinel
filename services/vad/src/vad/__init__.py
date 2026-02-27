"""
VoxSentinel VAD (Voice Activity Detection) Service.

Applies Silero VAD to incoming audio chunks to classify speech vs.
non-speech segments, dropping silent chunks to reduce downstream
ASR processing load and cost.
"""
