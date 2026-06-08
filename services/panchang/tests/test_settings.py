"""Smoke tests for the Panchang service settings loader."""

from panchang.settings import get_settings


def test_settings_load_with_defaults() -> None:
    """Settings must load without errors using dev defaults."""
    s = get_settings()
    assert s.environment in {"development", "staging", "production"}
    assert s.port > 0
    assert s.default_ayanamsa == "lahiri"


def test_settings_ephemeris_path_is_set() -> None:
    """Ephemeris path must be configured (Step 0.2 will point it at real data)."""
    s = get_settings()
    assert s.ephemeris_path != ""
