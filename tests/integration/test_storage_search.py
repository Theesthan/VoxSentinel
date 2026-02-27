"""Integration tests: Storage and search.

Verifies that stored transcripts and alerts are correctly indexed in
Elasticsearch and retrievable via the search API, including full-text
search, filtering, and pagination.
"""

import pytest


@pytest.mark.integration
class TestStorageSearch:
    """Test storage persistence and Elasticsearch indexing."""

    async def test_transcript_indexed_in_elasticsearch(self) -> None:
        """Verify transcripts are indexed in Elasticsearch after storage."""
        ...

    async def test_full_text_search_returns_results(self) -> None:
        """Verify full-text search matches stored transcripts."""
        ...

    async def test_search_with_time_range_filter(self) -> None:
        """Verify search results are filtered by time range."""
        ...

    async def test_audit_hash_stored_correctly(self) -> None:
        """Verify SHA-256 audit hashes are persisted for tamper evidence."""
        ...
