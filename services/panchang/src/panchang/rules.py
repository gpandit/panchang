"""Versioned, persistence-independent festival rules over computed PCS days.

The bundled catalog is draft editorial data. Public callers must use the default
published-only resolver; an editor can opt into previewing unpublished rules.
Adjacent PCS days are required for two-day tie-breaks and never synthesized here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Protocol, cast

from panchang import engine
from panchang.constants import LUNAR_MONTH_NAMES_AMANTA, NAKSHATRA_NAMES
from panchang.models import PanchangResult
from panchang.settings import get_settings

RuleType = Literal["lunar", "solar", "nakshatra_in_solar_month", "recurring"]
MONTHS = tuple(name.lower() for name in LUNAR_MONTH_NAMES_AMANTA)
RASHIS = (
    "mesha",
    "vrishabha",
    "mithuna",
    "karka",
    "simha",
    "kanya",
    "tula",
    "vrishchika",
    "dhanu",
    "makara",
    "kumbha",
    "meena",
)
ANCHORS = {
    "sunrise",
    "arunodaya",
    "pratahkala",
    "purvahna",
    "madhyahna",
    "aparahna",
    "sunset",
    "pradosh",
    "nishita",
    "moonrise",
    "sankranti",
    "sandhi",
}
TIE_BREAKS = {
    "udaya_tithi",
    "udaya_tithi_skip_if_kshaya_at_sunrise",
    "udaya_tithi_prefer_hasta",
    "tithi_at_anchor_else_next_day",
    "tithi_at_anchor_else_prev_day",
    "tithi_at_anchor_else_prev_day_if_more",
    "tithi_at_anchor_strict",
    "tithi_at_anchor_avoid_bhadra",
    "tithi_at_moonrise_else_next_day",
    "nakshatra_at_sunrise_else_greater_portion",
    "ekadashi_smarta_vaishnava",
    "ekadashi_vaishnava",
    "vaishnava_udaya_prefer_rohini",
    "sankranti_punya_kala",
}
STATES = {"draft", "in_review", "published", "archived"}
OVERRIDE_FIELDS = {
    "region",
    "name",
    "scheme",
    "month",
    "paksha",
    "tithi",
    "rashi",
    "nakshatra",
    "preferNakshatra",
    "anchor",
    "tieBreak",
    "notes",
    "deity",
}
RULE_FIELDS = {
    "id",
    "name",
    "type",
    "anchor",
    "tieBreak",
    "regions",
    "priority",
    "scheme",
    "month",
    "paksha",
    "tithi",
    "rashi",
    "nakshatra",
    "cycle",
    "aliases",
    "overrides",
    "duration_days",
    "preferNakshatra",
    "deity",
    "notes",
}
RULE_ID = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class FestivalRule:
    id: str
    name: str
    type: RuleType
    anchor: str
    tie_break: str
    regions: tuple[str, ...]
    priority: int
    scheme: str | None = None
    month: str | None = None
    paksha: str | None = None
    tithi: int | None = None
    rashi: str | None = None
    nakshatra: str | None = None
    cycle: str | None = None
    aliases: Mapping[str, str] | None = None
    overrides: tuple[Mapping[str, Any], ...] = ()
    duration_days: int | None = None
    prefer_nakshatra: str | None = None

    @classmethod
    def from_mapping(cls, value: object, path: str) -> FestivalRule:
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected an object")
        unknown = value.keys() - RULE_FIELDS
        if unknown:
            raise ValueError(f"{path}: unsupported keys {sorted(unknown)}")

        def text(
            key: str, *, required: bool = False, allowed: set[str] | tuple[str, ...] | None = None
        ) -> str | None:
            raw = value.get(key)
            if raw is None and not required:
                return None
            if (
                not isinstance(raw, str)
                or not raw.strip()
                or (allowed is not None and raw not in allowed)
            ):
                raise ValueError(f"{path}.{key}: invalid value {raw!r}")
            return raw.strip()

        kind = text(
            "type",
            required=True,
            allowed={"lunar", "solar", "nakshatra_in_solar_month", "recurring"},
        )
        anchor = text("anchor", required=True, allowed=ANCHORS)
        tie = text("tieBreak", required=True, allowed=TIE_BREAKS)
        regions = value.get("regions")
        if (
            not isinstance(regions, list)
            or not regions
            or not all(isinstance(r, str) and r.strip() for r in regions)
        ):
            raise ValueError(f"{path}.regions: expected a non-empty string array")
        priority = value.get("priority")
        if type(priority) is not int or not 0 <= priority <= 100:
            raise ValueError(f"{path}.priority: expected integer in [0, 100]")
        tithi = value.get("tithi")
        if tithi is not None and (type(tithi) is not int or not 1 <= tithi <= 30):
            raise ValueError(f"{path}.tithi: expected integer in [1, 30]")
        duration = value.get("duration_days")
        if duration is not None and (type(duration) is not int or duration < 1):
            raise ValueError(f"{path}.duration_days: expected positive integer")
        aliases = value.get("aliases", {})
        if not isinstance(aliases, dict) or not all(
            isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
            for k, v in aliases.items()
        ):
            raise ValueError(f"{path}.aliases: expected a string-to-string object")
        overrides = value.get("overrides", [])
        if not isinstance(overrides, list) or not all(
            isinstance(o, dict) and isinstance(o.get("region"), str) and o["region"].strip()
            for o in overrides
        ):
            raise ValueError(f"{path}.overrides: expected objects with region")
        for index, override in enumerate(overrides):
            unknown = override.keys() - OVERRIDE_FIELDS
            if unknown:
                raise ValueError(f"{path}.overrides[{index}]: unsupported keys {sorted(unknown)}")
            for key in (
                "scheme",
                "month",
                "paksha",
                "rashi",
                "anchor",
                "tieBreak",
                "nakshatra",
                "preferNakshatra",
                "name",
            ):
                if key in override:
                    allowed = (
                        {"amanta", "purnimanta"}
                        if key == "scheme"
                        else MONTHS
                        if key == "month"
                        else {"shukla", "krishna", "both"}
                        if key == "paksha"
                        else RASHIS
                        if key == "rashi"
                        else ANCHORS
                        if key == "anchor"
                        else TIE_BREAKS
                        if key == "tieBreak"
                        else None
                    )
                    if (
                        not isinstance(override[key], str)
                        or not override[key].strip()
                        or (allowed is not None and override[key] not in allowed)
                    ):
                        raise ValueError(f"{path}.overrides[{index}].{key}: invalid value")
            if "tithi" in override and (
                type(override["tithi"]) is not int or not 1 <= override["tithi"] <= 30
            ):
                raise ValueError(f"{path}.overrides[{index}].tithi: expected integer in [1, 30]")
        cycle = text("cycle", allowed={"tithi", "solar_ingress"})
        month = text("month", allowed=MONTHS)
        rashi = text("rashi", allowed=RASHIS)
        nakshatra = text("nakshatra", allowed=tuple(n.lower() for n in NAKSHATRA_NAMES))
        if (
            (kind == "solar" and rashi is None)
            or (kind == "nakshatra_in_solar_month" and (rashi is None or nakshatra is None))
            or (kind == "recurring" and cycle not in {"tithi", "solar_ingress"})
            or (kind == "lunar" and tithi is None)
            or (kind == "recurring" and cycle == "tithi" and tithi is None)
        ):
            raise ValueError(f"{path}: missing criteria for {kind}")
        identifier = cast(str, text("id", required=True))
        if not RULE_ID.fullmatch(identifier):
            raise ValueError(
                f"{path}.id: must contain only lowercase letters, digits and underscores"
            )
        return cls(
            id=identifier,
            name=cast(str, text("name", required=True)),
            type=cast(RuleType, kind),
            anchor=cast(str, anchor),
            tie_break=cast(str, tie),
            regions=tuple(r.strip() for r in regions),
            priority=priority,
            scheme=text("scheme", allowed={"amanta", "purnimanta"}),
            month=month,
            paksha=text("paksha", allowed={"shukla", "krishna", "both"}),
            tithi=tithi,
            rashi=rashi,
            nakshatra=nakshatra,
            cycle=cycle,
            aliases=MappingProxyType(dict(aliases)),
            overrides=tuple(MappingProxyType(dict(o)) for o in overrides),
            duration_days=duration,
            prefer_nakshatra=text(
                "preferNakshatra", allowed=tuple(n.lower() for n in NAKSHATRA_NAMES)
            ),
        )


@dataclass(frozen=True)
class RuleCatalog:
    version: str
    review_state: str
    source: str
    rules: tuple[FestivalRule, ...]
    path: Path

    @classmethod
    def load(cls, path: str | Path | None = None) -> RuleCatalog:
        selected = _default_rules_path() if path is None else Path(path)
        try:
            payload = json.loads(selected.read_text(encoding="utf-8"))
        except OSError as exc:
            raise FileNotFoundError(f"festival rule catalog not found: {selected}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"festival rule catalog is not valid JSON: {selected}") from exc
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("version"), str)
            or not payload["version"].strip()
        ):
            raise ValueError("festival rule catalog requires a version")
        state = payload.get("reviewState", "draft")
        if state not in STATES:
            raise ValueError("festival rule catalog has invalid reviewState")
        source = payload.get("source", "")
        if not isinstance(source, str):
            raise ValueError("festival rule catalog source must be a string")
        rules = tuple(
            FestivalRule.from_mapping(item, f"rules[{i}]")
            for i, item in enumerate(
                [
                    *_as_list(payload.get("rules"), "rules"),
                    *_as_list(payload.get("recurringCycles"), "recurringCycles"),
                ]
            )
        )
        if len({rule.id for rule in rules}) != len(rules):
            raise ValueError("festival rule catalog contains duplicate rule ids")
        return cls(payload["version"].strip(), state, source, rules, selected)


@dataclass(frozen=True)
class FestivalOccurrence:
    rule_id: str
    name: str
    date: date
    region: str
    priority: int
    rule_version: str
    flags: tuple[str, ...] = ()
    location_grid: str = ""
    year: int = 0
    anchor_utc: datetime | None = None
    explanation: str = ""


class OccurrenceStore(Protocol):
    """Persistence adapter contract; implementations must upsert on the full key.

    Corrections retain old versions for audit, then invalidate derived caches for
    the previous version. This contract does not imply a CMS or database adapter.
    """

    def upsert(self, occurrences: Sequence[FestivalOccurrence]) -> None: ...

    def list_for_year(
        self, year: int, location_grid: str, region: str, rule_version: str
    ) -> Sequence[FestivalOccurrence]: ...

    def invalidate_version(self, rule_version: str, location_grid: str) -> None: ...


def resolve_festivals(
    result: PanchangResult,
    catalog: RuleCatalog,
    *,
    region: str = "default",
    include_unpublished: bool = False,
    location_grid: str = "",
) -> list[FestivalOccurrence]:
    """Single-day preview. For adjacent-day decisions use resolve_festival_range.

    A one-day input cannot establish a tie-break; only a completed singleton
    tithi/ingress whose relevant neighbor is present should be published.
    """
    return resolve_festival_range(
        [result],
        catalog,
        region=region,
        include_unpublished=include_unpublished,
        location_grid=location_grid,
    )


def resolve_festival_range(
    days: Sequence[PanchangResult],
    catalog: RuleCatalog,
    *,
    region: str = "default",
    year: int | None = None,
    month: int | None = None,
    start: date | None = None,
    end: date | None = None,
    location_grid: str = "",
    include_unpublished: bool = False,
) -> list[FestivalOccurrence]:
    """Resolve candidate spans on consecutive PCS days and filter *after* tie-break.

    Supply a one-day halo outside a requested date/year window for boundary
    decisions. Missing neighboring days never cause a fabricated date.
    """
    if not region.strip():
        raise ValueError("region must not be empty")
    if year is not None and (type(year) is not int or not 1 <= year <= 9999):
        raise ValueError("year must be a valid Gregorian year")
    if month is not None and (type(month) is not int or not 1 <= month <= 12):
        raise ValueError("month must be in [1, 12]")
    if start is not None and end is not None and end < start:
        raise ValueError("end precedes start")
    if not days or (catalog.review_state != "published" and not include_unpublished):
        return []
    ordered = sorted(days, key=lambda d: d.request.date)
    identity = (
        ordered[0].request.lat,
        ordered[0].request.lon,
        ordered[0].request.tz,
        ordered[0].request.ayanamsa,
    )
    if any(
        (d.request.lat, d.request.lon, d.request.tz, d.request.ayanamsa) != identity
        or d.request.date != ordered[0].request.date + timedelta(days=i)
        for i, d in enumerate(ordered)
    ):
        raise ValueError("PCS days must be consecutive at the same location and ayanamsa")
    occurrences: list[FestivalOccurrence] = []
    for base in catalog.rules:
        rule = _regional_rule(base, region)
        if rule is None:
            continue
        if rule.type == "solar" or (rule.type == "recurring" and rule.cycle == "solar_ingress"):
            choices = _solar_choices(rule, ordered)
        elif rule.type == "nakshatra_in_solar_month":
            choices = _nakshatra_choices(rule, ordered)
        else:
            choices = _lunar_choices(rule, ordered)
        for chosen, anchor, explanation, flags in choices:
            day = chosen.request.date
            if (
                (year is not None and day.year != year)
                or (month is not None and day.month != month)
                or (start is not None and day < start)
                or (end is not None and day > end)
            ):
                continue
            occurrences.append(
                FestivalOccurrence(
                    rule_id=rule.id,
                    name=rule.name,
                    date=day,
                    region=region,
                    priority=rule.priority,
                    rule_version=catalog.version,
                    flags=flags,
                    location_grid=location_grid,
                    year=day.year,
                    anchor_utc=anchor,
                    explanation=explanation,
                )
            )
    return sorted(occurrences, key=lambda o: (o.date, -o.priority, o.rule_id, o.region))


def _regional_rule(rule: FestivalRule, region: str) -> FestivalRule | None:
    overrides = [o for o in rule.overrides if o["region"] == region]
    if len(overrides) > 1:
        raise ValueError(f"duplicate regional override for {rule.id}: {region}")
    if (
        region not in rule.regions
        and "default" not in rule.regions
        and not overrides
        and (rule.aliases is None or region not in rule.aliases)
    ):
        return None
    if not overrides:
        return replace(rule, name=(rule.aliases or {}).get(region, rule.name))
    override = overrides[0]
    fields = {
        "name": "name",
        "scheme": "scheme",
        "month": "month",
        "paksha": "paksha",
        "tithi": "tithi",
        "rashi": "rashi",
        "nakshatra": "nakshatra",
        "preferNakshatra": "prefer_nakshatra",
        "anchor": "anchor",
        "tieBreak": "tie_break",
    }
    update = {field: override[key] for key, field in fields.items() if key in override}
    update.setdefault("name", (rule.aliases or {}).get(region, rule.name))
    return replace(rule, **update)


def _month_matches(rule: FestivalRule, day: PanchangResult, paksha: str) -> bool:
    if rule.month is None:
        return True
    if day.calendrical.is_adhika_month and rule.type != "recurring":
        return False
    month = day.calendrical.lunar_month.lower()
    if month not in MONTHS:
        return False
    scheme = rule.scheme or day.request.month_scheme.value
    if scheme != day.request.month_scheme.value and paksha == "krishna":
        shift = 1 if scheme == "purnimanta" else -1
        month = MONTHS[(MONTHS.index(month) + shift) % 12]
    return month == rule.month


def _lunar_choices(
    rule: FestivalRule, days: Sequence[PanchangResult]
) -> list[tuple[PanchangResult, datetime, str, tuple[str, ...]]]:
    # One event per actual tithi span, not one event per day; this collapses
    # vriddhi at two sunrises and admits kshaya between two sunrises.
    spans: dict[tuple[int, datetime, datetime], list[PanchangResult]] = {}
    for day in days:
        for span in day.tithi:
            paksha = "shukla" if span.index <= 15 else "krishna"
            ordinal = span.index if paksha == "shukla" else span.index - 15
            if (
                rule.tithi not in (span.index, ordinal)
                or rule.paksha not in (None, "both", paksha)
                or not _month_matches(rule, day, paksha)
            ):
                continue
            spans.setdefault((span.index, span.start_utc, span.end_utc), []).append(day)
    output: list[tuple[PanchangResult, datetime, str, tuple[str, ...]]] = []
    for (_, begin, finish), candidates in sorted(spans.items(), key=lambda pair: pair[0][1]):
        # If a span already prevailed at the first supplied sunrise, an
        # unobserved previous sunrise may be its true vriddhi selection.
        if len(days) > 1 and begin < days[0].vara.start_utc and candidates[0] is days[0]:
            continue
        choice = _choose_lunar(rule, days, candidates, begin, finish)
        if choice is not None:
            day, anchor, why = choice
            flags = tuple(
                flag
                for flag, present in (
                    ("adhika", day.calendrical.is_adhika_month),
                    ("kshayaMaas", day.calendrical.is_kshaya_month),
                    (
                        "kshayaTithi",
                        not any(begin <= d.vara.start_utc < finish for d in candidates),
                    ),
                    (
                        "vriddhiTithi",
                        sum(begin <= d.vara.start_utc < finish for d in candidates) > 1,
                    ),
                )
                if present
            )
            output.append((day, anchor, why, flags))
    return output


def _instant(day: PanchangResult, anchor: str) -> tuple[datetime, datetime] | None:
    sunrise = day.vara.start_utc
    sunset = datetime.fromisoformat(day.day_events.sunset.iso).astimezone(UTC)
    day_length = sunset - sunrise
    if anchor == "sunrise":
        return sunrise, sunrise
    if anchor == "arunodaya":
        value = sunrise - timedelta(minutes=96)
        return value, value
    if anchor in {"pratahkala", "purvahna", "madhyahna", "aparahna"}:
        index = ("pratahkala", "purvahna", "madhyahna", "aparahna").index(anchor)
        return sunrise + day_length * index / 5, sunrise + day_length * (index + 1) / 5
    if anchor == "sunset":
        return sunset, sunset
    if anchor == "pradosh":
        return sunset, sunset + timedelta(minutes=96)
    if anchor == "nishita":
        period = next(p for p in day.muhurat if p.name == "Nishita Muhurat")
        return period.start_utc, period.end_utc
    if anchor == "moonrise" and day.day_events.moonrise is not None:
        moment = datetime.fromisoformat(day.day_events.moonrise.iso).astimezone(UTC)
        return moment, moment
    return None


def _overlap(begin: datetime, finish: datetime, window: tuple[datetime, datetime]) -> float:
    return max(0.0, (min(finish, window[1]) - max(begin, window[0])).total_seconds())


def _covers(begin: datetime, finish: datetime, instant: datetime) -> bool:
    return begin <= instant < finish


def _choose_lunar(
    rule: FestivalRule,
    all_days: Sequence[PanchangResult],
    candidates: Sequence[PanchangResult],
    begin: datetime,
    finish: datetime,
) -> tuple[PanchangResult, datetime, str] | None:
    tie = rule.tie_break
    if rule.anchor == "sandhi":
        if rule.tithi not in (8, 23):
            return None
        # Sandhi is the end of Ashtami; Navami follows immediately.
        day = next((d for d in candidates if d.vara.start_utc <= finish < d.vara.end_utc), None)
        return (day, finish, "Ashtami-Navami sandhi boundary") if day else None
    sunrise_days = [d for d in candidates if _covers(begin, finish, d.vara.start_utc)]
    if (
        tie.startswith("udaya_tithi")
        or tie.startswith("ekadashi_")
        or tie == "vaishnava_udaya_prefer_rohini"
    ):
        if (
            tie in {"udaya_tithi_prefer_hasta", "vaishnava_udaya_prefer_rohini"}
            and len(sunrise_days) > 1
        ):
            preferred = rule.prefer_nakshatra or (
                "hasta" if tie == "udaya_tithi_prefer_hasta" else "rohini"
            )
            sunrise_days = sorted(
                sunrise_days,
                key=lambda d: (
                    not any(
                        s.name.lower() == preferred
                        and _covers(s.start_utc, s.end_utc, d.vara.start_utc)
                        for s in d.nakshatra
                    ),
                    d.request.date,
                ),
            )
        if tie.startswith("ekadashi_"):
            clean = [
                d
                for d in sunrise_days
                if _covers(begin, finish, d.vara.start_utc - timedelta(minutes=96))
            ]
            if not clean and sunrise_days:
                following = next(
                    (
                        d
                        for d in all_days
                        if d.request.date == sunrise_days[0].request.date + timedelta(days=1)
                    ),
                    None,
                )
                return (
                    (following, following.vara.start_utc, f"{tie}: arunodaya viddha; deferred fast")
                    if following
                    else None
                )
            sunrise_days = clean
        if sunrise_days:
            chosen = sunrise_days[0]
            return chosen, chosen.vara.start_utc, f"{tie}: tithi at sunrise"
        if tie.startswith("ekadashi_"):
            return None
        chosen = candidates[0]
        return chosen, begin, f"{tie}: kshaya tithi after sunrise"
    scored = []
    for day in candidates:
        window = _instant(day, rule.anchor)
        if window is None:
            continue
        anchor = window[0] + (window[1] - window[0]) / 2
        covers = _covers(begin, finish, anchor)
        overlap = _overlap(begin, finish, window)
        if tie == "tithi_at_anchor_avoid_bhadra":
            free = _bhadra_free_overlap(day, begin, finish, window)
            if free == 0:
                continue
            overlap = free
            covers = covers and not any(
                k.name.lower() in {"vishti", "bhadra"} and _covers(k.start_utc, k.end_utc, anchor)
                for k in day.karana
            )
        scored.append((day, anchor, covers, overlap))
    if tie == "tithi_at_anchor_strict" and not any(c for _, _, c, _ in scored):
        return (
            (
                sunrise_days[0],
                sunrise_days[0].vara.start_utc,
                "strict anchor absent; sunrise fallback",
            )
            if sunrise_days
            else None
        )
    if not scored:
        return None
    if tie == "tithi_at_anchor_strict":
        scored = [item for item in scored if item[2]]
    # Exact anchor wins; then the specified direction or the greater portion.
    if tie in {
        "tithi_at_anchor_else_next_day",
        "tithi_at_moonrise_else_next_day",
        "tithi_at_anchor_else_prev_day",
    }:
        scored.sort(
            key=lambda item: (
                -int(item[2]),
                -item[3] if not any(x[2] for x in scored) else 0,
                item[0].request.date,
            )
        )
    elif tie == "tithi_at_anchor_else_prev_day_if_more" or tie == "tithi_at_anchor_avoid_bhadra":
        scored.sort(key=lambda item: (-int(item[2]), -item[3], item[0].request.date))
    else:
        scored.sort(key=lambda item: (-int(item[2]), item[0].request.date))
    chosen, anchor, covers, overlap = scored[0]
    if not covers and overlap == 0:
        return None
    return chosen, anchor, f"{tie}: {'exact anchor' if covers else 'anchor-window overlap'}"


def _bhadra_free_overlap(
    day: PanchangResult, begin: datetime, finish: datetime, window: tuple[datetime, datetime]
) -> float:
    start, end = max(begin, window[0]), min(finish, window[1])
    if start >= end:
        return 0.0
    blocked = sum(
        _overlap(start, end, (k.start_utc, k.end_utc))
        for k in day.karana
        if k.name.lower() in {"vishti", "bhadra"}
    )
    return max(0.0, (end - start).total_seconds() - blocked)


def _solar_choices(
    rule: FestivalRule, days: Sequence[PanchangResult]
) -> list[tuple[PanchangResult, datetime, str, tuple[str, ...]]]:
    output: list[tuple[PanchangResult, datetime, str, tuple[str, ...]]] = []
    engine.set_ayanamsa(days[0].request.ayanamsa.value)
    targets = range(12) if rule.rashi is None else [RASHIS.index(rule.rashi)]
    for i, day in enumerate(days):
        begin, finish = day.vara.start_utc, day.vara.end_utc
        jd_begin, jd_end = _jd(begin), _jd(finish)
        longitude = day.sun_longitude % 360
        travelled = (engine.sidereal_sun_longitude(jd_end) - longitude) % 360
        for index in targets:
            distance = (index * 30 - longitude) % 360
            if not 0 < distance < travelled:
                continue
            lo, hi = jd_begin, jd_end
            for _ in range(45):
                mid = (lo + hi) / 2
                if (engine.sidereal_sun_longitude(mid) - longitude) % 360 < distance:
                    lo = mid
                else:
                    hi = mid
            instant = begin + (finish - begin) * ((lo + hi) / 2 - jd_begin) / (jd_end - jd_begin)
            sunset = datetime.fromisoformat(day.day_events.sunset.iso).astimezone(UTC)
            chosen = (
                days[i + 1]
                if instant >= sunset and i + 1 < len(days)
                else day
                if instant < sunset
                else None
            )
            if chosen:
                output.append(
                    (
                        chosen,
                        instant,
                        "solar ingress; after-sunset ingress observes next day"
                        if chosen is not day
                        else "solar ingress before sunset",
                        (),
                    )
                )
    return output


def _nakshatra_choices(
    rule: FestivalRule, days: Sequence[PanchangResult]
) -> list[tuple[PanchangResult, datetime, str, tuple[str, ...]]]:
    output: list[tuple[PanchangResult, datetime, str, tuple[str, ...]]] = []
    seen: set[tuple[datetime, datetime]] = set()
    for day in days:
        if day.calendrical.sun_rashi.lower() != rule.rashi:
            continue
        for span in day.nakshatra:
            if span.name.lower() != rule.nakshatra or (span.start_utc, span.end_utc) in seen:
                continue
            seen.add((span.start_utc, span.end_utc))
            eligible = [
                d
                for d in days
                if d.calendrical.sun_rashi.lower() == rule.rashi
                and span.start_utc < d.vara.end_utc
                and span.end_utc > d.vara.start_utc
            ]
            at_sunrise = [
                d for d in eligible if _covers(span.start_utc, span.end_utc, d.vara.start_utc)
            ]
            if at_sunrise:
                chosen = at_sunrise[0]
                reason = "nakshatra at sunrise"
            elif eligible:
                chosen = max(
                    eligible,
                    key=lambda d: (
                        _overlap(
                            span.start_utc,
                            span.end_utc,
                            (
                                d.vara.start_utc,
                                datetime.fromisoformat(d.day_events.sunset.iso).astimezone(UTC),
                            ),
                        ),
                        -d.request.date.toordinal(),
                    ),
                )
                reason = "greater daytime nakshatra portion"
            else:
                continue
            output.append((chosen, chosen.vara.start_utc, reason, ()))
    return output


def _jd(value: datetime) -> float:
    value = value.astimezone(UTC)
    return engine.julday(
        value.year,
        value.month,
        value.day,
        value.hour + value.minute / 60 + (value.second + value.microsecond / 1_000_000) / 3600,
    )


def _as_list(value: object, name: str) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"festival rule catalog {name} must be an array")
    return value


def _default_rules_path() -> Path:
    configured = get_settings().festival_rules_path.strip()
    if configured:
        return Path(configured).expanduser()
    repo_path = (
        Path(__file__).resolve().parents[4] / "docs/architecture/the-pandit-festival-rules-v1.json"
    )
    return (
        repo_path
        if repo_path.exists()
        else Path.cwd() / "docs/architecture/the-pandit-festival-rules-v1.json"
    )
