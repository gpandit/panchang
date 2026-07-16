"""Provider (Pandit) Profile & Onboarding router (A1).

Endpoints:

* ``POST /providers/register`` — create the caller's Pandit provider profile
  (starts in ``OnboardingState.DRAFT``).
* ``GET /providers/me`` — the caller's own provider profile.
* ``POST /providers/me/agreements`` — record a versioned, logged acceptance of an
  onboarding legal document (partner agreement / code of conduct / cancellation
  policy).
* ``GET /providers/me/agreements`` — the caller's full acceptance history.
* ``POST /providers/me/submit-for-review`` — the DRAFT → SUBMITTED transition.

All endpoints require the caller to hold ``Role.PANDIT`` on their JWT (F3
``require_role``). **Scope note (inferred):** re-issuing a JWT with the ``pandit``
role added is an auth-service concern outside this module — F3 says a JWT *carrying*
the role must pass ``require_role``, but does not define a "grant this role" flow,
and there is no persisted Users/roles table in this codebase to upgrade (the F3/F4
work only ships ``require_role`` + the ``Role`` enum). A1 therefore models "create/
upgrade a user to the pandit role" as: creating the Pandit provider profile row for
a caller whose token already carries (or has been granted out-of-band) the
``pandit`` role — mirroring every other role-gated router in this codebase
(``require_role``/``require_tier`` are always checked against the *existing* token,
never mutate it). If a real "grant pandit role" flow is needed, it belongs in the
Users domain / auth service, not here.

The ops-side SUBMITTED → APPROVED | REJECTED | CHANGES_REQUESTED transitions belong
to the E1 provider-approval-queue admin console (WS-E) and are intentionally not
exposed here — A1 only wires the patron-invisible DRAFT/SUBMITTED half of the state
machine plus the state-machine engine (``transition_onboarding_state``) both sides
will call.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.marketplace_models import AgreementAcceptanceRow, PanditRow
from api.db.session import get_session
from api.dependencies import require_role
from api.marketplace.providers.repository import (
    AgreementAcceptanceRepository,
    PanditRepository,
)
from api.marketplace.providers.service import (
    IllegalTransitionError,
    MissingAgreementsError,
    PanditNotFoundError,
    ProviderAlreadyRegisteredError,
    ProviderOnboardingService,
)
from api.models.auth import Role, TokenClaims
from api.models.common import ApiResponse
from api.models.marketplace import (
    AgreementAcceptanceIn,
    AgreementAcceptanceOut,
    AgreementType,
    OnboardingState,
    OnboardingTransitionOut,
    PanditRegisterIn,
    PanditRegisterOut,
    VerificationStatus,
)

router = APIRouter(prefix="/providers", tags=["marketplace-providers"])

_pandit_role = require_role(Role.PANDIT)


def _service(session: AsyncSession) -> ProviderOnboardingService:
    return ProviderOnboardingService(
        PanditRepository(session),
        AgreementAcceptanceRepository(session),
    )


def _to_register_out(row: PanditRow) -> PanditRegisterOut:
    return PanditRegisterOut(
        id=row.id,
        user_id=row.user_id,
        display_name=row.display_name,
        onboarding_state=OnboardingState(row.onboarding_state),
        verification_status=VerificationStatus(row.verification_status),
        created_at=row.created_at,
    )


def _to_acceptance_out(row: AgreementAcceptanceRow) -> AgreementAcceptanceOut:
    return AgreementAcceptanceOut(
        id=row.id,
        pandit_id=row.pandit_id,
        agreement_type=AgreementType(row.agreement_type),
        version=row.version,
        accepted_by=row.accepted_by,
        accepted_at=row.accepted_at,
    )


@router.post(
    "/register",
    response_model=ApiResponse[PanditRegisterOut],
    status_code=status.HTTP_201_CREATED,
)
async def register_provider(
    body: PanditRegisterIn,
    claims: Annotated[TokenClaims, Depends(_pandit_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[PanditRegisterOut]:
    """Create the caller's Pandit provider profile, starting in DRAFT."""
    service = _service(session)
    try:
        pandit = await service.register(
            user_id=claims.sub,
            display_name=body.display_name,
            bio=body.bio,
            base_location_id=body.base_location_id,
            languages=body.languages,
            tradition=body.tradition,
            experience_years=body.experience_years,
        )
    except ProviderAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "already_registered", "message": str(exc)},
        ) from exc
    return ApiResponse(data=_to_register_out(pandit))


@router.get("/me", response_model=ApiResponse[PanditRegisterOut])
async def get_own_provider_profile(
    claims: Annotated[TokenClaims, Depends(_pandit_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[PanditRegisterOut]:
    pandit = await PanditRepository(session).by_user_id(claims.sub)
    if pandit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_registered", "message": "No provider profile for this user."},
        )
    return ApiResponse(data=_to_register_out(pandit))


async def _require_own_pandit(session: AsyncSession, claims: TokenClaims) -> PanditRow:
    pandit = await PanditRepository(session).by_user_id(claims.sub)
    if pandit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_registered", "message": "No provider profile for this user."},
        )
    return pandit


@router.post(
    "/me/agreements",
    response_model=ApiResponse[AgreementAcceptanceOut],
    status_code=status.HTTP_201_CREATED,
)
async def accept_agreement(
    body: AgreementAcceptanceIn,
    claims: Annotated[TokenClaims, Depends(_pandit_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[AgreementAcceptanceOut]:
    """Log acceptance of one versioned onboarding agreement (partner agreement /
    code of conduct / cancellation policy)."""
    pandit = await _require_own_pandit(session, claims)
    service = _service(session)
    acceptance = await service.accept_agreement(
        pandit_id=pandit.id,
        agreement_type=body.agreement_type,
        version=body.version,
        accepted_by=claims.sub,
    )
    return ApiResponse(data=_to_acceptance_out(acceptance))


@router.get("/me/agreements", response_model=ApiResponse[list[AgreementAcceptanceOut]])
async def list_own_agreement_acceptances(
    claims: Annotated[TokenClaims, Depends(_pandit_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[AgreementAcceptanceOut]]:
    pandit = await _require_own_pandit(session, claims)
    rows = await AgreementAcceptanceRepository(session).list_for_pandit(pandit.id)
    return ApiResponse(data=[_to_acceptance_out(r) for r in rows])


@router.post(
    "/me/submit-for-review",
    response_model=ApiResponse[OnboardingTransitionOut],
)
async def submit_for_review(
    claims: Annotated[TokenClaims, Depends(_pandit_role)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[OnboardingTransitionOut]:
    """DRAFT → SUBMITTED, gated on every required agreement being accepted."""
    pandit = await _require_own_pandit(session, claims)
    previous = OnboardingState(pandit.onboarding_state)
    service = _service(session)
    try:
        updated = await service.submit_for_review(pandit_id=pandit.id)
    except MissingAgreementsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "missing_agreements",
                "message": str(exc),
                "missing": [a.value for a in exc.missing],
            },
        ) from exc
    except IllegalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "illegal_transition",
                "message": str(exc),
                "current_state": exc.current.value,
                "requested_state": exc.requested.value,
            },
        ) from exc
    except PanditNotFoundError as exc:  # pragma: no cover — guarded by _require_own_pandit
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApiResponse(
        data=OnboardingTransitionOut(
            id=updated.id,
            onboarding_state=OnboardingState(updated.onboarding_state),
            previous_state=previous,
        )
    )
