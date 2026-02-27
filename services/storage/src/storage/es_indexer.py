"""
Elasticsearch indexer for VoxSentinel storage service.

Indexes redacted transcript text with session, stream, speaker, and
timestamp metadata into Elasticsearch for full-text, fuzzy, regex,
and Boolean search queries.
"""

from __future__ import annotations

from elasticsearch import AsyncElasticsearch
