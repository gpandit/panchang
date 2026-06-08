"""FastAPI application entry point for the API Gateway."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.settings import get_settings

settings = get_settings()

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
