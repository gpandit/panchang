"""Swiss Ephemeris engine — the single point of contact with pyswisseph.

Only this module (and tests that import it) may call swisseph directly.
All other panchang code must go through functions defined here.
"""

import os

import swisseph as swe

from panchang.settings import get_settings

_initialized = False

_AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
}


def _init() -> None:
    global _initialized
    if _initialized:
        return
    settings = get_settings()
    ephe_path = os.path.abspath(settings.ephemeris_path)
    swe.set_ephe_path(ephe_path)
    _initialized = True


def set_ayanamsa(ayanamsa: str = "lahiri") -> None:
    """Select the sidereal mode used by sidereal_longitude()."""
    _init()
    swe.set_sid_mode(_AYANAMSA_MODES[ayanamsa.lower()], 0, 0)


def get_ayanamsa_value(jd_ut: float) -> float:
    """Return the ayanamsa offset (degrees) at *jd_ut* for the active sidereal mode."""
    _init()
    return float(swe.get_ayanamsa_ut(jd_ut))


def get_planet_longitude(jd_ut: float, planet: int = swe.SUN) -> float:
    """Return the *tropical* ecliptic longitude of *planet* at Julian Day *jd_ut* (UT)."""
    _init()
    result, _ = swe.calc_ut(jd_ut, planet)
    return float(result[0])


def sidereal_longitude(jd_ut: float, planet: int = swe.SUN) -> float:
    """Return the sidereal ecliptic longitude of *planet*, using the ayanamsa
    selected by the most recent set_ayanamsa() call."""
    _init()
    result, _ = swe.calc_ut(jd_ut, planet, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return float(result[0]) % 360.0


def julday(year: int, month: int, day: int, hour: float = 12.0) -> float:
    """Thin wrapper around swe.julday for calendar → JD conversion."""
    _init()
    return swe.julday(year, month, day, hour)


def revjul(jd_ut: float) -> tuple[int, int, int, float]:
    """Thin wrapper around swe.revjul (JD → calendar date/time, UT)."""
    _init()
    return swe.revjul(jd_ut)


def rise_trans(jd_ut_start: float, planet: int, lon: float, lat: float, rsmi: int) -> float | None:
    """Find the next rising/setting/transit of *planet* at/after *jd_ut_start*.

    rsmi: one of swe.CALC_RISE, swe.CALC_SET, swe.CALC_MTRANSIT, swe.CALC_ITRANSIT.

    Returns the event's Julian Day (UT), or None if it cannot be found
    (e.g. circumpolar location/date).
    """
    _init()
    ret, tret = swe.rise_trans(jd_ut_start, planet, rsmi, (lon, lat, 0.0), flags=swe.FLG_SWIEPH)
    if ret != 0:
        return None
    return float(tret[0])
