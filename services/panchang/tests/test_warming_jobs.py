"""Worker behavior at the calendar, location selection and failure boundaries."""

from datetime import date

import pytest

from panchang.models import MonthScheme
from panchang.settings import Settings
from panchang.warming import PopularLocation
from panchang.warming_jobs import (
    ObservedLocation,
    PopularLocations,
    configured_locations,
    location_source_from_settings,
    publish_warm_job,
    run_warm_job,
)

DELHI = PopularLocation("Delhi", 28.6139, 77.209, "Asia/Kolkata")
NEAR_DELHI = PopularLocation("Nearby", 28.615, 77.21, "Asia/Kolkata")
LONDON = PopularLocation("London", 51.507, -0.128, "Europe/London")


class RecordingCache:
    def __init__(self, fail=None):
        self.requests = []
        self.fail = fail

    def get(self, request):
        self.requests.append(request)
        if self.fail is not None:
            self.fail(request)


def test_locations_merge_configured_and_ranked_observed_with_grid_deduplication():
    source = PopularLocations(
        [DELHI],
        lambda: [ObservedLocation(LONDON, 30), ObservedLocation(NEAR_DELHI, 40)],
        top_n=2,
    )
    assert source.locations() == (DELHI, LONDON)
    assert PopularLocations(
        [], lambda: [ObservedLocation(LONDON, 30), ObservedLocation(DELHI, 40)], top_n=1
    ).locations() == (DELHI,)


def test_worker_settings_wire_configured_and_observed_sources():
    settings = Settings(
        _env_file=None,
        warm_locations_json='[{"name":"Delhi","lat":28.6139,"lon":77.209,"tz":"Asia/Kolkata"}]',
        warm_top_locations=1,
        cache_grid_degrees=0.01,
    )
    source = location_source_from_settings(
        settings, lambda: [ObservedLocation(NEAR_DELHI, 10), ObservedLocation(LONDON, 5)]
    )
    assert source.locations() == (DELHI, NEAR_DELHI)


def test_duplicate_observed_grid_does_not_consume_top_n_slot():
    source = PopularLocations(
        [],
        lambda: [
            ObservedLocation(DELHI, 40),
            ObservedLocation(NEAR_DELHI, 30),
            ObservedLocation(LONDON, 20),
        ],
        top_n=2,
    )
    assert source.locations() == (DELHI, LONDON)


def test_worker_covers_fifteen_calendar_months_and_both_schemes():
    cache = RecordingCache()
    source = PopularLocations([DELHI], lambda: ())
    report = run_warm_job(cache, source, start=date(2024, 1, 31))
    assert report.end_exclusive == date(2025, 4, 30)
    assert report.succeeded == 455 * 2
    assert report.failed == 0
    assert cache.requests[0].date == date(2024, 1, 31)
    assert cache.requests[-1].date == date(2025, 4, 29)
    assert {req.month_scheme for req in cache.requests} == set(MonthScheme)


def test_retry_exhaustion_reports_precise_failed_requests_and_continues():
    def fail(request):
        if request.month_scheme == MonthScheme.PURNIMANTA:
            raise RuntimeError("private backend detail")

    cache = RecordingCache(fail)
    report = run_warm_job(
        cache, PopularLocations([DELHI], lambda: ()), start=date(2024, 1, 1), max_attempts=2
    )
    assert report.succeeded == 456
    assert report.failed == 456
    assert report.failures[0].day == date(2024, 1, 1)
    assert report.failures[0].scheme == MonthScheme.PURNIMANTA
    assert report.failures[0].attempts == 2
    assert report.failures[0].error_type == "RuntimeError"
    assert "private backend detail" not in repr(report)


def test_transient_failure_retries_then_succeeds():
    attempts = 0

    def fail_once(request):
        nonlocal attempts
        if request.date == date(2024, 1, 1) and request.month_scheme == MonthScheme.AMANTA:
            attempts += 1
            if attempts == 1:
                raise RuntimeError("transient")

    report = run_warm_job(
        RecordingCache(fail_once),
        PopularLocations([DELHI], lambda: ()),
        start=date(2024, 1, 1),
        max_attempts=2,
    )
    assert attempts == 2
    assert report.failed == 0


def test_empty_source_and_invalid_config_fail_before_computation():
    with pytest.raises(ValueError, match="no configured or observed"):
        run_warm_job(RecordingCache(), PopularLocations([], lambda: ()), start=date(2024, 1, 1))
    with pytest.raises(ValueError, match="timezone"):
        configured_locations('[{"name":"Bad","lat":1,"lon":2,"tz":"Bad/Zone"}]')
    assert (
        configured_locations('[{"name":"Delhi","lat":28.6,"lon":77.2,"tz":"Asia/Kolkata"}]')[0].tz
        == "Asia/Kolkata"
    )


def test_scheduler_publishes_stable_dedupe_identity():
    class Publisher:
        def __init__(self):
            self.calls = []

        def publish(self, *, start, dedupe_key):
            self.calls.append((start, dedupe_key))

    publisher = Publisher()
    key = publish_warm_job(publisher, start=date(2024, 2, 1))
    assert key == "panchang.warm.v1:2024-02-01"
    assert publisher.calls == [(date(2024, 2, 1), key)]
