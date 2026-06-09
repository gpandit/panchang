"""ContentService — editorial workflow and public query layer.

Workflow states:
  draft → in_review → published (→ archived)

A flag on a published item transitions it back to in_review.
Drafts and in_review items are never returned by the public query methods.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.content.models import ContentFlag, ContentItem, ContentStatus, ContentVersion
from api.content.schemas import ContentCreateRequest, ContentUpdateRequest, FlagRequest


class ContentError(Exception):
    """Raised for invalid state transitions or missing items."""


def _now() -> datetime:
    return datetime.now(UTC)


class ContentService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Admin: create ─────────────────────────────────────────────────────────

    async def create_draft(self, req: ContentCreateRequest) -> ContentItem:
        """Create a new content item in DRAFT state with an initial body payload.

        The body is saved in the item's metadata but not yet versioned — a
        version snapshot is only created on publish.
        """
        item = ContentItem(
            slug=req.slug,
            content_type=req.content_type.value,
            locale=req.locale,
            region_tags=req.region_tags,
            festival_rule_id=req.festival_rule_id,
            status=ContentStatus.DRAFT.value,
            # Stash the working body + attribution on the item row so editors
            # can iterate without creating version rows until publish.
        )
        # Store working body as a "pending" version placeholder keyed at 0.
        # We keep it as a Version row with version_number=0 so we always have
        # a body to promote on first publish.
        pending = ContentVersion(
            item=item,
            version_number=0,
            body=req.body,
            author_id=req.author_id,
            source_attribution=req.source_attribution,
        )
        self._s.add(item)
        self._s.add(pending)
        await self._s.flush()
        return item

    async def update_draft(self, item_id: str, req: ContentUpdateRequest) -> ContentItem:
        """Replace the working body of a DRAFT item."""
        item = await self._get(item_id)
        if item.status not in (ContentStatus.DRAFT.value, ContentStatus.IN_REVIEW.value):
            raise ContentError(
                f"Item {item_id} is {item.status}; only draft/in_review items can be updated"
            )

        pending = await self._pending_version(item_id)
        pending.body = req.body
        pending.author_id = req.author_id
        pending.source_attribution = req.source_attribution
        await self._s.flush()
        return item

    # ── Admin: workflow transitions ───────────────────────────────────────────

    async def submit_for_review(self, item_id: str) -> ContentItem:
        item = await self._get(item_id)
        if item.status != ContentStatus.DRAFT.value:
            raise ContentError(
                f"Item {item_id} must be in draft to submit for review (current: {item.status})"
            )
        item.status = ContentStatus.IN_REVIEW.value
        await self._s.flush()
        return item

    async def publish(self, item_id: str) -> tuple[ContentItem, ContentVersion]:
        """Publish the item: snapshot the working body as the next version."""
        item = await self._get(item_id)
        if item.status != ContentStatus.IN_REVIEW.value:
            raise ContentError(
                f"Item {item_id} must be in_review to publish (current: {item.status})"
            )

        pending = await self._pending_version(item_id)

        # Next version number.
        next_ver = (item.published_version or 0) + 1

        version = ContentVersion(
            item_id=item_id,
            version_number=next_ver,
            body=pending.body,
            author_id=pending.author_id,
            source_attribution=pending.source_attribution,
            published_at=_now(),
        )
        self._s.add(version)

        item.status = ContentStatus.PUBLISHED.value
        item.published_version = next_ver

        # Resolve any open flags (item has been corrected and re-published).
        result = await self._s.execute(
            select(ContentFlag).where(
                ContentFlag.item_id == item_id,
                ContentFlag.resolved_at.is_(None),
            )
        )
        for flag in result.scalars().all():
            flag.resolved_at = _now()

        await self._s.flush()
        return item, version

    async def archive(self, item_id: str) -> ContentItem:
        item = await self._get(item_id)
        item.status = ContentStatus.ARCHIVED.value
        await self._s.flush()
        return item

    # ── Public: read (published only) ────────────────────────────────────────

    async def get_published(
        self,
        *,
        locale: str | None = None,
        region_tag: str | None = None,
        content_type: str | None = None,
        festival_rule_id: str | None = None,
        slug: str | None = None,
    ) -> list[tuple[ContentItem, ContentVersion]]:
        """Return published items with their most-recent published version.

        All filters are AND-ed. Region-tag filtering matches any item whose
        region_tags list contains the requested tag.
        """
        stmt = (
            select(ContentItem)
            .where(ContentItem.status == ContentStatus.PUBLISHED.value)
            .options(selectinload(ContentItem.versions))
            .execution_options(populate_existing=True)
        )
        if locale:
            stmt = stmt.where(ContentItem.locale == locale)
        if content_type:
            stmt = stmt.where(ContentItem.content_type == content_type)
        if festival_rule_id:
            stmt = stmt.where(ContentItem.festival_rule_id == festival_rule_id)
        if slug:
            stmt = stmt.where(ContentItem.slug == slug)

        result = await self._s.execute(stmt)
        items = result.scalars().all()

        out: list[tuple[ContentItem, ContentVersion]] = []
        for item in items:
            ver = self._published_version(item)
            if ver is None:
                continue
            if region_tag and region_tag not in (item.region_tags or []):
                continue
            out.append((item, ver))
        return out

    async def get_published_one(
        self, slug: str, locale: str | None = None
    ) -> tuple[ContentItem, ContentVersion]:
        pairs = await self.get_published(slug=slug, locale=locale)
        if not pairs:
            raise ContentError(f"No published content found for slug={slug!r}")
        return pairs[0]

    # ── Admin: read (any status) ──────────────────────────────────────────────

    async def get_item(self, item_id: str) -> ContentItem:
        return await self._get(item_id, load_versions=True)

    async def list_items(
        self,
        *,
        status: str | None = None,
        content_type: str | None = None,
        locale: str | None = None,
    ) -> list[ContentItem]:
        stmt = select(ContentItem).options(selectinload(ContentItem.versions))
        if status:
            stmt = stmt.where(ContentItem.status == status)
        if content_type:
            stmt = stmt.where(ContentItem.content_type == content_type)
        if locale:
            stmt = stmt.where(ContentItem.locale == locale)
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    # ── Flag / correction hook ────────────────────────────────────────────────

    async def flag(self, item_id: str, req: FlagRequest) -> ContentFlag:
        """Flag a published item for review.

        Transitions status back to in_review and resets the pending version body
        to a copy of the current published version so editors can revise it.
        """
        item = await self._get(item_id, load_versions=True)
        if item.status != ContentStatus.PUBLISHED.value:
            raise ContentError(f"Only published items can be flagged (current: {item.status})")

        current = self._published_version(item)

        # Re-use or create the pending (version_number=0) slot.
        existing_pending = await self._s.execute(
            select(ContentVersion)
            .where(
                ContentVersion.item_id == item_id,
                ContentVersion.version_number == 0,
            )
            .limit(1)
        )
        pending = existing_pending.scalar_one_or_none()
        if pending is None:
            pending = ContentVersion(
                item_id=item_id,
                version_number=0,
                body=current.body if current else {},
                author_id=None,
                source_attribution=current.source_attribution if current else None,
            )
            self._s.add(pending)
        else:
            pending.body = current.body if current else {}
            pending.source_attribution = current.source_attribution if current else None

        item.status = ContentStatus.IN_REVIEW.value

        flag = ContentFlag(
            item_id=item_id,
            reporter_id=req.reporter_id,
            reason=req.reason,
            detail=req.detail,
        )
        self._s.add(flag)
        await self._s.flush()
        return flag

    async def list_flags(self, item_id: str) -> list[ContentFlag]:
        result = await self._s.execute(select(ContentFlag).where(ContentFlag.item_id == item_id))
        return list(result.scalars().all())

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get(self, item_id: str, *, load_versions: bool = False) -> ContentItem:
        stmt = (
            select(ContentItem)
            .where(ContentItem.id == item_id)
            .execution_options(populate_existing=True)
        )
        if load_versions:
            stmt = stmt.options(selectinload(ContentItem.versions))
        result = await self._s.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            raise ContentError(f"ContentItem {item_id!r} not found")
        return item

    async def _pending_version(self, item_id: str) -> ContentVersion:
        """Return the mutable pending version (version_number == 0)."""
        result = await self._s.execute(
            select(ContentVersion)
            .where(
                ContentVersion.item_id == item_id,
                ContentVersion.version_number == 0,
            )
            .limit(1)
        )
        pending = result.scalar_one_or_none()
        if pending is None:
            raise ContentError(f"No pending version found for item {item_id!r}")
        return pending

    @staticmethod
    def _published_version(item: ContentItem) -> ContentVersion | None:
        if item.published_version is None:
            return None
        for v in item.versions:
            if v.version_number == item.published_version:
                return v
        return None
