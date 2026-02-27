"""
VoxSentinel Storage & Indexing Service.

Persists redacted transcripts, alerts, and audit hashes to
PostgreSQL/TimescaleDB and indexes transcript text in Elasticsearch
for full-text search.
"""

__version__ = "0.1.0"
