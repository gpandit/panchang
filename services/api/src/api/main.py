"""FastAPI application entry point for the API Gateway."""

from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from festivals.rules import DIWALI, HOLI, RAKSHA_BANDHAN

from api.calendar.router import get_calendar_service
from api.calendar.router import router as calendar_router
from api.calendar.service import CalendarService
from api.content.db import make_session_factory as make_content_session_factory
from api.content.router import get_content_service
from api.content.router import router as content_router
from api.content.service import ContentService
from api.settings import get_settings
from api.subscriptions.models import BillingSource
from api.subscriptions.router import get_subscription_service
from api.subscriptions.router import router as subscriptions_router
from api.subscriptions.service import SubscriptionService
from api.subscriptions.verifiers import (
    AppleIAPVerifier,
    ReceiptVerifier,
    StaticAccessTokenProvider,
    GooglePlayVerifier,
    StripeVerifier,
)
from api.users.db import make_session_factory
from api.users.encryption import VaultCipher
from api.users.models import AuthProvider
from api.users.oauth import AppleVerifier, GoogleVerifier, IdentityVerifier
from api.users.router import get_secret_key, get_user_service
from api.users.router import router as users_router
from api.users.service import UserService
from api.users.vault import Vault
from panchang.cache import InMemoryCacheStore, InMemoryPanchangDayStore, PanchangCache
from panchang.compute import compute_panchang

settings = get_settings()

_session_factory = make_session_factory(settings.database_url)

# ── Subscription verifiers ────────────────────────────────────────────────────


def _build_stripe_price_tier_map() -> dict[str, "Tier"]:  # type: ignore[name-defined]
    from api.subscriptions.models import Tier

    result: dict[str, Tier] = {}
    raw = settings.stripe_price_tier_map
    if not raw:
        return result
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        price_id, tier_str = pair.split(":", 1)
        try:
            result[price_id.strip()] = Tier(tier_str.strip())
        except ValueError:
            pass
    return result


_receipt_verifiers: dict[BillingSource, ReceiptVerifier] = {
    BillingSource.APPLE: AppleIAPVerifier(
        shared_secret=settings.apple_iap_shared_secret,
        bundle_id=settings.apple_iap_bundle_id,
        sandbox=settings.apple_iap_sandbox,
    ),
    BillingSource.GOOGLE: GooglePlayVerifier(
        package_name=settings.google_play_package_name,
        access_token_provider=StaticAccessTokenProvider(""),  # replaced by SA in prod
    ),
    BillingSource.STRIPE: StripeVerifier(
        api_key=settings.stripe_secret_key,
        price_tier_map=_build_stripe_price_tier_map(),
    ),
}
_vault = Vault(VaultCipher(settings.vault_encryption_key))
_oauth_verifiers: dict[AuthProvider, IdentityVerifier] = {
    AuthProvider.GOOGLE: GoogleVerifier(settings.google_oauth_client_id),
    AuthProvider.APPLE: AppleVerifier(settings.apple_oauth_client_id),
}

_content_session_factory = make_content_session_factory(settings.database_url)

# Calendar assembly — uses an in-memory panchang cache backed by the real engine
# (Redis + Postgres are wired in staging/prod via infrastructure config).
_panchang_cache = PanchangCache(
    compute=compute_panchang,
    hot_store=InMemoryCacheStore(),
    durable_store=InMemoryPanchangDayStore(),
)
_festival_rules = [DIWALI, HOLI, RAKSHA_BANDHAN]
_calendar_service = CalendarService(_panchang_cache, _festival_rules)


async def _provide_user_service() -> AsyncGenerator[UserService, None]:
    async with _session_factory() as session:
        yield UserService(
            session,
            secret_key=settings.secret_key,
            vault=_vault,
            oauth_verifiers=_oauth_verifiers,
        )
        await session.commit()


async def _provide_content_service() -> AsyncGenerator[ContentService, None]:
    async with _content_session_factory() as session:
        yield ContentService(session)
        await session.commit()


async def _provide_subscription_service() -> AsyncGenerator[SubscriptionService, None]:
    async with _session_factory() as session:
        yield SubscriptionService(session, _receipt_verifiers)
        await session.commit()


def _provide_calendar_service() -> CalendarService:
    return _calendar_service


def _provide_secret_key() -> str:
    return settings.secret_key


app = FastAPI(
    title="The Pandit API",
    version="0.1.0",
    description=(
        "Versioned REST/JSON gateway for The Pandit platform. "
        "Clients (web, iOS, Android) call this service exclusively — "
        "domain services are never exposed directly."
    ),
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.dependency_overrides[get_user_service] = _provide_user_service
app.dependency_overrides[get_secret_key] = _provide_secret_key
app.dependency_overrides[get_content_service] = _provide_content_service
app.dependency_overrides[get_calendar_service] = _provide_calendar_service
app.dependency_overrides[get_subscription_service] = _provide_subscription_service
app.include_router(users_router)
app.include_router(content_router)
app.include_router(calendar_router)
app.include_router(subscriptions_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],  # tighten in staging/prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is alive."""
    return {"status": "ok", "environment": settings.environment}
