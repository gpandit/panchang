"""Pydantic schemas for the Content / CMS module.

Admin schemas cover the full editorial surface.
Public schemas expose only what published items need.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from api.content.models import ContentStatus, ContentType


# ── Admin: create ─────────────────────────────────────────────────────────────

class ContentCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200)
    content_type: ContentType
    locale: str = Field(..., min_length=2, max_length=16)
    region_tags: list[str] = Field(default_factory=list)
    festival_rule_id: str | None = None

    # Initial body (saved as version 1 on first publish).
    body: dict[str, Any]
    source_attribution: str | None = Field(None, max_length=500)
    author_id: str | None = None


class ContentUpdateRequest(BaseModel):
    body: dict[str, Any]
    source_attribution: str | None = Field(None, max_length=500)
    author_id: str | None = None


# ── Admin: responses ──────────────────────────────────────────────────────────

class ContentVersionOut(BaseModel):
    id: str
    version_number: int
    body: dict[str, Any]
    author_id: str | None
    source_attribution: str | None
    published_at: datetime

    model_config = {"from_attributes": True}


class ContentItemAdminOut(BaseModel):
    id: str
    slug: str
    content_type: ContentType
    locale: str
    region_tags: list[str]
    festival_rule_id: str | None
    status: ContentStatus
    published_version: int | None
    created_at: datetime
    updated_at: datetime
    versions: list[ContentVersionOut]

    model_config = {"from_attributes": True}


# ── Public: responses (published only) ───────────────────────────────────────

class ContentItemPublicOut(BaseModel):
    id: str
    slug: str
    content_type: ContentType
    locale: str
    region_tags: list[str]
    festival_rule_id: str | None
    published_version: int
    body: dict[str, Any]
    source_attribution: str | None
    published_at: datetime

    model_config = {"from_attributes": True}


# ── Flag ─────────────────────────────────────────────────────────────────────

class FlagRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)
    detail: dict[str, Any] = Field(default_factory=dict)
    reporter_id: str | None = None


class FlagOut(BaseModel):
    id: str
    item_id: str
    reporter_id: str | None
    reason: str
    detail: dict[str, Any]
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
