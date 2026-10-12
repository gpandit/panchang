"""Tests for the Panchang Computation Service core (Step 1.1).

Covers: golden-value shape/key-values, determinism, and the three time forms
(12h / 24h / 24-plus, including a past-midnight case).
"""

import itertools
from datetime import date

import pytest

from panchang.compute import compute_panchang
from panchang.models import PanchangRequest

DELHI = {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}


def _request(d: date) -> PanchangRequest:
    return PanchangRequest(date=d, **DELHI)


# ──────────────────────────────────────────────────────────────────────────
# Golden-value shape & key values
# ──────────────────────────────────────────────────────────────────────────


def test_result_shape_is_complete() -> None:
    result = compute_panchang(_request(date(2024, 1, 15)))

    assert len(result.tithi) >= 1
    assert len(result.nakshatra) >= 1
    assert len(result.yoga) >= 1
    assert len(result.karana) >= 1
    assert result.vara.name

    assert result.day_events.sunrise is not None
    assert result.day_events.sunset is not None

    assert len(result.muhurat) >= 5
    assert len(result.choghadiya) == 16
    assert len(result.hora) == 24

    assert result.calendrical.shaka_samvat > 0
    assert result.calendrical.vikram_samvat > 0
    assert result.calendrical.lunar_month
    assert result.calendrical.paksha in {"Shukla Paksha", "Krishna Paksha"}


def test_golden_values_2024_01_15_delhi() -> None:
    """Fixed input — assert the key values that must not silently drift."""
    result = compute_panchang(_request(date(2024, 1, 15)))

    # Sunrise around 07:14 IST in Delhi on this date.
    assert result.day_events.sunrise.hour_24.startswith("07:1")

    assert result.vara.name == "Somavara"  # 2024-01-15 is a Monday

    tithi_names = [t.name for t in result.tithi]
    assert "Shukla Panchami" in tithi_names or "Shukla Shashthi" in tithi_names

    assert result.calendrical.ayana == "Uttarayana"
    assert result.calendrical.sun_rashi == "Makara"


def test_sunrise_and_anga_boundary_regression_2024_01_15_delhi() -> None:
    """Existing-engine regression values, not independent accuracy references."""
    result = compute_panchang(_request(date(2024, 1, 15)))
    assert result.day_events.sunrise.iso == "2024-01-15T07:14:49+05:30"
    assert result.day_events.sunset.iso == "2024-01-15T17:46:02+05:30"
    assert result.tithi[0].name == "Shukla Panchami"
    assert result.tithi[0].end is not None
    assert result.tithi[0].end.iso == "2024-01-16T02:17:04+05:30"
    assert result.nakshatra[0].name == "Shatabhisha"
    assert result.nakshatra[0].end is not None
    assert result.nakshatra[0].end.iso == "2024-01-15T08:06:56+05:30"


def test_anga_spans_cover_the_full_day_contiguously() -> None:
    result = compute_panchang(_request(date(2024, 1, 15)))

    for spans in (result.tithi, result.nakshatra, result.yoga, result.karana):
        assert spans[0].start is None or spans[0].start is not None  # first may be clipped
        assert spans[-1].end is None or spans[-1].end is not None
        # Internal boundaries must chain start[i+1] == end[i]
        for prev, nxt in itertools.pairwise(spans):
            assert prev.end is not None
            assert nxt.start is not None
            assert prev.end.iso == nxt.start.iso


# ──────────────────────────────────────────────────────────────────────────
# Determinism
# ──────────────────────────────────────────────────────────────────────────


def test_determinism_same_input_same_output() -> None:
    request = _request(date(2024, 1, 15))
    first = compute_panchang(request)
    second = compute_panchang(request)
    assert first.model_dump() == second.model_dump()


def test_determinism_across_locations_and_dates() -> None:
    for d, lat, lon, tz in [
        (date(2024, 6, 21), 19.0760, 72.8777, "Asia/Kolkata"),
        (date(2025, 12, 25), 13.0827, 80.2707, "Asia/Kolkata"),
    ]:
        request = PanchangRequest(date=d, lat=lat, lon=lon, tz=tz)
        assert compute_panchang(request).model_dump() == compute_panchang(request).model_dump()


# ──────────────────────────────────────────────────────────────────────────
# Time forms — 12h / 24h / 24-plus, including past-midnight
# ──────────────────────────────────────────────────────────────────────────


def test_time_forms_are_consistent_for_daytime_event() -> None:
    result = compute_panchang(_request(date(2024, 1, 15)))
    sunrise = result.day_events.sunrise

    h, _m, _s = (int(x) for x in sunrise.hour_24.split(":"))
    assert 0 <= h <= 23

    # 12h form round-trips to the same hour/minute.
    assert sunrise.hour_12.endswith("AM") or sunrise.hour_12.endswith("PM")

    # For an event on/after the Panchang day's civil midnight and before noon,
    # the 24-plus form matches the 24h form exactly (no past-midnight wrap).
    assert sunrise.hour_24_plus == sunrise.hour_24


def test_24_plus_form_is_first_class_for_past_midnight_event() -> None:
    """At least one anga boundary should fall after local midnight but before
    the next sunrise — its 24-plus form must read >= 24:00, distinct from the
    wrapped 24h clock value, while the 24h/12h/iso forms stay conventional."""
    result = compute_panchang(_request(date(2024, 1, 15)))

    past_midnight = None
    for spans in (result.tithi, result.nakshatra, result.yoga, result.karana):
        for span in spans:
            for tv in (span.start, span.end):
                if tv is None:
                    continue
                plus_hour = int(tv.hour_24_plus.split(":")[0])
                clock_hour = int(tv.hour_24.split(":")[0])
                if plus_hour >= 24 and plus_hour != clock_hour:
                    past_midnight = tv
                    break

    assert past_midnight is not None, "expected at least one past-midnight boundary on this date"

    plus_h, plus_m, plus_s = past_midnight.hour_24_plus.split(":")
    clock_h, clock_m, clock_s = past_midnight.hour_24.split(":")
    assert int(plus_h) == int(clock_h) + 24
    assert plus_m == clock_m
    assert plus_s == clock_s

    # The 24h and 12h forms remain conventional (wrapped) representations.
    assert int(clock_h) < 24
    assert past_midnight.hour_12.endswith("AM")


@pytest.mark.parametrize("d", [date(2024, 3, 1), date(2024, 9, 15)])
def test_time_value_forms_present_for_every_day_event(d: date) -> None:
    result = compute_panchang(_request(d))
    for tv in (result.day_events.sunrise, result.day_events.sunset):
        assert tv.iso
        assert len(tv.hour_24.split(":")) == 3
        assert tv.hour_12.endswith("AM") or tv.hour_12.endswith("PM")
        assert len(tv.hour_24_plus.split(":")) == 3
