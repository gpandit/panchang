"""In-memory audit log.

Every content and config change records who/what/when.  A future step will
persist this to the PostgreSQL audit_log table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from api.models.admin import AuditEntry

_log: list[AuditEntry] = []


def record(
    *,
    actor_id: str,
    actor_email: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: dict[str, Any] | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(UTC),
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
    )
    _log.append(entry)
    return entry


def list_entries(
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
    actor_id: str | None = None,
    limit: int = 100,
) -> list[AuditEntry]:
    results = _log[:]
    if resource_type:
        results = [e for e in results if e.resource_type == resource_type]
    if resource_id:
        results = [e for e in results if e.resource_id == resource_id]
    if actor_id:
        results = [e for e in results if e.actor_id == actor_id]
    return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]


def clear() -> None:
    """Test helper — reset the audit log."""
    _log.clear()
