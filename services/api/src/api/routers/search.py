"""
Full-text search API router for VoxSentinel.

Provides Elasticsearch-backed search across historical transcripts
supporting exact phrase, fuzzy, regex, and Boolean queries with
result highlighting.
"""

from __future__ import annotations

from fastapi import APIRouter
