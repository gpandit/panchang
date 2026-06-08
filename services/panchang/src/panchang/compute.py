"""Pure orchestration: (date, lat, lon, tz, ayanamsa, scheme) -> PanchangResult.

This module contains no I/O, no caching, and reads no hidden clock — every
value is a deterministic function of the `PanchangRequest`. It is the only
writer of raw Panchang truth (per Architecture §2); cache (Step 1.4) wraps it.

NOTE: several calendrical fields (samvat epoch boundaries, lunar-month naming,
adhika/kshaya detection) use standard approximations. Final calibration against
a published reference Panchang is the explicit job of the accuracy harness
(Step 1.3) — this engine's structure and determinism are what Step 1.1 gates.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from panchang import constants as C
from panchang import engine
from panchang.models import (
    AngaSpan,
    Calendrical,
    Choghadiya,
    DayEvents,
    MuhuratPeriod,
    PanchangRequest,
    PanchangResult,
)
from panchang.timeforms import jd_to_local_datetime, to_time_value

_DEG = 360.0
_SYNODIC_MONTH = 29.530588853  # mean length of a lunar month, days


# ──────────────────────────────────────────────────────────────────────────
# Generic angle helpers & boundary root-finding
# ──────────────────────────────────────────────────────────────────────────

def _sun(jd: float) -> float:
    return engine.sidereal_longitude(jd, swe.SUN)


def _moon(jd: float) -> float:
    return engine.sidereal_longitude(jd, swe.MOON)


def _bisect_crossing(angle_fn, jd_lo: float, jd_hi: float, target_deg: float) -> float | None:
    """Find jd in [jd_lo, jd_hi] where angle_fn crosses *target_deg* (mod 360),
    assuming angle_fn is monotonically increasing (mod 360, no double-wrap)
    over the interval."""
    base = angle_fn(jd_lo) % _DEG
    target_rel = (target_deg - base) % _DEG

    def g(jd: float) -> float:
        return (angle_fn(jd) % _DEG - base) % _DEG

    g_hi = g(jd_hi)
    if target_rel == 0.0:
        return jd_lo
    if not (0.0 < target_rel <= g_hi):
        return None

    lo, hi = jd_lo, jd_hi
    for _ in range(80):
        mid = (lo + hi) / 2
        if g(mid) < target_rel:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _anga_spans(
    angle_fn,
    step_deg: float,
    name_fn,
    day_start: float,
    day_end: float,
    search_back: float,
    search_fwd: float,
    tv,
) -> list[AngaSpan]:
    """Enumerate every occurrence of this anga overlapping [day_start, day_end)."""
    angle_at_start = angle_fn(day_start) % _DEG
    cycle_index = int(angle_at_start // step_deg)

    # Start of the span containing day_start (search backward).
    start_target = (cycle_index * step_deg) % _DEG
    span_start = _bisect_crossing(angle_fn, day_start - search_back, day_start, start_target)
    if span_start is None:
        span_start = day_start - search_back  # degrade gracefully

    spans: list[AngaSpan] = []
    cur_index = cycle_index
    cur_start = span_start
    horizon = day_end + search_fwd

    while cur_start < day_end:
        end_target = ((cur_index + 1) * step_deg) % _DEG
        cur_end = _bisect_crossing(angle_fn, cur_start, horizon, end_target)
        if cur_end is None:
            cur_end = horizon

        index1 = cur_index + 1  # 1-based, within its 360°-cycle of `step_deg`
        spans.append(
            AngaSpan(
                index=index1,
                name=name_fn(cur_index),
                start=None if cur_start < day_start else tv(cur_start),
                end=None if cur_end > day_end else tv(cur_end),
            )
        )

        cur_start = cur_end
        cur_index += 1

    return spans


# ──────────────────────────────────────────────────────────────────────────
# Day events
# ──────────────────────────────────────────────────────────────────────────

def _find_event(jd_search_from: float, planet: int, rsmi: int, lat: float, lon: float) -> float | None:
    return engine.rise_trans(jd_search_from, planet, lon, lat, rsmi)


# ──────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────

def compute_panchang(request: PanchangRequest) -> PanchangResult:
    tz = ZoneInfo(request.tz)
    engine.set_ayanamsa(request.ayanamsa.value)

    # Local midnight at the start of the requested date -> UT Julian Day,
    # used purely as a search anchor for the sunrise that opens this Panchang day.
    local_midnight = datetime(request.date.year, request.date.month, request.date.day, 0, 0, 0, tzinfo=tz)
    midnight_utc = local_midnight.astimezone(ZoneInfo("UTC"))
    jd_midnight = engine.julday(
        midnight_utc.year, midnight_utc.month, midnight_utc.day,
        midnight_utc.hour + midnight_utc.minute / 60 + midnight_utc.second / 3600,
    )

    # Sunrise-to-sunrise day logic (Architecture §5).
    search_from = jd_midnight - 1.0
    sunrise = _find_event(search_from, swe.SUN, swe.CALC_RISE, request.lat, request.lon)
    if sunrise is None or sunrise < jd_midnight:
        sunrise = _find_event(jd_midnight - 0.6, swe.SUN, swe.CALC_RISE, request.lat, request.lon)

    sunset: float | None = None
    next_sunrise: float | None = None
    if sunrise is not None:
        sunset = _find_event(sunrise, swe.SUN, swe.CALC_SET, request.lat, request.lon)
        next_sunrise = _find_event(sunrise + 0.2, swe.SUN, swe.CALC_RISE, request.lat, request.lon)

    if sunrise is None or sunset is None or next_sunrise is None:
        # Polar day/night: the sun does not rise (or set) on this civil date at
        # this latitude, so no genuine sunrise-to-sunrise span exists. Fall back
        # to a synthetic civil-midnight-to-midnight Panchang day, anchored at
        # local midnight, with sunrise/sunset placeholders at 00:00 / 12:00
        # local civil time. Documented in docs/edge-cases.md.
        sunrise = jd_midnight
        sunset = jd_midnight + 0.5
        next_sunrise = jd_midnight + 1.0

    moonrise = _find_event(sunrise, swe.MOON, swe.CALC_RISE, request.lat, request.lon)
    moonset = _find_event(sunrise, swe.MOON, swe.CALC_SET, request.lat, request.lon)
    if moonrise is not None and moonrise > next_sunrise:
        moonrise = None
    if moonset is not None and moonset > next_sunrise:
        moonset = None

    day_start = sunrise
    day_end = next_sunrise
    day_start_local = jd_to_local_datetime(day_start, request.tz)

    def tv(jd: float):
        return to_time_value(jd, request.tz, day_start_local)

    # ── Reference longitudes (at sunrise — the moment the Panchang day opens) ──
    sun_lon = _sun(day_start)
    moon_lon = _moon(day_start)
    ayanamsa_value = engine.get_ayanamsa_value(day_start)

    # ── The five angas ──────────────────────────────────────────────────────
    def tithi_angle(jd: float) -> float:
        return (_moon(jd) - _sun(jd)) % _DEG

    def yoga_angle(jd: float) -> float:
        return (_sun(jd) + _moon(jd)) % _DEG

    def nakshatra_angle(jd: float) -> float:
        return _moon(jd)

    nak_step = _DEG / 27.0
    yoga_step = _DEG / 27.0
    karana_step = 6.0

    def karana_name(global_index: int) -> str:
        k = global_index % 60
        if k == 0:
            return "Kintughna"
        if k >= 57:
            return C.KARANA_NAMES_FIXED[k - 57]
        return C.KARANA_NAMES_MOVABLE[(k - 1) % 7]

    tithi = _anga_spans(
        tithi_angle, 12.0, lambda i: C.TITHI_NAMES[i % 30],
        day_start, day_end, search_back=1.3, search_fwd=1.3, tv=tv,
    )
    nakshatra = _anga_spans(
        nakshatra_angle, nak_step, lambda i: C.NAKSHATRA_NAMES[i % 27],
        day_start, day_end, search_back=1.3, search_fwd=1.3, tv=tv,
    )
    yoga = _anga_spans(
        yoga_angle, yoga_step, lambda i: C.YOGA_NAMES[i % 27],
        day_start, day_end, search_back=1.3, search_fwd=1.3, tv=tv,
    )
    karana = _anga_spans(
        tithi_angle, karana_step, karana_name,
        day_start, day_end, search_back=0.7, search_fwd=0.7, tv=tv,
    )

    weekday_index = (request.date.weekday() + 1) % 7  # 0 = Sunday
    vara = AngaSpan(
        index=weekday_index + 1,
        name=C.VARA_NAMES[weekday_index],
        start=tv(day_start),
        end=tv(day_end),
    )

    day_events = DayEvents(
        sunrise=tv(sunrise),
        sunset=tv(sunset),
        moonrise=tv(moonrise) if moonrise is not None else None,
        moonset=tv(moonset) if moonset is not None else None,
    )

    # ── Muhurat / period values ─────────────────────────────────────────────
    muhurat = _compute_muhurat(sunrise, sunset, next_sunrise, tv)
    choghadiya = _compute_choghadiya(sunrise, sunset, next_sunrise, weekday_index, tv)
    hora = _compute_hora(sunrise, sunset, next_sunrise, weekday_index, tv)

    # ── Samvat & calendrical fields ─────────────────────────────────────────
    is_adhika_month, is_kshaya_month = _detect_adhika_kshaya(tithi_angle, day_start, tithi[0].index)
    calendrical = _compute_calendrical(
        request, sun_lon, moon_lon, tithi[0].index, is_adhika_month, is_kshaya_month
    )

    return PanchangResult(
        request=request,
        sun_longitude=sun_lon,
        moon_longitude=moon_lon,
        ayanamsa_value=ayanamsa_value,
        tithi=tithi,
        nakshatra=nakshatra,
        yoga=yoga,
        karana=karana,
        vara=vara,
        day_events=day_events,
        muhurat=muhurat,
        choghadiya=choghadiya,
        hora=hora,
        calendrical=calendrical,
    )


# ──────────────────────────────────────────────────────────────────────────
# Muhurat / Choghadiya / Hora
# ──────────────────────────────────────────────────────────────────────────

def _compute_muhurat(sunrise: float, sunset: float, next_sunrise: float, tv) -> list[MuhuratPeriod]:
    day_dur = sunset - sunrise
    night_dur = next_sunrise - sunset
    segment = day_dur / 8.0

    def seg_period(name: str, seg_index: int) -> MuhuratPeriod:
        start = sunrise + segment * seg_index
        end = start + segment
        return MuhuratPeriod(name=name, start=tv(start), end=tv(end))

    weekday_index = _weekday_from_jd(sunrise)
    periods = [
        seg_period("Rahu Kalam", C.RAHU_KALAM_SEGMENT[weekday_index]),
        seg_period("Yamaganda", C.YAMAGANDA_SEGMENT[weekday_index]),
        seg_period("Gulika Kalam", C.GULIKA_SEGMENT[weekday_index]),
    ]

    minute = 1.0 / (24.0 * 60.0)

    midday = sunrise + day_dur / 2.0
    periods.append(MuhuratPeriod(name="Abhijit Muhurat", start=tv(midday - 24 * minute), end=tv(midday + 24 * minute)))

    periods.append(
        MuhuratPeriod(name="Brahma Muhurat", start=tv(sunrise - 96 * minute), end=tv(sunrise - 48 * minute))
    )

    midnight = sunset + night_dur / 2.0
    periods.append(MuhuratPeriod(name="Nishita Muhurat", start=tv(midnight - 24 * minute), end=tv(midnight + 24 * minute)))

    return periods


def _compute_choghadiya(sunrise: float, sunset: float, next_sunrise: float, weekday_index: int, tv) -> list[Choghadiya]:
    result: list[Choghadiya] = []

    day_segment = (sunset - sunrise) / 8.0
    for i, name in enumerate(C.CHOGHADIYA_DAY_SEQUENCE[weekday_index]):
        start = sunrise + day_segment * i
        end = start + day_segment
        result.append(Choghadiya(name=name, start=tv(start), end=tv(end), is_day=True))

    night_segment = (next_sunrise - sunset) / 8.0
    for i, name in enumerate(C.CHOGHADIYA_NIGHT_SEQUENCE[weekday_index]):
        start = sunset + night_segment * i
        end = start + night_segment
        result.append(Choghadiya(name=name, start=tv(start), end=tv(end), is_day=False))

    return result


def _compute_hora(sunrise: float, sunset: float, next_sunrise: float, weekday_index: int, tv) -> list[MuhuratPeriod]:
    result: list[MuhuratPeriod] = []
    start_idx = C.HORA_START_INDEX[weekday_index]

    day_segment = (sunset - sunrise) / 12.0
    night_segment = (next_sunrise - sunset) / 12.0

    for i in range(12):
        lord = C.HORA_LORDS[(start_idx + i) % 7]
        start = sunrise + day_segment * i
        end = start + day_segment
        result.append(MuhuratPeriod(name=f"Hora — {lord}", start=tv(start), end=tv(end)))

    for i in range(12):
        lord = C.HORA_LORDS[(start_idx + 12 + i) % 7]
        start = sunset + night_segment * i
        end = start + night_segment
        result.append(MuhuratPeriod(name=f"Hora — {lord}", start=tv(start), end=tv(end)))

    return result


def _weekday_from_jd(jd_ut: float) -> int:
    """0 = Sunday, per the Julian-Day weekday convention (JD+1.5 mod 7)."""
    return int((jd_ut + 1.5) % 7)


# ──────────────────────────────────────────────────────────────────────────
# Samvat & calendrical fields
# ──────────────────────────────────────────────────────────────────────────

def _detect_adhika_kshaya(tithi_angle, day_start: float, tithi_index: int) -> tuple[bool, bool]:
    """Detect Adhika (leap) and Kshaya (skipped) lunar months.

    A lunisolar (Amanta) month runs new-moon to new-moon. It is:
      - **Adhika** (leap) when the Sun does not cross into a new rashi
        (no sankranti) between the bounding new moons — the month repeats
        the previous month's name with an "Adhika" label.
      - **Kshaya** (skipped, very rare) when the Sun crosses into a new
        rashi *twice* within one lunar month — that month's name is
        absorbed/skipped in the sequence.
      - Otherwise (exactly one sankranti) the month is a normal month.

    New-moon instants are located by bisecting the tithi angle (Moon − Sun)
    to 0° within a window around the mean-tithi-length estimate of where
    each bounding new moon should fall; see docs/edge-cases.md for the
    rationale and accuracy margin of this approximation.
    """
    avg_tithi = _SYNODIC_MONTH / 30.0
    prev_est = day_start - (tithi_index - 0.5) * avg_tithi
    next_est = day_start + (30 - tithi_index + 0.5) * avg_tithi

    prev_new_moon = _bisect_crossing(tithi_angle, prev_est - 2.0, prev_est + 2.0, 0.0)
    next_new_moon = _bisect_crossing(tithi_angle, next_est - 2.0, next_est + 2.0, 0.0)
    if prev_new_moon is None:
        prev_new_moon = prev_est
    if next_new_moon is None:
        next_new_moon = next_est

    rashi_prev = int(_sun(prev_new_moon) // 30) % 12
    rashi_next = int(_sun(next_new_moon) // 30) % 12
    diff = (rashi_next - rashi_prev) % 12

    is_adhika = diff == 0
    is_kshaya = diff == 2
    return is_adhika, is_kshaya


def _compute_calendrical(
    request: PanchangRequest,
    sun_lon: float,
    moon_lon: float,
    tithi_index: int,
    is_adhika_month: bool = False,
    is_kshaya_month: bool = False,
) -> Calendrical:
    year = request.date.year
    month = request.date.month
    day = request.date.day

    # Lunisolar new-year falls roughly in late March / early April (Chaitra
    # Shukla Pratipada). Pending the Step 1.3 reference calibration we use the
    # Gregorian date as a proxy for which side of the epoch boundary we're on.
    after_new_year = (month, day) >= (3, 22)

    shaka_samvat = year - 78 if after_new_year else year - 79
    vikram_samvat = year + 57 if after_new_year else year + 56
    gujarati_samvat = vikram_samvat - 1 if month >= 11 or month <= 3 else vikram_samvat

    samvatsara = C.SAMVATSARA_NAMES[(shaka_samvat + 14) % 60]

    sun_rashi_index = int(sun_lon // 30) % 12
    moon_rashi_index = int(moon_lon // 30) % 12

    ritu = C.RITU_NAMES[sun_rashi_index // 2]

    # Uttarayana: Sun's sidereal longitude in [270°, 360°) ∪ [0°, 90°)
    # (Makar Sankranti to Karka Sankranti).
    ayana = "Uttarayana" if (sun_lon >= 270.0 or sun_lon < 90.0) else "Dakshinayana"

    paksha = "Shukla Paksha" if tithi_index <= 15 else "Krishna Paksha"

    # Lunar months map directly onto the sidereal solar rashi the Sun occupies
    # for most of that month (Chaitra<->Mesha, Vaishakha<->Vrishabha, ...).
    # An Adhika (leap) month repeats without a sankranti, so it is conventionally
    # named for the *following* month rather than the rashi it actually shares
    # with its successor (validated against the published reference — Step 1.3).
    # Purnimanta months run new-moon-to-new-moon offset by half a cycle: once
    # the Krishna-paksha half begins (tithi_index > 15), the Purnimanta name has
    # already advanced to the following Amanta month's name.
    month_index = sun_rashi_index
    if is_adhika_month or (request.month_scheme.value == "purnimanta" and tithi_index > 15):
        month_index += 1
    lunar_month = C.LUNAR_MONTH_NAMES_AMANTA[month_index % 12]

    return Calendrical(
        shaka_samvat=shaka_samvat,
        vikram_samvat=vikram_samvat,
        gujarati_samvat=gujarati_samvat,
        samvatsara=samvatsara,
        ritu=ritu,
        ayana=ayana,
        lunar_month=lunar_month,
        is_adhika_month=is_adhika_month,
        is_kshaya_month=is_kshaya_month,
        paksha=paksha,
        moon_rashi=C.RASHI_NAMES[moon_rashi_index],
        sun_rashi=C.RASHI_NAMES[sun_rashi_index],
    )
