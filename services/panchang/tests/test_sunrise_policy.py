"""The proxy interval is explicitly approximate and stays on the correct local day."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from panchang import engine
from panchang.app import app
from panchang.compute import compute_panchang
from panchang.models import PanchangRequest, PanchangResult
from panchang.sunrise_policy import POLICY, SunriseFallbackError, sunrise_interval
from panchang.timeforms import jd_to_local_datetime


@pytest.mark.parametrize(
    ("day", "lat", "lon", "tz", "season"),
    [
        (date(2024, 6, 21), 78.2, 15.6, "Arctic/Longyearbyen", "polarDay"),
        (date(2024, 12, 21), 78.2, 15.6, "Arctic/Longyearbyen", "polarNight"),
        (date(2024, 6, 21), -78.2, 15.6, "Europe/Oslo", "polarNight"),
        (date(2024, 12, 21), -78.2, 15.6, "Europe/Oslo", "polarDay"),
        (date(2024, 3, 10), 89.0, -74.0, "America/New_York", "polarNight"),
        (date(2024, 11, 3), -89.0, -74.0, "America/New_York", "polarDay"),
        (date(2024, 10, 6), -89.0, 166.0, "Antarctica/McMurdo", "polarDay"),
    ],
)
def test_nearest_valid_latitude_preserves_local_day_and_utc_identity(
    day: date, lat: float, lon: float, tz: str, season: str
) -> None:
    rise, set_, next_rise, flags = sunrise_interval(day, lon, lat, tz)
    assert flags == ["sunriseFallback", POLICY, season]
    assert rise < set_ < next_rise
    assert [jd_to_local_datetime(jd, tz).date() for jd in (rise, set_, next_rise)] == [
        day,
        day,
        day + timedelta(days=1),
    ]
    # The selected proxy is the first valid inward 1-degree candidate; the
    # same longitude, timezone and date are kept throughout the search.
    for step in range(1, 91):
        candidate = (1 if lat >= 0 else -1) * max(0.0, abs(lat) - step)
        candidate_rise, candidate_set, candidate_next, candidate_flags = sunrise_interval(
            day, lon, candidate, tz
        )
        if candidate_flags == []:
            assert (candidate_rise, candidate_set, candidate_next) == (rise, set_, next_rise)
            break
    else:
        pytest.fail("proxy does not correspond to any inward latitude")

    result = compute_panchang(PanchangRequest(date=day, lat=lat, lon=lon, tz=tz))
    assert result.flags == flags == result.day_events.flags
    assert all("sunriseFallback" in window.flags for window in result.hora)
    sunrise_utc = datetime.fromisoformat(result.day_events.sunrise.iso).astimezone(UTC)
    assert result.vara.start_utc == sunrise_utc
    assert all(
        window.hours_from_sunrise
        == pytest.approx((window.end_utc - sunrise_utc).total_seconds() / 3600)
        for window in result.hora
    )
    assert PanchangResult.model_validate(result.model_dump(mode="json", by_alias=True)) == result


@pytest.mark.parametrize("day", [date(2024, 3, 9), date(2024, 11, 2)])
def test_proxy_intervals_cross_dst_as_utc_instants(day: date) -> None:
    result = compute_panchang(PanchangRequest(date=day, lat=89, lon=-74, tz="America/New_York"))
    assert "sunriseFallback" in result.flags
    assert any(
        datetime.fromisoformat(window.start.iso).utcoffset()
        != datetime.fromisoformat(window.end.iso).utcoffset()
        for window in result.hora
    )
    assert all(window.end_utc > window.start_utc for window in result.hora)


def test_normal_sunrise_is_not_marked_as_proxy() -> None:
    result = compute_panchang(
        PanchangRequest(date=date(2024, 6, 21), lat=28.6, lon=77.2, tz="Asia/Kolkata")
    )
    assert result.flags == result.day_events.flags == []


def test_impossible_skipped_civil_date_returns_structured_failure() -> None:
    request = PanchangRequest(date=date(2011, 12, 30), lat=-13.8, lon=-171.8, tz="Pacific/Apia")
    with pytest.raises(SunriseFallbackError) as captured:
        compute_panchang(request)
    assert captured.value.reason == "impossibleLocalDate"
    response = TestClient(app).post("/compute", json=request.model_dump(mode="json"))
    assert response.status_code == 422
    assert response.json() == {"reason": "impossibleLocalDate", "flags": captured.value.flags}


def test_last_supported_civil_date_fails_explicitly() -> None:
    with pytest.raises(SunriseFallbackError, match="impossibleLocalDate"):
        sunrise_interval(date.max, 0, 0, "UTC")


def test_unavailable_reference_latitude_fails_closed_with_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "sun_rise", lambda *_args: None)
    with pytest.raises(SunriseFallbackError) as captured:
        sunrise_interval(date(2024, 6, 21), 15.6, 78.2, "Arctic/Longyearbyen")
    assert captured.value.reason == "noValidLatitude"
    assert captured.value.flags == [
        "sunriseFallback",
        "sunriseFallbackUnavailable",
        "noValidLatitude",
    ]
