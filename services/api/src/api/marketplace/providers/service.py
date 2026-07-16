"""Business logic for provider registration & onboarding (A1).

Three operations, mirroring the dev-plan A1 Build list:

1. :meth:`ProviderOnboardingService.register` — create (or upgrade a user to) a
   Pandit provider profile, starting in ``OnboardingState.DRAFT``.
2. :meth:`ProviderOnboardingService.accept_agreement` — record a versioned,
   logged acceptance of one of the three required legal documents.
3. :meth:`ProviderOnboardingService.submit_for_review` — the ``DRAFT`` →
   ``SUBMITTED`` transition, gated on every required agreement having at least one
   acceptance on file.

:meth:`ProviderOnboardingService.transition_onboarding_state` is the general state
machine entry point (also used by ops/E1 later for the SUBMITTED → APPROVED /
REJECTED / CHANGES_REQUESTED transitions, and by CHANGES_REQUESTED → DRAFT).
Illegal transitions raise :class:`IllegalTransitionError`, which the router maps to
a 409.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from api.db.marketplace_models import (
    ONBOARDING_TRANSITIONS,
    AgreementAcceptanceRow,
    AgreementType,
    OnboardingState,
    PanditRow,
)
from api.marketplace.providers.repository import (
    AgreementAcceptanceRepository,
    PanditRepository,
)

#: Every agreement a pandit must accept at least once before submitting for review
#: (dev-plan A1: "agreement / code-of-conduct / cancellation-policy"). Explicit
#: tuple (not "all AgreementType members") so a future addition to the enum doesn't
#: silently change the submit gate without a deliberate edit here.
REQUIRED_AGREEMENTS: tuple[AgreementType, ...] = (
    AgreementType.PARTNER_AGREEMENT,
    AgreementType.CODE_OF_CONDUCT,
    AgreementType.CANCELLATION_POLICY,
)


class ProviderAlreadyRegisteredError(Exception):
    """Raised when a user who already has a Pandit profile registers again."""


class PanditNotFoundError(Exception):
    """Raised when an operation references a pandit id that does not exist."""


class IllegalTransitionError(Exception):
    """Raised when a requested onboarding-state transition is not legal.

    Carries the current and requested states so the router can build a precise
    4xx error body.
    """

    def __init__(self, current: OnboardingState, requested: OnboardingState) -> None:
        self.current = current
        self.requested = requested
        super().__init__(
            f"Cannot transition onboarding state from {current.value!r} to {requested.value!r}."
        )


class MissingAgreementsError(Exception):
    """Raised when submit_for_review is called with required agreements unaccepted."""

    def __init__(self, missing: list[AgreementType]) -> None:
        self.missing = missing
        names = ", ".join(a.value for a in missing)
        super().__init__(f"Missing required agreement acceptance(s): {names}.")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _now() -> datetime:
    return datetime.now(UTC)


class ProviderOnboardingService:
    def __init__(
        self,
        pandit_repo: PanditRepository,
        agreement_repo: AgreementAcceptanceRepository,
    ) -> None:
        self._pandits = pandit_repo
        self._agreements = agreement_repo

    async def register(
        self,
        *,
        user_id: str,
        display_name: str,
        bio: str | None = None,
        base_location_id: str | None = None,
        languages: list[str] | None = None,
        tradition: str | None = None,
        experience_years: int | None = None,
    ) -> PanditRow:
        """Create the Pandit provider profile for ``user_id``, starting in DRAFT.

        One profile per user — a second call for a user who already has one raises
        :class:`ProviderAlreadyRegisteredError` rather than silently creating a
        duplicate (the dev-plan phrases this as "create/upgrade a user to the
        pandit role"; upgrading an *existing* profile is out of A1's scope — that is
        catalogue/profile editing, not onboarding).
        """
        existing = await self._pandits.by_user_id(user_id)
        if existing is not None:
            raise ProviderAlreadyRegisteredError(
                f"user {user_id!r} already has a provider profile ({existing.id})"
            )

        now = _now()
        pandit = PanditRow(
            id=_new_id("pandit"),
            user_id=user_id,
            display_name=display_name,
            bio=bio,
            base_location_id=base_location_id,
            languages=list(languages or []),
            tradition=tradition,
            experience_years=experience_years,
            onboarding_state=OnboardingState.DRAFT.value,
            created_at=now,
            updated_at=now,
        )
        return await self._pandits.add(pandit)

    async def accept_agreement(
        self,
        *,
        pandit_id: str,
        agreement_type: AgreementType,
        version: str,
        accepted_by: str,
    ) -> AgreementAcceptanceRow:
        """Log a versioned acceptance of one agreement document.

        Every acceptance is inserted as a new row (never updated in place) so the
        history of *which version was accepted, by whom, and when* is preserved even
        across re-acceptance of a later version.
        """
        pandit = await self._pandits.get(pandit_id)
        if pandit is None:
            raise PanditNotFoundError(f"no pandit with id {pandit_id!r}")

        acceptance = AgreementAcceptanceRow(
            id=_new_id("agree"),
            pandit_id=pandit_id,
            agreement_type=agreement_type.value,
            version=version,
            accepted_by=accepted_by,
            accepted_at=_now(),
        )
        return await self._agreements.add(acceptance)

    async def missing_required_agreements(self, pandit_id: str) -> list[AgreementType]:
        """Which of :data:`REQUIRED_AGREEMENTS` have never been accepted by this pandit."""
        latest = await self._agreements.latest_versions(pandit_id)
        return [a for a in REQUIRED_AGREEMENTS if a.value not in latest]

    async def transition_onboarding_state(
        self, *, pandit_id: str, to_state: OnboardingState
    ) -> PanditRow:
        """Apply an onboarding-state transition, enforcing :data:`ONBOARDING_TRANSITIONS`.

        Raises :class:`PanditNotFoundError` / :class:`IllegalTransitionError`. The
        router maps the latter to a 409 Conflict with the current + requested state
        in the body, per the dev-plan's "reject illegal ones with a clear 4xx".
        """
        pandit = await self._pandits.get(pandit_id)
        if pandit is None:
            raise PanditNotFoundError(f"no pandit with id {pandit_id!r}")

        current = OnboardingState(pandit.onboarding_state)
        allowed = ONBOARDING_TRANSITIONS.get(current, frozenset())
        if to_state not in allowed:
            raise IllegalTransitionError(current, to_state)

        pandit.onboarding_state = to_state.value
        pandit.updated_at = _now()
        await self._pandits.session.flush()
        return pandit

    async def submit_for_review(self, *, pandit_id: str) -> PanditRow:
        """The DRAFT → SUBMITTED transition, gated on all required agreements.

        Raises :class:`MissingAgreementsError` (mapped to 4xx by the router) if any
        of :data:`REQUIRED_AGREEMENTS` has never been accepted; otherwise delegates
        to :meth:`transition_onboarding_state`, which also enforces that the pandit
        is currently in ``DRAFT`` (any other starting state is an illegal transition).
        """
        missing = await self.missing_required_agreements(pandit_id)
        if missing:
            raise MissingAgreementsError(missing)
        return await self.transition_onboarding_state(
            pandit_id=pandit_id, to_state=OnboardingState.SUBMITTED
        )


__all__ = [
    "REQUIRED_AGREEMENTS",
    "IllegalTransitionError",
    "MissingAgreementsError",
    "PanditNotFoundError",
    "ProviderAlreadyRegisteredError",
    "ProviderOnboardingService",
]
