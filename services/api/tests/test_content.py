"""Tests for the Content / CMS module (Step 2.3).

Exercises ContentService directly against an in-memory SQLite database.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.content.db import init_models, make_engine
from api.content.models import ContentStatus
from api.content.schemas import ContentCreateRequest, ContentUpdateRequest, FlagRequest
from api.content.service import ContentError, ContentService

# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
async def session_factory() -> async_sessionmaker[AsyncSession]:
    engine = make_engine("sqlite+aiosqlite://")
    await init_models(engine)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_factory) -> AsyncSession:
    async with session_factory() as s:
        yield s


def _svc(session: AsyncSession) -> ContentService:
    return ContentService(session)


def _festival_req(**overrides) -> ContentCreateRequest:
    defaults = {
        "slug": "diwali-hi",
        "content_type": "festival",
        "locale": "hi",
        "region_tags": ["north", "gujarat"],
        "festival_rule_id": "rule-diwali-001",
        "body": {
            "title": "दीपावली",
            "subtitle": "रोशनी का पर्व",
            "body": "दीपावली हिंदू धर्म का प्रमुख त्यौहार है।",
            "puja_vidhi": "लक्ष्मी पूजन विधि...",
            "katha": "प्राचीन कथा...",
        },
        "source_attribution": "Traditional sources",
        "author_id": "editor-001",
    }
    defaults.update(overrides)
    return ContentCreateRequest(**defaults)


# ── Create → review → publish flow ────────────────────────────────────────────


async def test_create_draft(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await session.commit()

    assert item.status == ContentStatus.DRAFT.value
    assert item.slug == "diwali-hi"
    assert item.locale == "hi"
    assert item.festival_rule_id == "rule-diwali-001"
    assert item.published_version is None


async def test_draft_not_visible_publicly(session: AsyncSession) -> None:
    svc = _svc(session)
    await svc.create_draft(_festival_req())
    await session.commit()

    results = await svc.get_published()
    assert results == []


async def test_in_review_not_visible_publicly(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    await session.commit()

    results = await svc.get_published()
    assert results == []


async def test_publish_makes_item_visible(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    published_item, ver = await svc.publish(item.id)
    await session.commit()

    assert published_item.status == ContentStatus.PUBLISHED.value
    assert published_item.published_version == 1
    assert ver.version_number == 1
    assert ver.body["title"] == "दीपावली"

    results = await svc.get_published()
    assert len(results) == 1
    result_item, result_ver = results[0]
    assert result_item.id == item.id
    assert result_ver.version_number == 1


async def test_version_history_retained_after_republish(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    await svc.publish(item.id)
    await session.commit()

    # Update body and re-publish.
    await svc.flag(item.id, FlagRequest(reason="Body needs correction"))
    await svc.update_draft(
        item.id,
        ContentUpdateRequest(
            body={"title": "दीपावली — सुधारित", "body": "सुधारित सामग्री"},
            source_attribution="Corrected by editor",
        ),
    )
    _, ver2 = await svc.publish(item.id)
    await session.commit()

    assert ver2.version_number == 2

    full = await svc.get_item(item.id)
    version_numbers = {v.version_number for v in full.versions if v.version_number > 0}
    assert version_numbers == {1, 2}


# ── Locale / region filtering ─────────────────────────────────────────────────


async def test_locale_filtering(session: AsyncSession) -> None:
    svc = _svc(session)

    for locale in ("hi", "en", "mr"):
        item = await svc.create_draft(_festival_req(slug=f"diwali-{locale}", locale=locale))
        await svc.submit_for_review(item.id)
        await svc.publish(item.id)
    await session.commit()

    results = await svc.get_published(locale="hi")
    assert len(results) == 1
    assert results[0][0].locale == "hi"


async def test_region_tag_filtering(session: AsyncSession) -> None:
    svc = _svc(session)

    north_item = await svc.create_draft(_festival_req(slug="diwali-north", region_tags=["north"]))
    await svc.submit_for_review(north_item.id)
    await svc.publish(north_item.id)

    south_item = await svc.create_draft(_festival_req(slug="diwali-south", region_tags=["south"]))
    await svc.submit_for_review(south_item.id)
    await svc.publish(south_item.id)
    await session.commit()

    north_results = await svc.get_published(region_tag="north")
    assert len(north_results) == 1
    assert north_results[0][0].slug == "diwali-north"

    south_results = await svc.get_published(region_tag="south")
    assert len(south_results) == 1
    assert south_results[0][0].slug == "diwali-south"


async def test_festival_rule_id_filtering(session: AsyncSession) -> None:
    svc = _svc(session)

    item_a = await svc.create_draft(_festival_req(slug="diwali-a", festival_rule_id="rule-001"))
    await svc.submit_for_review(item_a.id)
    await svc.publish(item_a.id)

    item_b = await svc.create_draft(_festival_req(slug="diwali-b", festival_rule_id="rule-002"))
    await svc.submit_for_review(item_b.id)
    await svc.publish(item_b.id)
    await session.commit()

    results = await svc.get_published(festival_rule_id="rule-001")
    assert len(results) == 1
    assert results[0][0].festival_rule_id == "rule-001"


# ── Flag / correction hook ────────────────────────────────────────────────────


async def test_flag_transitions_to_in_review(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    await svc.publish(item.id)
    await session.commit()

    flag = await svc.flag(
        item.id, FlagRequest(reason="Incorrect puja vidhi", reporter_id="user-999")
    )
    await session.commit()

    assert flag.reason == "Incorrect puja vidhi"
    assert flag.reporter_id == "user-999"
    assert flag.resolved_at is None

    refreshed = await svc.get_item(item.id)
    assert refreshed.status == ContentStatus.IN_REVIEW.value


async def test_flagged_item_not_visible_publicly(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    await svc.publish(item.id)
    await svc.flag(item.id, FlagRequest(reason="Error found"))
    await session.commit()

    results = await svc.get_published()
    assert results == []


async def test_flag_resolved_on_republish(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    await svc.publish(item.id)

    flag = await svc.flag(item.id, FlagRequest(reason="Wrong date"))
    flag_id = flag.id

    await svc.publish(item.id)
    await session.commit()

    flags = await svc.list_flags(item.id)
    resolved = next(f for f in flags if f.id == flag_id)
    assert resolved.resolved_at is not None


# ── Invalid transitions ────────────────────────────────────────────────────────


async def test_cannot_publish_draft_directly(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await session.commit()

    with pytest.raises(ContentError, match="must be in_review"):
        await svc.publish(item.id)


async def test_cannot_flag_non_published_item(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await session.commit()

    with pytest.raises(ContentError, match="Only published items can be flagged"):
        await svc.flag(item.id, FlagRequest(reason="Test"))


async def test_cannot_submit_review_twice(session: AsyncSession) -> None:
    svc = _svc(session)
    item = await svc.create_draft(_festival_req())
    await svc.submit_for_review(item.id)
    await session.commit()

    with pytest.raises(ContentError, match="must be in draft"):
        await svc.submit_for_review(item.id)
