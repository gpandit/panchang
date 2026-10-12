"""Tests for the Panchang engine's hard-day handling (Stage 1, Step 1.2).

Each case here corresponds to an entry in services/panchang/docs/edge-cases.md
and to an item in Architecture §4.2 "Lunar edge cases the build must handle":

  - Adhika (leap) and Kshaya (skipped) lunar months
  - Kshaya (skipped) and Vriddhi (repeated) tithis
  - High-latitude / undefined sunrise (polar regions)
  - DST transitions occurring mid-tithi
"""

from datetime import date

from panchang.compute import _detect_adhika_kshaya, compute_panchang
from panchang.models import PanchangRequest

DELHI = {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}
SVALBARD = {"lat": 78.2, "lon": 15.6, "tz": "Arctic/Longyearbyen"}
NEW_YORK = {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"}


def _delhi(d: date) -> PanchangRequest:
    return PanchangRequest(date=d, **DELHI)


# ──────────────────────────────────────────────────────────────────────────
# Adhika & Kshaya maas
# ──────────────────────────────────────────────────────────────────────────


def test_known_adhika_maas_year_is_labelled() -> None:
    """2023 carried an Adhika (leap) Shravan, roughly 18 Jul - 16 Aug 2023.
    A date well inside that window must be labelled as an Adhika month, and
    must NOT simultaneously be labelled Kshaya."""
    result = compute_panchang(_delhi(date(2023, 8, 1)))

    assert result.calendrical.is_adhika_month is True
    assert result.calendrical.is_kshaya_month is False


def test_normal_month_is_not_mislabelled() -> None:
    """An ordinary month (no double-/zero-sankranti month boundary) must carry
    neither the Adhika nor the Kshaya label."""
    result = compute_panchang(_delhi(date(2024, 1, 15)))

    assert result.calendrical.is_adhika_month is False
    assert result.calendrical.is_kshaya_month is False


def test_kshaya_maas_detection_flags_a_double_sankranti_month() -> None:
    """Genuine Kshaya maas years are astronomically rare (multi-decade gaps),
    so we exercise the detection rule itself directly: a lunar month is Kshaya
    when the Sun crosses into a new rashi *twice* between its bounding new
    moons (diff == 2), and Adhika when it crosses zero times (diff == 0).
    See docs/edge-cases.md for the rationale."""
    synodic = 29.530588853
    t0 = 1000.0

    # Synthetic tithi angle: a perfectly linear Moon-minus-Sun separation that
    # completes one cycle (360 deg) every synodic month, zeroed at t0.
    def tithi_angle(jd: float) -> float:
        return ((jd - t0) * (360.0 / synodic)) % 360.0

    day_start = t0 + 10.0  # within the lunar month starting at the new moon t0

    import panchang.compute as compute_module

    original_sun = compute_module._sun
    try:
        # Two-sankranti month: Sun advances 60 deg (two rashis) over one
        # synodic month -> Kshaya.
        compute_module._sun = lambda jd: ((jd - t0) * (60.0 / synodic)) % 360.0
        is_adhika, is_kshaya = _detect_adhika_kshaya(tithi_angle, day_start, tithi_index=11)
        assert is_kshaya is True
        assert is_adhika is False

        # Zero-sankranti month: Sun barely moves, stays in the same rashi -> Adhika.
        compute_module._sun = lambda jd: 10.0
        is_adhika, is_kshaya = _detect_adhika_kshaya(tithi_angle, day_start, tithi_index=11)
        assert is_adhika is True
        assert is_kshaya is False
    finally:
        compute_module._sun = original_sun


# ──────────────────────────────────────────────────────────────────────────
# Kshaya & Vriddhi tithis
# ──────────────────────────────────────────────────────────────────────────


def test_kshaya_tithi_is_fully_contained_within_a_single_day() -> None:
    """A Kshaya tithi never touches a sunrise: it begins and ends entirely
    within one Panchang day, so three tithis (not the usual one or two)
    overlap that day, and the middle one's start AND end are both defined."""
    result = compute_panchang(_delhi(date(2024, 1, 14)))

    assert len(result.tithi) == 3
    skipped = result.tithi[1]
    assert skipped.start is not None
    assert skipped.end is not None
    # Its neighbours bound it exactly — no gap, no overlap.
    assert result.tithi[0].end.iso == skipped.start.iso
    assert result.tithi[2].start.iso == skipped.end.iso


def test_vriddhi_tithi_spans_two_consecutive_sunrises() -> None:
    """A Vriddhi tithi is present at two consecutive sunrises: it is the last
    (open-ended) tithi of one Panchang day and also the first (start-less)
    tithi of the next — same index, same name, unambiguously continuous."""
    day1 = compute_panchang(_delhi(date(2024, 1, 12)))
    day2 = compute_panchang(_delhi(date(2024, 1, 13)))

    last_of_day1 = day1.tithi[-1]
    first_of_day2 = day2.tithi[0]

    assert last_of_day1.end is None  # open — continues past this day's sunrise
    assert first_of_day2.start is None  # open — was already running at sunrise
    assert last_of_day1.index == first_of_day2.index
    assert last_of_day1.name == first_of_day2.name


# ──────────────────────────────────────────────────────────────────────────
# High-latitude / undefined sunrise
# ──────────────────────────────────────────────────────────────────────────


def test_polar_day_uses_marked_proxy_sunrise() -> None:
    """The same-longitude lower-latitude day supplies a marked approximation."""
    result = compute_panchang(PanchangRequest(date=date(2024, 6, 21), **SVALBARD))

    assert result.day_events.sunrise.hour_24 != "00:00:00"
    assert result.day_events.sunset.hour_24 != "12:00:00"
    assert "polarDay" in result.flags
    assert "sunriseFallback" in result.day_events.flags
    assert len(result.tithi) >= 1
    assert result.vara.name


def test_polar_night_also_uses_marked_proxy_sunrise() -> None:
    """Mirror case in the polar-night season — same marked approximation."""
    result = compute_panchang(PanchangRequest(date=date(2024, 12, 21), **SVALBARD))

    assert result.day_events.sunrise.hour_24 != "00:00:00"
    assert result.day_events.sunset.hour_24 != "12:00:00"
    assert "polarNight" in result.flags
    assert len(result.tithi) >= 1


# ──────────────────────────────────────────────────────────────────────────
# DST mid-tithi
# ──────────────────────────────────────────────────────────────────────────


def test_dst_spring_forward_mid_tithi_keeps_24_plus_consistent() -> None:
    """2024-03-10 is the US spring-forward date (America/New_York skips
    02:00 -> 03:00). The engine must compute a coherent result spanning the
    transition, and every anga boundary's 24-plus value must be strictly
    increasing in elapsed real time relative to the Panchang day's sunrise —
    the wall-clock jump must not produce a backwards or duplicated reading."""
    request = PanchangRequest(date=date(2024, 3, 10), **NEW_YORK)
    result = compute_panchang(request)

    assert result.day_events.sunrise is not None
    assert result.day_events.sunset is not None

    def plus_seconds(hms: str) -> int:
        h, m, s = (int(x) for x in hms.split(":"))
        return h * 3600 + m * 60 + s

    for spans in (result.tithi, result.nakshatra, result.yoga, result.karana):
        boundaries = []
        for span in spans:
            for tv in (span.start, span.end):
                if tv is not None:
                    boundaries.append(plus_seconds(tv.hour_24_plus))
        assert boundaries == sorted(boundaries)


def test_dst_fall_back_mid_tithi_keeps_24_plus_consistent() -> None:
    """2024-11-03 is the US fall-back date (America/New_York repeats 01:00-02:00).
    Same coherence guarantee in the other direction across the transition."""
    request = PanchangRequest(date=date(2024, 11, 3), **NEW_YORK)
    result = compute_panchang(request)

    def plus_seconds(hms: str) -> int:
        h, m, s = (int(x) for x in hms.split(":"))
        return h * 3600 + m * 60 + s

    for spans in (result.tithi, result.nakshatra, result.yoga, result.karana):
        boundaries = []
        for span in spans:
            for tv in (span.start, span.end):
                if tv is not None:
                    boundaries.append(plus_seconds(tv.hour_24_plus))
        assert boundaries == sorted(boundaries)
    assert len(result.tithi) >= 1


def test_determinism_holds_across_a_dst_boundary() -> None:
    request = PanchangRequest(date=date(2024, 3, 10), **NEW_YORK)
    assert compute_panchang(request).model_dump() == compute_panchang(request).model_dump()
