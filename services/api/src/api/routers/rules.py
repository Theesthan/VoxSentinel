"""
Keyword rule management API router for VoxSentinel.

CRUD endpoints for creating, reading, updating, and deleting keyword
detection rules with hot-reload support (changes effective within 5 s).
"""

from __future__ import annotations

import json
import uuid as _uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from api.dependencies import get_db_session, get_redis
from api.schemas.rule_schemas import (
    RuleCreateRequest,
    RuleCreateResponse,
    RuleListResponse,
    RuleSummary,
    RuleUpdateRequest,
)

from tg_common.db.orm_models import KeywordRuleORM

logger = structlog.get_logger()

router = APIRouter(prefix="/rules", tags=["rules"])


async def _publish_rules_updated(redis: Any) -> None:
    """Publish ``rules_updated`` so NLP hot-reloads within 5 seconds."""
    if redis is not None:
        await redis.publish("rules_updated", '{"event": "rules_updated"}')


@router.post("", status_code=201, response_model=RuleCreateResponse)
async def create_rule(
    body: RuleCreateRequest,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> RuleCreateResponse:
    rule_id = _uuid.uuid4()

    rule = KeywordRuleORM(
        rule_id=rule_id,
        rule_set_name=body.rule_set_name,
        keyword=body.keyword,
        match_type=body.match_type,
        fuzzy_threshold=body.fuzzy_threshold,
        severity=body.severity,
        category=body.category,
        language=body.language,
        enabled=body.enabled,
    )
    if db is not None:
        db.add(rule)
        await db.commit()
        await db.refresh(rule)

    await _publish_rules_updated(redis)

    return RuleCreateResponse(
        rule_id=rule_id,
        created_at=rule.created_at,
    )


@router.get("", response_model=RuleListResponse)
async def list_rules(
    rule_set_name: str | None = Query(default=None),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    db: Any = Depends(get_db_session),
) -> RuleListResponse:
    if db is None:
        return RuleListResponse(rules=[], total=0)

    from sqlalchemy import select

    stmt = select(KeywordRuleORM)
    if rule_set_name:
        stmt = stmt.where(KeywordRuleORM.rule_set_name == rule_set_name)
    if category:
        stmt = stmt.where(KeywordRuleORM.category == category)
    if language:
        stmt = stmt.where(KeywordRuleORM.language == language)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    rules = [
        RuleSummary(
            rule_id=r.rule_id,
            rule_set_name=r.rule_set_name,
            keyword=r.keyword,
            match_type=r.match_type,
            fuzzy_threshold=r.fuzzy_threshold,
            severity=r.severity,
            category=r.category,
            language=r.language,
            enabled=r.enabled,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return RuleListResponse(rules=rules, total=len(rules))


@router.patch("/{rule_id}", response_model=RuleSummary)
async def update_rule(
    rule_id: _uuid.UUID,
    body: RuleUpdateRequest,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> Any:
    if db is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    from sqlalchemy import select

    result = await db.execute(
        select(KeywordRuleORM).where(KeywordRuleORM.rule_id == rule_id),
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rule, field, value)
    await db.commit()

    await _publish_rules_updated(redis)

    return RuleSummary(
        rule_id=rule.rule_id,
        rule_set_name=rule.rule_set_name,
        keyword=rule.keyword,
        match_type=rule.match_type,
        fuzzy_threshold=rule.fuzzy_threshold,
        severity=rule.severity,
        category=rule.category,
        language=rule.language,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}", status_code=204, response_model=None)
async def delete_rule(
    rule_id: _uuid.UUID,
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> None:
    if db is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    from sqlalchemy import select

    result = await db.execute(
        select(KeywordRuleORM).where(KeywordRuleORM.rule_id == rule_id),
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()

    await _publish_rules_updated(redis)


# ────────────────────────────────────────────────────────
# Export / Import
# ────────────────────────────────────────────────────────

@router.get("/export")
async def export_rules(db: Any = Depends(get_db_session)) -> JSONResponse:
    """Download all keyword rules as a JSON file."""
    if db is None:
        return JSONResponse(content={"rules": []}, headers={
            "Content-Disposition": 'attachment; filename="voxsentinel_rules.json"',
        })

    from sqlalchemy import select

    result = await db.execute(select(KeywordRuleORM))
    rows = result.scalars().all()

    rules_data = [
        {
            "rule_set_name": r.rule_set_name,
            "keyword": r.keyword,
            "match_type": r.match_type,
            "fuzzy_threshold": r.fuzzy_threshold,
            "severity": r.severity,
            "category": r.category,
            "language": r.language,
            "enabled": r.enabled,
        }
        for r in rows
    ]

    return JSONResponse(
        content={"rules": rules_data, "version": 1, "total": len(rules_data)},
        headers={
            "Content-Disposition": 'attachment; filename="voxsentinel_rules.json"',
        },
    )


@router.post("/import", status_code=201)
async def import_rules(
    file: UploadFile = File(...),
    db: Any = Depends(get_db_session),
    redis: Any = Depends(get_redis),
) -> dict:
    """Import keyword rules from a JSON file.  Expects the same format
    produced by ``GET /rules/export``.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    raw = await file.read()
    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    rules_list = payload if isinstance(payload, list) else payload.get("rules", [])
    if not isinstance(rules_list, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of rules (or {\"rules\": [...]})")

    created = 0
    skipped = 0
    for item in rules_list:
        if not isinstance(item, dict) or "keyword" not in item:
            skipped += 1
            continue
        try:
            rule = KeywordRuleORM(
                rule_id=_uuid.uuid4(),
                rule_set_name=item.get("rule_set_name", "imported"),
                keyword=item["keyword"],
                match_type=item.get("match_type", "exact"),
                fuzzy_threshold=item.get("fuzzy_threshold", 0.8),
                severity=item.get("severity", "medium"),
                category=item.get("category", "general"),
                language=item.get("language"),
                enabled=item.get("enabled", True),
            )
            db.add(rule)
            created += 1
        except Exception:
            skipped += 1
            logger.warning("import_rule_skip", item=item)

    await db.commit()
    await _publish_rules_updated(redis)

    logger.info("rules_imported", created=created, skipped=skipped)
    return {"created": created, "skipped": skipped}
