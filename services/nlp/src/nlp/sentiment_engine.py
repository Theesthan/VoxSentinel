"""
Sentiment classification engine for VoxSentinel.

Runs DistilBERT-based sentiment model on 3-5 second transcript spans
to classify sentiment as positive/neutral/negative with confidence
scores. Emits escalation alerts on persistent negative sentiment.
"""

from __future__ import annotations

from transformers import pipeline
