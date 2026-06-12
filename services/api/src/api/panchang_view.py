"""Map DailyPanchangOut (raw computation) to DailyPanchangViewOut (UI view-model).

Every field below is derived by relabeling/reformatting values already present
on DailyPanchangOut — nothing here recomputes Panchang. festivals, advisories,
highlights, and dharma_card require content sources that don't exist yet, so
they're returned empty/None; the corresponding sections on the Today screen
hide themselves when empty.
"""

from __future__ import annotations

from datetime import UTC, datetime

from api.models.panchang import (
    AngaSpanOut,
    DailyPanchangOut,
    DailyPanchangViewOut,
    MuhuratWindowOut,
    PanchangElementOut,
)


def _anga_element(key: str, label: str, spans: list[AngaSpanOut]) -> PanchangElementOut:
    span = spans[0]
    secondary = f"ends:{span.end.iso}" if span.end else None
    return PanchangElementOut(
        key=key, label=label, value=span.name, secondary_value=secondary, group="core"
    )


def _calendrical_elements(out: DailyPanchangOut) -> list[PanchangElementOut]:
    c = out.calendrical
    return [
        PanchangElementOut(key="sun_rashi", label="Sun Rashi", value=c.sun_rashi, group="solar"),
        PanchangElementOut(key="ritu", label="Ritu", value=c.ritu, group="solar"),
        PanchangElementOut(key="ayana", label="Ayana", value=c.ayana, group="solar"),
        PanchangElementOut(key="moon_rashi", label="Moon Rashi", value=c.moon_rashi, group="lunar"),
        PanchangElementOut(key="paksha", label="Paksha", value=c.paksha, group="lunar"),
        PanchangElementOut(
            key="lunar_month", label="Lunar Month", value=c.lunar_month, group="lunar"
        ),
        PanchangElementOut(
            key="vikram_samvat", label="Vikram Samvat", value=str(c.vikram_samvat), group="other"
        ),
        PanchangElementOut(
            key="shaka_samvat", label="Shaka Samvat", value=str(c.shaka_samvat), group="other"
        ),
        PanchangElementOut(
            key="gujarati_samvat",
            label="Gujarati Samvat",
            value=str(c.gujarati_samvat),
            group="other",
        ),
        PanchangElementOut(key="samvatsara", label="Samvatsara", value=c.samvatsara, group="other"),
    ]


def to_daily_panchang_view(out: DailyPanchangOut) -> DailyPanchangViewOut:
    """Build the Today-screen view payload from a computed DailyPanchangOut."""
    elements = [
        _anga_element("tithi", "Tithi", out.tithi),
        _anga_element("nakshatra", "Nakshatra", out.nakshatra),
        _anga_element("yoga", "Yoga", out.yoga),
        _anga_element("karana", "Karana", out.karana),
        PanchangElementOut(key="vara", label="Vara", value=out.vara.name, group="core"),
        *_calendrical_elements(out),
    ]

    muhurats = [
        MuhuratWindowOut(name=m.name, start_time=m.start.iso, end_time=m.end.iso, type="auspicious")
        for m in out.muhurat
    ]

    if out.calendrical.is_adhika_month:
        leap_month_flag = "adhika"
    elif out.calendrical.is_kshaya_month:
        leap_month_flag = "kshaya"
    else:
        leap_month_flag = None

    return DailyPanchangViewOut(
        date=out.date,
        lat=out.lat,
        lon=out.lon,
        tz=out.tz,
        location_label=f"{out.lat:.2f}°, {out.lon:.2f}°",
        summary_title=f"{out.vara.name} · {out.tithi[0].name}",
        panchang_hindi_date=f"{out.calendrical.lunar_month} · {out.calendrical.paksha} Paksha",
        elements=elements,
        sunrise=out.day_events.sunrise.iso,
        sunset=out.day_events.sunset.iso,
        moonrise=out.day_events.moonrise.iso if out.day_events.moonrise else None,
        moonset=out.day_events.moonset.iso if out.day_events.moonset else None,
        muhurats=muhurats,
        festivals=[],
        advisories=[],
        highlights=[],
        dharma_card=None,
        leap_month_flag=leap_month_flag,
        cached_at=datetime.now(UTC).isoformat(),
    )
