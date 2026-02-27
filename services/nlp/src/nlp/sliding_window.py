"""
Per-stream sliding text window for VoxSentinel NLP service.

Maintains a rolling window of the last N seconds (default 10 s) of
finalized transcript text per stream for keyword detection. Updates
on each new TranscriptToken arrival.
"""

from __future__ import annotations
