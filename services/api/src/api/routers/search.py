"""
Full-text search API router for VoxSentinel.

Provides Elasticsearch-backed search across historical transcripts
supporting exact phrase, fuzzy, regex, and Boolean queries with
result highlighting.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import get_es_client
from api.schemas.search_schemas import SearchHit, SearchRequest, SearchResponse

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_transcripts(
    body: SearchRequest,
    es: Any = Depends(get_es_client),
) -> SearchResponse:
    if es is None:
        return SearchResponse(results=[], total=0)

    # Build Elasticsearch query body.
    must: list[dict[str, Any]] = []

    if body.search_type == "phrase":
        must.append({"match_phrase": {"text": body.query}})
    elif body.search_type == "regex":
        must.append({"regexp": {"text": body.query}})
    else:
        must.append({"match": {"text": {"query": body.query, "fuzziness": "AUTO"}}})

    if body.stream_ids:
        must.append({"terms": {"stream_id": body.stream_ids}})
    if body.speaker_id:
        must.append({"term": {"speaker_id": body.speaker_id}})
    if body.language:
        must.append({"term": {"language": body.language}})

    date_filter: dict[str, Any] = {}
    if body.date_from:
        date_filter["gte"] = body.date_from.isoformat()
    if body.date_to:
        date_filter["lte"] = body.date_to.isoformat()
    if date_filter:
        must.append({"range": {"timestamp": date_filter}})

    query_body: dict[str, Any] = {"bool": {"must": must}}
    highlight_body: dict[str, Any] = {"fields": {"text": {}}}

    try:
        raw = await es.search(
            index="transcripts",
            query=query_body,
            highlight=highlight_body,
            from_=body.offset,
            size=body.limit,
        )
    except Exception as exc:
        # Index may not exist yet (no transcripts indexed).
        err_str = str(exc).lower()
        if "index_not_found" in err_str or "no such index" in err_str:
            return SearchResponse(results=[], total=0)
        raise

    hits = raw.get("hits", {})
    total_val = hits.get("total", {})
    if isinstance(total_val, dict):
        total = total_val.get("value", 0)
    else:
        total = int(total_val)

    results: list[SearchHit] = []
    for h in hits.get("hits", []):
        src = h.get("_source", {})
        highlight = h.get("highlight", {}).get("text", [])
        text = highlight[0] if highlight else src.get("text", "")
        results.append(
            SearchHit(
                segment_id=src.get("segment_id", ""),
                session_id=src.get("session_id", ""),
                stream_id=src.get("stream_id", ""),
                stream_name=src.get("stream_name"),
                speaker_id=src.get("speaker_id"),
                timestamp=src.get("timestamp", ""),
                text=text,
                sentiment_label=src.get("sentiment_label"),
                score=h.get("_score"),
            ),
        )

    return SearchResponse(results=results, total=total)
