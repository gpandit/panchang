"""Tests for the Swiss Ephemeris engine (Step 0.2).

Verifies:
  - the engine exposes named solar/lunar event and longitude operations
  - The ephemeris data path resolves to an existing directory
  - A known date returns a plausible Sun longitude
"""

import os

import pytest

from panchang import engine


def test_ephemeris_path_exists() -> None:
    from panchang.settings import get_settings

    s = get_settings()
    # The default "../../libs/ephemeris" is relative to the service root.
    # Resolve it from the actual service directory (two dirs up from this test file).
    service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resolved = os.path.normpath(os.path.join(service_dir, s.ephemeris_path))

    assert os.path.isdir(resolved), (
        f"Ephemeris directory not found at {resolved!r}. "
        "Run tests from the repo root or set PANCHANG_EPHEMERIS_PATH to an absolute path."
    )


@pytest.mark.parametrize(
    "year,month,day,expected_min,expected_max,description",
    [
        # J2000.0 — Sun near 280° (tropical Capricorn)
        (2000, 1, 1, 278.0, 282.0, "J2000.0 reference epoch"),
        # Summer solstice 2024 — Sun near 90° (tropical Cancer)
        (2024, 6, 21, 88.0, 92.0, "2024 summer solstice"),
        # Vernal equinox 2024 — Sun near 0° (tropical Aries); use 0±2° range
        (2024, 3, 20, 0.0, 2.0, "2024 vernal equinox"),
    ],
)
def test_sun_longitude_plausible(
    year: int,
    month: int,
    day: int,
    expected_min: float,
    expected_max: float,
    description: str,
) -> None:
    from panchang.engine import get_planet_longitude, julday

    jd = julday(year, month, day, 12.0)
    lon = get_planet_longitude(jd) % 360
    assert expected_min <= lon <= expected_max, (
        f"{description}: Sun longitude {lon:.4f}° not in [{expected_min}, {expected_max}]"
    )


def test_named_longitudes_and_julian_calendar_round_trip() -> None:
    jd = engine.julday(2024, 1, 15, 12.0)
    assert engine.revjul(jd) == (2024, 1, 15, 12.0)
    engine.set_ayanamsa("lahiri")
    assert 0 <= engine.sidereal_sun_longitude(jd) < 360
    assert 0 <= engine.sidereal_moon_longitude(jd) < 360
    assert engine.sidereal_sun_longitude(jd) == engine.sidereal_longitude(jd)
    assert engine.sidereal_moon_longitude(jd) != engine.sidereal_sun_longitude(jd)


def test_named_events_return_ut_julian_days_in_expected_order() -> None:
    jd = engine.julday(2024, 1, 15, 0.0)
    lon, lat = 77.2090, 28.6139
    sunrise = engine.sun_rise(jd, lon, lat)
    assert sunrise is not None
    sunset = engine.sun_set(sunrise, lon, lat)
    next_sunrise = engine.sun_rise(sunrise + 0.2, lon, lat)
    assert sunset is not None and next_sunrise is not None
    assert sunrise < sunset < next_sunrise
    moonrise = engine.moon_rise(sunrise, lon, lat)
    moonset = engine.moon_set(sunrise, lon, lat)
    assert moonrise is not None and moonset is not None
    assert sunrise < moonrise < sunset < moonset < next_sunrise


def test_named_events_preserve_no_event_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "rise_trans", lambda *args: None)
    for event in (engine.sun_rise, engine.sun_set, engine.moon_rise, engine.moon_set):
        assert event(2460324.5, 15.6, 78.2) is None
