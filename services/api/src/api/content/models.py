"""ORM models for the Content / CMS module.

Editorial workflow: draft → in_review → published (→ archived).
Drafts and in_review items are never served on the public API surface.

`festival_rule_id` is a cross-service reference (string) to a FestivalRule
in the festivals service — not a FK, because the two services run separately.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ContentBase(DeclarativeBase):
    """Declarative base for all Content-module ORM models."""


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ContentType(str, Enum):
    FESTIVAL = "festival"
    VRAT = "vrat"
    EDUCATIONAL = "educational"
    MANTRA = "mantra"
    TEMPLATE = "template"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentItem(ContentBase):
    """A single piece of CMS content (one locale + region variant).

    One logical "thing" (e.g. Diwali festival page in Hindi for North India)
    is one row. Each publication creates an immutable ContentVersion snapshot.
    """

    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(200), index=True)
    content_type: Mapped[str] = mapped_column(String(32))

    # Cross-service reference — null for non-festival content types.
    festival_rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    locale: Mapped[str] = mapped_column(String(16))        # BCP-47, e.g. "hi", "en", "mr"
    region_tags: Mapped[list] = mapped_column(JSON, default=list)  # e.g. ["north", "gujarat"]

    status: Mapped[str] = mapped_column(String(16), default=ContentStatus.DRAFT.value)

    # The most recent published version number (null until first publish).
    published_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    versions: Mapped[list["ContentVersion"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ContentVersion.version_number"
    )
    flags: Mapped[list["ContentFlag"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class ContentVersion(ContentBase):
    """Immutable snapshot of a ContentItem at the time it was published.

    Every publish creates a new row; history is never deleted.
    """

    __tablename__ = "content_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_items.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)

    # Structured content body — flexible schema per content_type.
    # Festival: {title, subtitle, body, puja_vidhi, katha, significance, ...}
    # Mantra:   {text, transliteration, meaning, audio_url, ...}
    # etc.
    body: Mapped[dict] = mapped_column(JSON)

    # Who authored / where it came from.
    author_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_attribution: Mapped[str | None] = mapped_column(String(500), nullable=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    item: Mapped["ContentItem"] = relationship(back_populates="versions")


class ContentFlag(ContentBase):
    """A user/editor correction flag on a published item.

    Creating a flag transitions the item back to in_review.
    Flags are resolved by an admin after corrections are made and re-published.
    """

    __tablename__ = "content_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_items.id"), index=True)

    reporter_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user id, optional for anonymous
    reason: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    # resolved_at is set when an admin re-publishes the item after correction.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    item: Mapped["ContentItem"] = relationship(back_populates="flags")
