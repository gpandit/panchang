"""FastAPI application entry point for the API Gateway."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.settings import get_settings
from api.content.db import make_session_factory as make_content_session_factory
from api.content.router import get_content_service, router as content_router
from api.content.service import ContentService
from api.users.db import make_session_factory
from api.users.encryption import VaultCipher
from api.users.oauth import AppleVerifier, GoogleVerifier
from api.users.router import get_secret_key, get_user_service, router as users_router
from api.users.models import AuthProvider
from api.users.service import UserService
from api.users.vault import Vault

settings = get_settings()

_session_factory = make_session_factory(settings.database_url)
_vault = Vault(VaultCipher(settings.vault_encryption_key))
_oauth_verifiers = {
    AuthProvider.GOOGLE: GoogleVerifier(settings.google_oauth_client_id),
    AuthProvider.APPLE: AppleVerifier(settings.apple_oauth_client_id),
}

_content_session_factory = make_content_session_factory(settings.database_url)


async def _provide_user_service() -> UserService:
    async with _session_factory() as session:
        yield UserService(
            session,
            secret_key=settings.secret_key,
            vault=_vault,
            oauth_verifiers=_oauth_verifiers,
        )
        await session.commit()


async def _provide_content_service() -> ContentService:
    async with _content_session_factory() as session:
        yield ContentService(session)
        await session.commit()


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
app.include_router(users_router)
app.include_router(content_router)

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
