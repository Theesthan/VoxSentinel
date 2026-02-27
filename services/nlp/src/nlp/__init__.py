"""
VoxSentinel NLP & Keyword Engine Service.

Consumes TranscriptTokens and runs keyword matching (Aho-Corasick,
RapidFuzz, regex), sentiment/intent classification (DistilBERT),
and PII redaction (Presidio + spaCy/GLiNER) in parallel pipelines.
"""
