"""
Elasticsearch indexer for VoxSentinel storage service.

Indexes redacted transcript text with session, stream, speaker, and
timestamp metadata into Elasticsearch for full-text, fuzzy, regex,
and Boolean search queries.
"""

from __future__ import annotations

from typing import Any

import structlog
from elasticsearch import AsyncElasticsearch

from tg_common.models.transcript import TranscriptSegment

logger = structlog.get_logger(__name__)

INDEX_NAME = "transcripts"

# Elasticsearch index mapping for the ``transcripts`` index.
INDEX_MAPPING: dict[str, Any] = {
    "mappings": {
        "properties": {
            "segment_id": {"type": "keyword"},
            "session_id": {"type": "keyword"},
            "stream_id": {"type": "keyword"},
            "speaker_id": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "text": {"type": "text", "analyzer": "standard"},
            "sentiment_label": {"type": "keyword"},
            "language": {"type": "keyword"},
        },
    },
}


class ESIndexer:
    """Indexes redacted transcript segments into Elasticsearch.

    Parameters
    ----------
    es_client:
        An ``AsyncElasticsearch`` instance.
    index_name:
        Target index name (defaults to ``"transcripts"``).
    """

    def __init__(
        self,
        es_client: AsyncElasticsearch,
        index_name: str = INDEX_NAME,
    ) -> None:
        self._es = es_client
        self._index = index_name

    async def ensure_index(self) -> None:
        """Create the index if it does not yet exist."""
        exists = await self._es.indices.exists(index=self._index)
        if not exists:
            await self._es.indices.create(index=self._index, body=INDEX_MAPPING)
            logger.info("es_index_created", index=self._index)

    async def index_segment(
        self,
        segment: TranscriptSegment,
        segment_hash: str | None = None,
    ) -> Any:
        """Index a single transcript segment.

        Only the *redacted* text is stored in ES.  Returns the ES
        response dict.
        """
        doc: dict[str, Any] = {
            "segment_id": str(segment.segment_id),
            "session_id": str(segment.session_id),
            "stream_id": str(segment.stream_id),
            "speaker_id": segment.speaker_id,
            "timestamp": segment.start_time.isoformat(),
            "text": segment.text_redacted,
            "sentiment_label": segment.sentiment_label,
            "language": segment.language,
        }
        resp = await self._es.index(
            index=self._index,
            id=str(segment.segment_id),
            document=doc,
        )
        logger.debug(
            "segment_indexed",
            segment_id=str(segment.segment_id),
            es_result=resp.get("result") if isinstance(resp, dict) else None,
        )
        return resp

    async def search(
        self,
        query_text: str,
        *,
        session_id: str | None = None,
        stream_id: str | None = None,
        size: int = 20,
    ) -> Any:
        """Full-text search across indexed transcripts.

        Supports phrase queries and highlights matching text.
        """
        must: list[dict[str, Any]] = [
            {"match": {"text": {"query": query_text}}},
        ]
        if session_id:
            must.append({"term": {"session_id": session_id}})
        if stream_id:
            must.append({"term": {"stream_id": stream_id}})

        body: dict[str, Any] = {
            "query": {"bool": {"must": must}},
            "highlight": {"fields": {"text": {}}},
            "size": size,
        }
        return await self._es.search(index=self._index, body=body)

    async def close(self) -> None:
        """Close the underlying ES transport."""
        await self._es.close()
