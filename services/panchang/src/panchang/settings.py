"""Panchang service settings — loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PANCHANG_",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    environment: str = "development"

    # ── Ephemeris ─────────────────────────────────────────────────────────────
    # Path to the Swiss Ephemeris data files (libs/ephemeris).
    # Must be set to an absolute path in staging/production.
    ephemeris_path: str = "../../libs/ephemeris"

    # Default Ayanamsa (can be overridden per-request).
    # See pyswisseph constants: SE_SIDM_LAHIRI = 1
    default_ayanamsa: str = "lahiri"

    # ── Licence gate ──────────────────────────────────────────────────────────
    # Values: "agpl" (dev/test only) | "commercial" (required for public launch)
    # See docs/licensing/swiss-ephemeris.md and tools/check_launch_readiness.py.
    ephemeris_license: str = "agpl"

    # ── Build profile ─────────────────────────────────────────────────────────
    # Values: "development" | "staging" | "production"
    # Production builds are blocked by CI when ephemeris_license != "commercial".
    build_profile: str = "development"

    # ── Cache ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 86_400  # 24 h — Panchang doesn't change once computed


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance (lazy-init)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
