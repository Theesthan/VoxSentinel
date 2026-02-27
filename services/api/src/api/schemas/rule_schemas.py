"""
Keyword rule API schemas for VoxSentinel.

Pydantic request/response models for keyword rule CRUD operations,
including rule creation, update, and filtered list responses.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from typing import Optional

from pydantic import BaseModel, Field


class RuleCreateRequest(BaseModel):
    rule_set_name: str = Field(..., max_length=255)
    keyword: str = Field(...)
    match_type: str = Field(default="exact")
    fuzzy_threshold: Optional[float] = Field(default=0.8, ge=0.0, le=1.0)
    severity: str = Field(default="medium")
    category: str = Field(default="general", max_length=100)
    language: str | None = Field(default=None, max_length=10)
    enabled: bool = Field(default=True)


class RuleCreateResponse(BaseModel):
    rule_id: UUID
    created_at: Optional[datetime] = None


class RuleSummary(BaseModel):
    rule_id: UUID
    rule_set_name: str
    keyword: str
    match_type: str
    fuzzy_threshold: Optional[float] = None
    severity: str
    category: str
    language: str | None
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RuleListResponse(BaseModel):
    rules: list[RuleSummary]
    total: int


class RuleUpdateRequest(BaseModel):
    keyword: str | None = None
    match_type: str | None = None
    fuzzy_threshold: float | None = None
    severity: str | None = None
    category: str | None = None
    language: str | None = None
    enabled: bool | None = None
