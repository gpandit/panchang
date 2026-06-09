"""In-memory flag / review queue store.

Users (or the system) raise flags on content items or Panchang dates.
Admin staff see the queue and resolve or dismiss each flag.
Resolutions feed back into content/rule fixes — tracked via the audit log.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from api.admin import audit as audit_log
from api.models.admin import FlagIn, FlagRecord, FlagStatus

_queue: dict[str, FlagRecord] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def create_flag(data: FlagIn, *, reported_by: str) -> FlagRecord:
    fid = str(uuid.uuid4())
    flag = FlagRecord(
        id=fid,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        reason=data.reason,
        details=data.details,
        reported_by=reported_by,
        reported_at=_now(),
        status=FlagStatus.OPEN,
    )
    _queue[fid] = flag
    return flag


def list_flags(status: FlagStatus | None = None) -> list[FlagRecord]:
    results = list(_queue.values())
    if status:
        results = [f for f in results if f.status == status]
    return sorted(results, key=lambda f: f.reported_at, reverse=True)


def get_flag(flag_id: str) -> FlagRecord | None:
    return _queue.get(flag_id)


def resolve_flag(
    flag_id: str,
    *,
    action: str,
    resolution_note: str | None,
    actor_id: str,
    actor_email: str | None,
) -> FlagRecord:
    flag = _queue[flag_id]
    now = _now()
    flag.status = FlagStatus.RESOLVED if action == "resolve" else FlagStatus.DISMISSED
    flag.reviewed_by = actor_id
    flag.reviewed_at = now
    flag.resolution_note = resolution_note

    audit_log.record(
        actor_id=actor_id,
        actor_email=actor_email,
        action=f"flag.{action}",
        resource_type=flag.resource_type,
        resource_id=flag.resource_id,
        detail={
            "flag_id": flag_id,
            "reason": flag.reason,
            "resolution_note": resolution_note,
        },
    )
    return flag


def clear() -> None:
    _queue.clear()
