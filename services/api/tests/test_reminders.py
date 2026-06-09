"""Tests for the Reminders & Scheduling module (Step 2.5).

Exercises the resolver, scheduler, and delivery service directly — no HTTP
layer or Swiss Ephemeris invoked. A deterministic stub Panchang source drives
all astronomy lookups.

Key scenarios:
- Ekadashi recurrence resolves at correct local times across several months.
- Vriddhi (repeated) Tithi fires exactly once — not twice.
- Adhika (leap) month filtering: regular recurrence skips the leap month;
  observe_in_adhika recurrence fires in the leap month only.
- Kshaya (skipped) month: resolver produces no spurious fires.
- Gregorian anniversary recurrence resolves correctly.
- Weekday recurrence resolves correctly.
- Nakshatra recurrence resolves correctly.
- Idempotency: re-running the scheduler does not duplicate fires.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, timedelta
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import panchang.constants as C
from api.reminders.db import init_models, make_engine, make_session_factory
from api.reminders.delivery import DeliveryService, InMemoryChannel
from api.reminders.models import Reminder
from api.reminders.resolver import PanchangSource, resolve
from api.reminders.scheduler import ReminderScheduler
from api.reminders.schemas import RecurrenceKind, RecurrenceSpec
from panchang.models import (
    AngaSpan,
    Calendrical,
    DayEvents,
    MonthScheme,
    PanchangRequest,
    PanchangResult,
    TimeValue,
)

# ── shared stubs ───────────────────────────────────────────────────────────────

IST = ZoneInfo("Asia/Kolkata")

_SUNRISE_TV = TimeValue(
    iso="2024-11-01T06:15:00+05:30",
    hour_24="06:15:00",
    hour_12="06:15:00 AM",
    hour_24_plus="06:15:00",
)


def _span(index: int, name: str) -> AngaSpan:
    return AngaSpan(index=index, name=name, start=_SUNRISE_TV, end=_SUNRISE_TV)


def _make_result(
    day: date,
    *,
    tithi_index: int = 1,  # global 1..30
    nakshatra_name: str = "Ashwini",
    lunar_month: str = "Kartika",
    paksha: str = "Shukla Paksha",
    sun_rashi: str = "Tula",
    is_adhika: bool = False,
    is_kshaya: bool = False,
) -> PanchangResult:
    return PanchangResult(
        request=PanchangRequest(
            date=day, lat=28.6, lon=77.2, tz="Asia/Kolkata", month_scheme=MonthScheme.AMANTA
        ),
        sun_longitude=180.0,
        moon_longitude=0.0,
        ayanamsa_value=24.0,
        tithi=[_span(tithi_index, C.TITHI_NAMES[(tithi_index - 1) % 30])],
        nakshatra=[_span(1, nakshatra_name)],
        yoga=[_span(1, "Vishkambha")],
        karana=[_span(1, "Bava")],
        vara=_span(1, "Somavara"),
        day_events=DayEvents(sunrise=_SUNRISE_TV, sunset=_SUNRISE_TV, moonrise=None, moonset=None),
        muhurat=[],
        choghadiya=[],
        hora=[],
        calendrical=Calendrical(
            shaka_samvat=1946,
            vikram_samvat=2081,
            gujarati_samvat=2080,
            samvatsara="Krodhi",
            ritu="Sharad",
            ayana="Dakshinayana",
            lunar_month=lunar_month,
            is_adhika_month=is_adhika,
            is_kshaya_month=is_kshaya,
            paksha=paksha,
            moon_rashi="Mesha",
            sun_rashi=sun_rashi,
        ),
    )


def _make_source(seed: dict[date, PanchangResult]) -> PanchangSource:
    def _source(d: date) -> PanchangResult:
        return seed.get(d, _make_result(d))

    return _source


# ── DB fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = make_engine("sqlite+aiosqlite://")
    await init_models(engine)
    _factory = make_session_factory("sqlite+aiosqlite://")
    # Recreate with the initialised engine so tables exist.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory2 = async_sessionmaker(engine, expire_on_commit=False)
    async with factory2() as s:
        yield s


# ── StubCache helper ───────────────────────────────────────────────────────────


class StubCache:
    """Thin stand-in for PanchangCache backed by a seed dict."""

    def __init__(self, seed: dict[date, PanchangResult]) -> None:
        self._seed = seed

    def get(self, req: PanchangRequest) -> PanchangResult:
        return self._seed.get(req.date, _make_result(req.date))


# ── Ekadashi resolver tests ────────────────────────────────────────────────────


class TestEkadashiResolver:
    """Ekadashi = 11th Tithi of either Paksha; global tithi index 11 (Shukla)
    or 26 (Krishna). Both fire once per lunar fortnight."""

    def _build_ekadashi_seed(self, year: int) -> dict[date, PanchangResult]:
        """Build a synthetic year where Ekadashi (tithi 11 and 26) falls on
        predictable dates — one every ~15 days."""
        seed: dict[date, PanchangResult] = {}
        # Simulate a simple tithi cycle: tithi = (day_of_year % 30) + 1
        # This is not astronomically accurate — it's deterministic for testing.
        start = date(year, 1, 1)
        for i in range(366):
            d = start + timedelta(days=i)
            global_index = (i % 30) + 1
            paksha = "Shukla Paksha" if global_index <= 15 else "Krishna Paksha"
            seed[d] = _make_result(d, tithi_index=global_index, paksha=paksha)
        return seed

    def test_ekadashi_fires_roughly_twice_per_month(self):
        seed = self._build_ekadashi_seed(2024)
        source = _make_source(seed)
        spec = RecurrenceSpec(kind=RecurrenceKind.TITHI, tithi_index=11)

        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
            source=source,
            user_tz=IST,
        )

        # 12 months × ~2 = ~24; our 30-day cycle in 365 days → 12 full cycles
        # Each 30-day cycle has tithi 11 (day 10) and tithi 26 (day 25).
        # 365 / 30 ≈ 12.16 → 12 complete cycles → 24 Ekadashi occurrences.
        assert len(occurrences) == 24

    def test_ekadashi_fire_time_is_at_sunrise(self):
        seed = self._build_ekadashi_seed(2024)
        source = _make_source(seed)
        spec = RecurrenceSpec(kind=RecurrenceKind.TITHI, tithi_index=11, fire_at_sunrise=True)

        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
            source=source,
            user_tz=IST,
        )
        assert occurrences
        # Sunrise stub is 06:15 IST = 00:45 UTC
        for occ in occurrences:
            assert occ.fire_at.tzinfo == UTC
            assert occ.fire_at.hour == 0
            assert occ.fire_at.minute == 45

    def test_ekadashi_correct_local_time_custom_hour(self):
        seed = self._build_ekadashi_seed(2024)
        source = _make_source(seed)
        spec = RecurrenceSpec(
            kind=RecurrenceKind.TITHI,
            tithi_index=11,
            fire_at_sunrise=False,
            fire_hour=7,
            fire_minute=30,
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
            source=source,
            user_tz=IST,
        )
        assert occurrences
        # 07:30 IST = 02:00 UTC
        for occ in occurrences:
            assert occ.fire_at.hour == 2
            assert occ.fire_at.minute == 0

    def test_ekadashi_idempotency_keys_unique(self):
        seed = self._build_ekadashi_seed(2024)
        source = _make_source(seed)
        spec = RecurrenceSpec(kind=RecurrenceKind.TITHI, tithi_index=11)
        rid = str(uuid.uuid4())

        occurrences = resolve(
            reminder_id=rid,
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
            source=source,
            user_tz=IST,
        )
        keys = [o.idempotency_key for o in occurrences]
        assert len(keys) == len(set(keys)), "Idempotency keys must be unique"


# ── Vriddhi (repeated Tithi) tests ─────────────────────────────────────────────


class TestVriddhiTithi:
    """A Vriddhi Tithi spans two consecutive sunrises.
    The resolver must fire exactly once (first sunrise)."""

    def test_vriddhi_fires_once_not_twice(self):
        # Tithi 11 on both day1 and day2 (same global index) → Vriddhi
        day1 = date(2024, 3, 1)
        day2 = date(2024, 3, 2)
        day3 = date(2024, 3, 3)
        seed = {
            day1: _make_result(day1, tithi_index=11, paksha="Shukla Paksha"),
            day2: _make_result(day2, tithi_index=11, paksha="Shukla Paksha"),  # Vriddhi
            day3: _make_result(day3, tithi_index=12, paksha="Shukla Paksha"),
        }
        source = _make_source(seed)
        spec = RecurrenceSpec(kind=RecurrenceKind.TITHI, tithi_index=11)

        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=day1,
            end=day3,
            source=source,
            user_tz=IST,
        )

        assert len(occurrences) == 1
        assert occurrences[0].occurrence_date == day1.isoformat()


# ── Adhika (leap) month tests ──────────────────────────────────────────────────


class TestAdhikaMonth:
    """Reminders without observe_in_adhika skip the leap occurrence.
    Reminders with observe_in_adhika fire only in the leap month."""

    def _build_adhika_seed(self) -> dict[date, PanchangResult]:
        # Normal Kartika: Jan
        # Adhika Kartika: Feb  (is_adhika=True)
        seed: dict[date, PanchangResult] = {}
        for i in range(15):
            d = date(2024, 1, i + 1)
            global_idx = i + 1
            seed[d] = _make_result(
                d, tithi_index=global_idx, lunar_month="Kartika", paksha="Shukla Paksha"
            )
        for i in range(15):
            d = date(2024, 2, i + 1)
            global_idx = i + 1
            seed[d] = _make_result(
                d,
                tithi_index=global_idx,
                lunar_month="Kartika",
                paksha="Shukla Paksha",
                is_adhika=True,
            )
        return seed

    def test_regular_recurrence_skips_adhika(self):
        seed = self._build_adhika_seed()
        source = _make_source(seed)
        spec = RecurrenceSpec(
            kind=RecurrenceKind.TITHI,
            tithi_index=11,
            lunar_month="Kartika",
            observe_in_adhika=False,
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 2, 28),
            source=source,
            user_tz=IST,
        )
        # Only the regular (Jan 11) occurrence, not the Adhika (Feb 11) one.
        assert len(occurrences) == 1
        assert occurrences[0].occurrence_date == date(2024, 1, 11).isoformat()

    def test_adhika_recurrence_fires_in_leap_month(self):
        seed = self._build_adhika_seed()
        source = _make_source(seed)
        spec = RecurrenceSpec(
            kind=RecurrenceKind.TITHI,
            tithi_index=11,
            lunar_month="Kartika",
            observe_in_adhika=True,
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 2, 28),
            source=source,
            user_tz=IST,
        )
        # Only the Adhika (Feb 11) occurrence.
        assert len(occurrences) == 1
        assert occurrences[0].occurrence_date == date(2024, 2, 11).isoformat()


# ── Kshaya (skipped) month tests ───────────────────────────────────────────────


class TestKshayaMonth:
    """In a Kshaya year the named lunar month is absent — resolver must not
    invent a spurious occurrence."""

    def test_no_occurrence_when_month_absent(self):
        # No day in the range carries lunar_month="Pausha" — Kshaya scenario.
        seed: dict[date, PanchangResult] = {}
        for i in range(60):
            d = date(2024, 1, 1) + timedelta(days=i)
            seed[d] = _make_result(
                d,
                tithi_index=(i % 30) + 1,
                lunar_month="Margashirsha",  # the skipped month is Pausha
                paksha="Shukla Paksha" if (i % 30) < 15 else "Krishna Paksha",
            )
        source = _make_source(seed)
        spec = RecurrenceSpec(
            kind=RecurrenceKind.TITHI,
            tithi_index=11,
            lunar_month="Pausha",  # this month is absent — Kshaya
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 3, 1),
            source=source,
            user_tz=IST,
        )
        assert occurrences == [], "Kshaya month must produce no occurrences"


# ── Gregorian recurrence tests ─────────────────────────────────────────────────


class TestGregorianRecurrence:
    def test_annual_anniversary(self):
        seed: dict[date, PanchangResult] = {}
        source = _make_source(seed)
        spec = RecurrenceSpec(
            kind=RecurrenceKind.GREGORIAN,
            gregorian_month=8,
            gregorian_day=15,
            fire_at_sunrise=False,
            fire_hour=8,
            fire_minute=0,
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2025, 12, 31),
            source=source,
            user_tz=IST,
        )
        assert len(occurrences) == 2
        assert occurrences[0].occurrence_date == "2024-08-15"
        assert occurrences[1].occurrence_date == "2025-08-15"

    def test_feb_29_skipped_in_non_leap_year(self):
        source = _make_source({})
        spec = RecurrenceSpec(
            kind=RecurrenceKind.GREGORIAN,
            gregorian_month=2,
            gregorian_day=29,
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2023, 1, 1),
            end=date(2025, 12, 31),
            source=source,
            user_tz=IST,
        )
        # Only 2024 is a leap year
        assert len(occurrences) == 1
        assert occurrences[0].occurrence_date == "2024-02-29"


# ── Weekday recurrence tests ───────────────────────────────────────────────────


class TestWeekdayRecurrence:
    def test_every_monday_in_january(self):
        source = _make_source({})
        spec = RecurrenceSpec(
            kind=RecurrenceKind.WEEKDAY,
            weekday=0,  # Monday
            fire_at_sunrise=False,
            fire_hour=9,
            fire_minute=0,
        )
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 1, 1),
            end=date(2024, 1, 31),
            source=source,
            user_tz=IST,
        )
        # Mondays in Jan 2024: 1, 8, 15, 22, 29
        assert len(occurrences) == 5
        dates = [o.occurrence_date for o in occurrences]
        assert "2024-01-01" in dates
        assert "2024-01-08" in dates
        assert "2024-01-29" in dates

    def test_weekday_fires_on_correct_day_of_week(self):
        source = _make_source({})
        spec = RecurrenceSpec(kind=RecurrenceKind.WEEKDAY, weekday=4)  # Friday
        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 6, 1),
            end=date(2024, 6, 30),
            source=source,
            user_tz=IST,
        )
        for occ in occurrences:
            d = date.fromisoformat(occ.occurrence_date)
            assert d.weekday() == 4, f"{d} is not a Friday"


# ── Nakshatra recurrence tests ─────────────────────────────────────────────────


class TestNakshatraRecurrence:
    def test_rohini_nakshatra_fires_on_matching_days(self):
        seed: dict[date, PanchangResult] = {}
        for i in range(30):
            d = date(2024, 4, 1) + timedelta(days=i)
            nak = "Rohini" if i % 27 == 3 else "Ashwini"
            seed[d] = _make_result(d, nakshatra_name=nak)
        source = _make_source(seed)
        spec = RecurrenceSpec(kind=RecurrenceKind.NAKSHATRA, nakshatra_name="Rohini")

        occurrences = resolve(
            reminder_id=str(uuid.uuid4()),
            spec=spec,
            start=date(2024, 4, 1),
            end=date(2024, 4, 30),
            source=source,
            user_tz=IST,
        )
        assert len(occurrences) == 1
        assert occurrences[0].occurrence_date == date(2024, 4, 4).isoformat()


# ── Idempotency (scheduler) tests ──────────────────────────────────────────────


class TestSchedulerIdempotency:
    """Re-running the scheduler must not duplicate deliveries."""

    @pytest.mark.asyncio
    async def test_rerun_does_not_duplicate(self, session: AsyncSession):
        channel = InMemoryChannel()
        delivery = DeliveryService([channel])

        # Build an Ekadashi seed: tithi 11 on Jan 11 and Jan 26 2024.
        seed: dict[date, PanchangResult] = {}
        ekadashi_days = [date(2024, 1, 11), date(2024, 1, 26)]
        for i in range(31):
            d = date(2024, 1, 1) + timedelta(days=i)
            global_idx = i + 1 if i < 15 else i - 14
            paksha = "Shukla Paksha" if i < 15 else "Krishna Paksha"
            seed[d] = _make_result(
                d, tithi_index=11 if d in ekadashi_days else global_idx, paksha=paksha
            )

        cache = StubCache(seed)

        # Create a reminder in DB.
        rid = str(uuid.uuid4())
        reminder = Reminder(
            id=rid,
            user_id=str(uuid.uuid4()),
            title="Ekadashi",
            recurrence={
                "kind": "tithi",
                "tithi_index": 11,
                "fire_at_sunrise": False,
                "fire_hour": 6,
                "fire_minute": 0,
            },
            timezone="Asia/Kolkata",
            lat=28.6,
            lon=77.2,
            month_scheme="amanta",
            enabled=True,
        )
        session.add(reminder)
        await session.flush()

        scheduler = ReminderScheduler(session, cache, delivery)

        # First run — fires due occurrences (past dates relative to a future "today").
        today_past = date(2024, 1, 31)  # all Jan occurrences are "due"
        fired1 = await scheduler.run_all(today=today_past)

        # Second run — should fire nothing new.
        fired2 = await scheduler.run_all(today=today_past)

        assert fired2 == 0, "Second run must not re-fire already-delivered occurrences"
        # Total fires from first run equals unique occurrences.
        first_run_keys = {d["idempotency_key"] for d in channel.delivered}
        assert len(first_run_keys) == fired1

    @pytest.mark.asyncio
    async def test_only_past_due_occurrences_fire(self, session: AsyncSession):
        """Occurrences with fire_at > now must not be delivered."""
        channel = InMemoryChannel()
        delivery = DeliveryService([channel])

        seed = {
            date(2025, 12, 11): _make_result(
                date(2025, 12, 11), tithi_index=11, paksha="Shukla Paksha"
            )
        }
        cache = StubCache(seed)

        reminder = Reminder(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            title="Future Ekadashi",
            recurrence={
                "kind": "tithi",
                "tithi_index": 11,
                "fire_at_sunrise": False,
                "fire_hour": 6,
                "fire_minute": 0,
            },
            timezone="Asia/Kolkata",
            lat=28.6,
            lon=77.2,
            month_scheme="amanta",
            enabled=True,
        )
        session.add(reminder)
        await session.flush()

        scheduler = ReminderScheduler(session, cache, delivery)
        # today = 2024-01-01 → 2025-12-11 is in horizon but fire_at is in the future
        fired = await scheduler.run_all(today=date(2024, 1, 1))
        assert fired == 0
        assert len(channel.delivered) == 0


# ── RecurrenceSpec validation ──────────────────────────────────────────────────


class TestRecurrenceSpecValidation:
    def test_tithi_requires_tithi_index(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecurrenceSpec(kind=RecurrenceKind.TITHI)

    def test_nakshatra_requires_nakshatra_name(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecurrenceSpec(kind=RecurrenceKind.NAKSHATRA)

    def test_gregorian_requires_month_and_day(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecurrenceSpec(kind=RecurrenceKind.GREGORIAN, gregorian_month=8)

    def test_weekday_requires_weekday(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecurrenceSpec(kind=RecurrenceKind.WEEKDAY)

    def test_valid_ekadashi_spec(self):
        spec = RecurrenceSpec(kind=RecurrenceKind.TITHI, tithi_index=11)
        assert spec.tithi_index == 11
        assert spec.paksha is None  # matches both pakshas
