"""Persistence for the Provider (Pandit) Profile & Onboarding module (A1).

Builds on the F1 :class:`~api.db.repository.Repository` pattern. The centrepiece is
the **discoverability predicate** (dev-plan A1 "hard gate"): a pandit is not
discoverable until ``onboarding_state == APPROVED`` *and*
``verification_status == VERIFIED``. B1 (Discovery & Search) and A2 (Verification)
do not exist yet, so this predicate is expressed once here — as both a reusable
SQLAlchemy filter expression and a boolean helper — for those steps to import and
reuse rather than re-derive.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, and_, select

from api.db.marketplace_models import (
    AgreementAcceptanceRow,
    OnboardingState,
    PanditRow,
    VerificationStatus,
)
from api.db.repository import Repository


def discoverable_predicate() -> ColumnElement[bool]:
    """The hard discoverability gate as a reusable SQL filter expression.

    ``APPROVED`` onboarding **and** ``VERIFIED`` verification — nothing else makes a
    pandit visible in search. B1 (search) and A2 (verification) should compose this
    into their own queries (e.g. ``select(PanditRow).where(discoverable_predicate())``)
    rather than re-deriving the two-column condition.
    """
    return and_(
        PanditRow.onboarding_state == OnboardingState.APPROVED.value,
        PanditRow.verification_status == VerificationStatus.VERIFIED.value,
    )


def is_discoverable(pandit: PanditRow) -> bool:
    """In-Python mirror of :func:`discoverable_predicate` for an already-loaded row.

    Kept in lockstep with the SQL predicate intentionally — both must agree on
    exactly the same two conditions.
    """
    return (
        pandit.onboarding_state == OnboardingState.APPROVED.value
        and pandit.verification_status == VerificationStatus.VERIFIED.value
    )


class PanditRepository(Repository[PanditRow]):
    model = PanditRow

    async def by_user_id(self, user_id: str) -> PanditRow | None:
        """Return the Pandit profile owned by ``user_id``, or ``None``.

        A user has at most one provider profile — enforced at the service layer
        (register is idempotent-ish: a second call for the same user is rejected).
        """
        result = await self.session.execute(select(PanditRow).where(PanditRow.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_discoverable(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> Sequence[PanditRow]:
        """Return pandits that pass the hard discoverability gate.

        This is the single query B1 (Discovery & Search) should reuse rather than
        re-implementing the APPROVED+VERIFIED condition.
        """
        stmt = select(PanditRow).where(discoverable_predicate())
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AgreementAcceptanceRepository(Repository[AgreementAcceptanceRow]):
    model = AgreementAcceptanceRow

    async def list_for_pandit(self, pandit_id: str) -> Sequence[AgreementAcceptanceRow]:
        """Full acceptance history for a pandit, oldest first (the audit trail)."""
        result = await self.session.execute(
            select(AgreementAcceptanceRow)
            .where(AgreementAcceptanceRow.pandit_id == pandit_id)
            .order_by(AgreementAcceptanceRow.accepted_at)
        )
        return result.scalars().all()

    async def latest_versions(self, pandit_id: str) -> dict[str, Any]:
        """Map of ``agreement_type -> most-recently-accepted version`` for a pandit.

        Used by ``submit_for_review`` to check that every required agreement has at
        least one acceptance on file before allowing the DRAFT → SUBMITTED transition.
        """
        rows = await self.list_for_pandit(pandit_id)
        latest: dict[str, str] = {}
        for row in rows:  # rows are oldest-first, so the last write per type wins
            latest[row.agreement_type] = row.version
        return latest


__all__ = [
    "AgreementAcceptanceRepository",
    "PanditRepository",
    "discoverable_predicate",
    "is_discoverable",
]
