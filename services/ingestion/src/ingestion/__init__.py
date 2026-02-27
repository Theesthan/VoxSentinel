"""
VoxSentinel Ingestion Service.

Handles audio extraction from external sources (RTSP, HLS, DASH, files),
normalizes audio to 16 kHz mono PCM, and produces timestamped chunks
for downstream VAD and ASR processing.
"""
