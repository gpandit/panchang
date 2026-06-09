"""Admin-layer models: roles, audit entries, flags, reporting."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class AdminRole(str, Enum):
    """Ordered admin roles — viewer < editor < publisher < super_admin."""

    VIEWER = "viewer"
    EDITOR = "editor"
    PUBLISHER = "publisher"
    SUPER_ADMIN = "super_admin"

    _ORDER = None  # set below

    def meets(self, required: "AdminRole") -> bool:
        order = [AdminRole.VIEWER, AdminRole.EDITOR, AdminRole.PUBLISHER, AdminRole.SUPER_ADMIN]
        return order.index(self) >= order.index(required)


# ── Audit ──────────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    actor_id: str
    actor_email: str | None
    action: str          # e.g. "content.publish", "content.delete", "flag.resolve"
    resource_type: str   # e.g. "festival", "flag"
    resource_id: str
    detail: dict[str, Any] = {}


# ── Content workflow ───────────────────────────────────────────────────────────

class ContentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ContentVersion(BaseModel):
    version: int
    status: ContentStatus
    changed_by: str
    changed_at: datetime
    snapshot: dict[str, Any]  # full field snapshot at that version


class FestivalIn(BaseModel):
    name: str
    slug: str
    date: str = ""
    description: str | None = None
    body: str | None = None
    puja: str | None = None
    katha: str | None = None
    tags: list[str] = []
    region: str | None = "all"
    locale: str | None = "en"


class FestivalRecord(BaseModel):
    id: str
    status: ContentStatus
    versions: list[ContentVersion]
    current: FestivalIn
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Flag / review queue ────────────────────────────────────────────────────────

class FlagStatus(str, Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class FlagIn(BaseModel):
    resource_type: str   # "festival" | "panchang_date" | "content"
    resource_id: str
    reason: str
    details: str | None = None


class FlagRecord(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    reason: str
    details: str | None
    reported_by: str
    reported_at: datetime
    status: FlagStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    resolution_note: str | None = None


class FlagResolve(BaseModel):
    action: str          # "resolve" | "dismiss"
    resolution_note: str | None = None


# ── Reporting ──────────────────────────────────────────────────────────────────

class ReportRow(BaseModel):
    date: str            # "YYYY-MM-DD"
    signups: int
    active_users: int
    conversions: int     # free→paid upgrades


class ReportOut(BaseModel):
    period: str          # "last_7d" | "last_30d" | "last_90d"
    rows: list[ReportRow]
    totals: ReportRow
