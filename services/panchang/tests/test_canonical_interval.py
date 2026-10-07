"""Canonical instant identity survives display clipping, DST and JSON round trips."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from panchang import engine
from panchang.cache import ENGINE_VERSION, cache_key_for
from panchang.compute import compute_panchang
from panchang.models import CanonicalInterval, PanchangRequest, PanchangResult
from panchang.timeforms import to_time_value


def _compute(day: date, tz: str = "Asia/Kolkata") -> PanchangResult:
    lat, lon = (28.6139, 77.209) if tz == "Asia/Kolkata" else (40.7128, -74.006)
    return compute_panchang(PanchangRequest(date=day, lat=lat, lon=lon, tz=tz))


def test_interval_contract_invalidates_v1_pcs_cache_key() -> None:
    assert ENGINE_VERSION == "2"
    key = cache_key_for(
        PanchangRequest(date=date(2024, 1, 15), lat=28.6, lon=77.2, tz="Asia/Kolkata")
    )
    assert key.as_string().startswith("panchang:2:")


def test_all_intervals_have_valid_utc_identity_even_when_display_is_clipped() -> None:
    result = _compute(date(2024, 1, 15))
    sunrise = datetime.fromisoformat(result.day_events.sunrise.iso).astimezone(UTC)
    spans = [*result.tithi, *result.nakshatra, *result.yoga, *result.karana, result.vara]
    windows = [*result.muhurat, *result.choghadiya, *result.hora]
    assert spans[0].start is None
    assert "carriesOver" in spans[0].flags
    assert any(span.end is None and "carriesOver" in span.flags for span in spans)
    for interval in [*spans, *windows]:
        assert interval.start_utc.tzinfo == UTC
        assert interval.end_utc > interval.start_utc
        assert interval.hours_from_sunrise == pytest.approx(
            (interval.end_utc - sunrise).total_seconds() / 3600
        )
    assert any(window.hours_from_sunrise < 0 for window in windows)  # Brahma Muhurat
    assert any(span.hours_from_sunrise > 24 for span in spans)  # full span beyond day end
    assert any(span.end is not None and span.end.hour_24_plus.startswith("26:") for span in spans)
    payload = result.model_dump(mode="json", by_alias=True)
    assert "startUtc" in payload["tithi"][0]
    assert "start_utc" not in payload["tithi"][0]
    assert PanchangResult.model_validate(payload) == result


@pytest.mark.parametrize("day", [date(2024, 3, 9), date(2024, 11, 2)])
def test_dst_night_uses_instant_arithmetic_and_endpoint_offsets(day: date) -> None:
    result = _compute(day, "America/New_York")
    night = [window for window in result.hora if window.start.hour_24_plus >= "20:00:00"]
    assert night
    assert all(window.end_utc > window.start_utc for window in night)
    assert any(
        datetime.fromisoformat(window.start.iso).utcoffset()
        != datetime.fromisoformat(window.end.iso).utcoffset()
        for window in night
    )
    assert all(
        window.local_offset_minutes
        == int(datetime.fromisoformat(window.start.iso).utcoffset().total_seconds() / 60)
        for window in night
    )


def test_24_plus_display_does_not_move_backward_during_repeated_local_hour() -> None:
    tz = "America/New_York"
    sunrise = datetime.fromisoformat("2024-11-02T07:00:00-04:00")

    def jd(utc_hour: float) -> float:
        return engine.julday(2024, 11, 3, utc_hour)

    first = to_time_value(jd(5.75), tz, sunrise)  # 01:45 EDT
    second = to_time_value(jd(6.25), tz, sunrise)  # 01:15 EST
    assert first.hour_24 > second.hour_24  # civil clock repeats
    assert first.hour_24_plus < second.hour_24_plus  # elapsed instant display does not


def test_polar_placeholders_are_explicitly_marked_until_fallback_is_replaced() -> None:
    result = compute_panchang(
        PanchangRequest(date=date(2024, 6, 21), lat=78.2, lon=15.6, tz="Arctic/Longyearbyen")
    )
    assert "sunriseFallback" in result.flags
    assert "sunriseFallback" in result.day_events.flags
    assert all("sunriseFallback" in span.flags for span in result.tithi)


def test_kshaya_and_vriddhi_flags_follow_full_sunrise_boundaries() -> None:
    skipped = _compute(date(2024, 1, 14)).tithi[1]
    assert "kshaya" in skipped.flags
    assert skipped.start is not None and skipped.end is not None
    vriddhi = _compute(date(2024, 1, 29)).tithi[-1]
    assert "vriddhi" in vriddhi.flags
    assert vriddhi.end is None
    following = _compute(date(2024, 1, 30)).tithi[0]
    assert following.start_utc == vriddhi.start_utc
    assert "vriddhi" in following.flags


@pytest.mark.parametrize(
    "overrides",
    [
        {"endUtc": "2024-01-01T00:00:00Z"},
        {"startUtc": "2024-01-01T00:00:00"},
        {"localOffsetMinutes": 1500},
        {"hoursFromSunrise": float("nan")},
    ],
)
def test_invalid_intervals_are_rejected(overrides: dict[str, object]) -> None:
    fields: dict[str, object] = {
        "startUtc": "2024-01-01T00:00:00Z",
        "endUtc": "2024-01-02T00:00:00Z",
        "localOffsetMinutes": 330,
        "hoursFromSunrise": 24,
        "flags": [],
    }
    fields.update(overrides)
    with pytest.raises(ValidationError):
        CanonicalInterval.model_validate(fields)
