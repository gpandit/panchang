"""Admin content store — CRUD + draft/review/publish workflow with version history.

Mirrors the public CMS store but carries the full workflow state and version
snapshots.  On publish, the canonical CMS store is updated so the public API
reflects the new content immediately.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from api.admin import audit as audit_log
from api.cms.store import FestivalContent, upsert_festival
from api.models.admin import (
    ContentStatus,
    ContentVersion,
    FestivalIn,
    FestivalRecord,
)

# In-process store keyed by festival_id
_records: dict[str, FestivalRecord] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _snapshot(data: FestivalIn) -> dict[str, object]:
    return data.model_dump()


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return f"fest-{uuid.uuid4().hex[:8]}"


# ── Public API ─────────────────────────────────────────────────────────────────


def list_records(status: ContentStatus | None = None) -> list[FestivalRecord]:
    results = list(_records.values())
    if status:
        results = [r for r in results if r.status == status]
    return sorted(results, key=lambda r: r.updated_at, reverse=True)


def get_record(festival_id: str) -> FestivalRecord | None:
    return _records.get(festival_id)


def create_record(data: FestivalIn, *, actor_id: str, actor_email: str | None) -> FestivalRecord:
    fid = _new_id()
    now = _now()
    version = ContentVersion(
        version=1,
        status=ContentStatus.DRAFT,
        changed_by=actor_id,
        changed_at=now,
        snapshot=_snapshot(data),
    )
    record = FestivalRecord(
        id=fid,
        status=ContentStatus.DRAFT,
        versions=[version],
        current=data,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    _records[fid] = record
    audit_log.record(
        actor_id=actor_id,
        actor_email=actor_email,
        action="content.create",
        resource_type="festival",
        resource_id=fid,
        detail={"name": data.name, "status": ContentStatus.DRAFT},
    )
    return record


def update_record(
    festival_id: str,
    data: FestivalIn,
    *,
    actor_id: str,
    actor_email: str | None,
) -> FestivalRecord:
    record = _records[festival_id]
    now = _now()
    next_ver = len(record.versions) + 1
    version = ContentVersion(
        version=next_ver,
        status=record.status,
        changed_by=actor_id,
        changed_at=now,
        snapshot=_snapshot(data),
    )
    record.versions.append(version)
    record.current = data
    record.updated_at = now
    audit_log.record(
        actor_id=actor_id,
        actor_email=actor_email,
        action="content.update",
        resource_type="festival",
        resource_id=festival_id,
        detail={"name": data.name, "status": record.status},
    )
    return record


def transition_status(
    festival_id: str,
    new_status: ContentStatus,
    *,
    actor_id: str,
    actor_email: str | None,
) -> FestivalRecord:
    """Move content through the workflow.  Caller must already have verified the role."""
    record = _records[festival_id]
    old_status = record.status
    now = _now()
    next_ver = len(record.versions) + 1
    version = ContentVersion(
        version=next_ver,
        status=new_status,
        changed_by=actor_id,
        changed_at=now,
        snapshot=_snapshot(record.current),
    )
    record.versions.append(version)
    record.status = new_status
    record.updated_at = now

    audit_log.record(
        actor_id=actor_id,
        actor_email=actor_email,
        action=f"content.{new_status.value}",
        resource_type="festival",
        resource_id=festival_id,
        detail={
            "from_status": old_status,
            "to_status": new_status,
            "name": record.current.name,
        },
    )

    if new_status == ContentStatus.PUBLISHED:
        # Sync to the public CMS store so the public API returns it
        upsert_festival(
            FestivalContent(
                id=festival_id,
                slug=record.current.slug,
                name=record.current.name,
                date=record.current.date,
                description=record.current.description,
                body=record.current.body,
                puja=record.current.puja,
                katha=record.current.katha,
                tags=record.current.tags,
                region=record.current.region,
                locale=record.current.locale,
                status="published",
            )
        )

    return record


def delete_record(festival_id: str, *, actor_id: str, actor_email: str | None) -> None:
    record = _records.pop(festival_id, None)
    if record:
        audit_log.record(
            actor_id=actor_id,
            actor_email=actor_email,
            action="content.delete",
            resource_type="festival",
            resource_id=festival_id,
            detail={"name": record.current.name},
        )


def clear() -> None:
    """Test helper."""
    _records.clear()
