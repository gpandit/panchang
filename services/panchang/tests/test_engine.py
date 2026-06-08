"""Tests for the Swiss Ephemeris engine (Step 0.2).

Verifies:
  - pyswisseph imports successfully
  - The ephemeris data path resolves to an existing directory
  - A known date returns a plausible Sun longitude
"""

import os

import pytest


def test_swisseph_importable() -> None:
    import swisseph as swe  # noqa: F401 — import is the assertion


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
