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
    # See CONTRIBUTING.md §4 for the secrets management strategy.
    secret_key: str = "change-me-in-production-use-managed-secret-store"

    # ── Downstream services ───────────────────────────────────────────────────
    panchang_service_url: str = "http://localhost:8001"

    # ── Users module: vault encryption ────────────────────────────────────────
    # Fernet key protecting birth/family data at rest. MUST come from the
    # managed secret store in staging/prod — never commit a real value.
    # Generate one with `VaultCipher.generate_key()`.
    vault_encryption_key: str = "x6n6F8h6genBJ8qfWZHlA0sX2DhniGtY1k1MfRwGVC0="

    # ── Users module: OAuth client ids (set via secret store) ────────────────
    google_oauth_client_id: str = ""
    apple_oauth_client_id: str = ""

    # ── Subscriptions: Apple IAP (set via secret store) ───────────────────────
    apple_iap_shared_secret: str = ""
    apple_iap_bundle_id: str = "com.pandit.app"
    apple_iap_sandbox: bool = True  # flip to False in production

    # ── Subscriptions: Google Play (set via secret store) ─────────────────────
    google_play_package_name: str = "com.pandit.app"
    # Service account JSON key path or inline JSON — loaded from secret store
    google_play_service_account_json: str = ""

    # ── Subscriptions: Stripe (set via secret store) ──────────────────────────
    stripe_secret_key: str = ""
    # Comma-separated "price_id:tier" pairs, e.g. "price_abc:silver,price_xyz:gold"
    stripe_price_tier_map: str = ""


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance (lazy-init)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
