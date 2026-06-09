"""API gateway settings — loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="API_",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: str = "development"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://pandit:pandit@localhost:5432/pandit_dev"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Object Storage (S3-compatible / MinIO in dev) ─────────────────────────
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "pandit-dev"

    # ── Auth ──────────────────────────────────────────────────────────────────
    # IMPORTANT: set a strong random value in staging/prod via the managed secret store.
    secret_key: str = "change-me-in-production-use-managed-secret-store"
    jwt_algorithm: str = "HS256"
    # Access token lifetime in seconds (15 min default)
    access_token_expire_seconds: int = 900

    # ── Rate limiting ─────────────────────────────────────────────────────────
    # Requests per minute per authenticated user (or per IP for anonymous)
    rate_limit_per_minute: int = 60
    # Stricter limit for expensive endpoints (PDF jobs, calendar month)
    rate_limit_burst_per_minute: int = 10

    # ── Edge / in-process cache ────────────────────────────────────────────────
    # TTL in seconds for the daily Panchang in-process cache (mirrors CDN TTL)
    panchang_cache_ttl_seconds: int = 3600  # 1 hour
    # Max items in the in-process LRU cache
    panchang_cache_max_size: int = 1024

    # ── Downstream services ───────────────────────────────────────────────────
    panchang_service_url: str = "http://localhost:8001"
    # Timeout for downstream Panchang service calls (seconds)
    panchang_service_timeout: float = 1.5


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance (lazy-init)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
