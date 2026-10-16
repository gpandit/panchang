"""Panchang service settings — loaded from environment / .env file."""

from pydantic import field_validator
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
    database_url: str = "postgresql+psycopg://pandit:pandit@localhost:5432/pandit_dev"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 86_400  # 24 h — Panchang doesn't change once computed
    cache_grid_degrees: float = 0.1

    @field_validator("cache_grid_degrees")
    @classmethod
    def validate_grid(cls, value: float) -> float:
        from panchang.cache import _validate_grid

        return _validate_grid(value)

    # JSON array of seed locations for the worker; observed locations are
    # supplied by the deployment's aggregated usage repository.
    warm_locations_json: str = "[]"
    warm_top_locations: int = 500

    # Versioned editorial rule export.  Production should point this at the
    # reviewed CMS artifact rather than relying on the repository fallback.
    festival_rules_path: str = ""


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance (lazy-init)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
