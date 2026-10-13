"""Queue-agnostic cache warming worker and scheduling contract.

The deployment scheduler publishes a dated job through its RQ/outbox adapter;
the worker resolves locations and cache dependencies in its own process. No
process-local state is assumed to survive between runs.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from panchang.cache import LOCATION_GRID_DEGREES, _validate_grid, cache_key_for
from panchang.models import Ayanamsa, MonthScheme, PanchangRequest
from panchang.warming import DEFAULT_HORIZON_MONTHS, PopularLocation, _add_months

if TYPE_CHECKING:
    from panchang.settings import Settings


@dataclass(frozen=True)
class ObservedLocation:
    """Aggregated request volume from a trusted analytics/repository adapter."""

    location: PopularLocation
    request_count: int


class LocationSource(Protocol):
    def locations(self) -> Iterable[PopularLocation]: ...


class WarmJobPublisher(Protocol):
    """Implement with an outbox transaction or an RQ publisher at deployment."""

    def publish(self, *, start: date, dedupe_key: str) -> None: ...


class WarmCache(Protocol):
    def get(self, request: PanchangRequest) -> object: ...


def publish_warm_job(publisher: WarmJobPublisher, *, start: date) -> str:
    """A scheduler calls this once per local calendar day; publisher owns deduplication."""
    key = f"panchang.warm.v1:{start.isoformat()}"
    publisher.publish(start=start, dedupe_key=key)
    return key


def _location_key(location: PopularLocation, grid_degrees: float) -> tuple[float, float, str]:
    request = PanchangRequest(
        date=date(2000, 1, 1), lat=location.lat, lon=location.lon, tz=location.tz
    )
    key = cache_key_for(request, grid_degrees=grid_degrees)
    return key.lat_grid, key.lon_grid, location.tz


def _validate_location(location: PopularLocation) -> None:
    if not location.name.strip():
        raise ValueError("location name is required")
    if (
        isinstance(location.lat, bool)
        or isinstance(location.lon, bool)
        or not isinstance(location.lat, (float, int))
        or not isinstance(location.lon, (float, int))
        or not (-90 <= location.lat <= 90 and -180 <= location.lon <= 180)
    ):
        raise ValueError("location coordinates out of bounds")
    try:
        ZoneInfo(location.tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("location timezone must be IANA") from exc


class PopularLocations:
    """Configured seed cities plus a ranked observation snapshot.

    Observed rows can be supplied from request metrics or a user-location
    aggregation. The adapter must aggregate counts outside this worker; no
    individual user coordinates or identifiers are persisted in the job.
    """

    def __init__(
        self,
        configured: Iterable[PopularLocation],
        observed: Callable[[], Iterable[ObservedLocation]],
        *,
        top_n: int = 500,
        grid_degrees: float = LOCATION_GRID_DEGREES,
    ) -> None:
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
            raise ValueError("top_n must be a positive integer")
        self._configured = tuple(configured)
        self._observed = observed
        self._top_n = top_n
        self._grid_degrees = _validate_grid(grid_degrees)

    def locations(self) -> tuple[PopularLocation, ...]:
        rows = tuple(self._observed())
        if any(
            isinstance(row.request_count, bool)
            or not isinstance(row.request_count, int)
            or row.request_count < 0
            for row in rows
        ):
            raise ValueError("observed request counts must be non-negative")
        ranked = sorted(
            rows,
            key=lambda row: (
                -row.request_count,
                row.location.tz,
                row.location.lat,
                row.location.lon,
                row.location.name,
            ),
        )
        deduped: dict[tuple[float, float, str], PopularLocation] = {}
        for location in self._configured:
            _validate_location(location)
            deduped.setdefault(_location_key(location, self._grid_degrees), location)
        observed_keys: set[tuple[float, float, str]] = set()
        for row in ranked:
            location = row.location
            _validate_location(location)
            key = _location_key(location, self._grid_degrees)
            if key in observed_keys:
                continue
            if len(observed_keys) == self._top_n:
                break
            observed_keys.add(key)
            deduped.setdefault(key, location)
        return tuple(deduped.values())


def location_source_from_settings(
    settings: Settings, observed: Callable[[], Iterable[ObservedLocation]]
) -> PopularLocations:
    """Build a source from worker settings and an aggregated-usage adapter."""
    return PopularLocations(
        configured_locations(settings.warm_locations_json),
        observed,
        top_n=settings.warm_top_locations,
        grid_degrees=settings.cache_grid_degrees,
    )


def configured_locations(raw_json: str) -> tuple[PopularLocation, ...]:
    """Parse PANCHANG_WARM_LOCATIONS_JSON; malformed configuration fails closed."""
    data = json.loads(raw_json)
    if not isinstance(data, list):
        raise ValueError("warm locations must be a JSON array")
    locations = []
    for item in data:
        if not isinstance(item, dict) or set(item) != {"name", "lat", "lon", "tz"}:
            raise ValueError("each warm location requires name, lat, lon and tz")
        if not isinstance(item["name"], str) or not isinstance(item["tz"], str):
            raise ValueError("location name and tz must be strings")
        location = PopularLocation(**item)
        _validate_location(location)
        locations.append(location)
    return tuple(locations)


@dataclass(frozen=True)
class WarmFailure:
    day: date
    location: PopularLocation
    scheme: MonthScheme
    attempts: int
    error_type: str


@dataclass(frozen=True)
class WarmReport:
    start: date
    end_exclusive: date
    locations: int
    succeeded: int
    failures: tuple[WarmFailure, ...]

    @property
    def failed(self) -> int:
        return len(self.failures)


def run_warm_job(
    cache: WarmCache,
    source: LocationSource,
    *,
    start: date,
    horizon_months: int = DEFAULT_HORIZON_MONTHS,
    max_attempts: int = 3,
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI,
) -> WarmReport:
    """Warm [start, start + calendar months) for both schemes, reporting every failure.

    Retries are immediate, bounded and deterministic. Unresolved failures are
    reported to the invoking worker, which must record/alert or requeue them.
    Source failures are fatal so a missing location snapshot is never a success.
    """
    if (
        isinstance(horizon_months, bool)
        or not isinstance(horizon_months, int)
        or horizon_months < 15
    ):
        raise ValueError("horizon_months must be at least 15")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    locations = tuple(source.locations())
    if not locations:
        raise ValueError("warm job has no configured or observed locations")
    for location in locations:
        _validate_location(location)
    end = _add_months(start, horizon_months)
    failures: list[WarmFailure] = []
    succeeded = 0
    for offset in range((end - start).days):
        day = start + timedelta(days=offset)
        for location in locations:
            for scheme in MonthScheme:
                request = PanchangRequest(
                    date=day,
                    lat=location.lat,
                    lon=location.lon,
                    tz=location.tz,
                    ayanamsa=ayanamsa,
                    month_scheme=scheme,
                )
                for attempt in range(1, max_attempts + 1):
                    try:
                        cache.get(request)
                    except Exception as exc:
                        if attempt == max_attempts:
                            failures.append(
                                WarmFailure(day, location, scheme, attempt, type(exc).__name__)
                            )
                    else:
                        succeeded += 1
                        break
    return WarmReport(start, end, len(locations), succeeded, tuple(failures))
