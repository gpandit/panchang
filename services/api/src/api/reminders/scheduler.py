"""Reminder scheduler — rolling horizon + queue-driven fan-out.

Responsibilities:
1. For each enabled Reminder, resolve recurrences forward from today to
   `today + horizon_days` using the Panchang cache.
2. For each resolved occurrence, check idempotency (skip if already delivered).
3. Enqueue due occurrences and fan out to the delivery service.
4. Mark occurrences delivered in the DB so re-runs are idempotent.

The scheduler is designed to be called:
- By a periodic background task (e.g. Celery beat, APScheduler, or a cron job)
  to advance the rolling horizon.
- On-demand when a new Reminder is created to pre-fill the horizon.

It never blocks interactive FastAPI request handlers — call it from a
background task only.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.reminders.delivery import DeliveryService
from api.reminders.models import DeliveredOccurrence, Reminder
from api.reminders.resolver import make_panchang_source, resolve
from api.reminders.schemas import OccurrenceRead, RecurrenceSpec
from panchang.cache import PanchangCache
from panchang.models import MonthScheme

log = logging.getLogger(__name__)

# Default horizon: resolve this many days ahead on each scheduler run.
DEFAULT_HORIZON_DAYS = 90


class ReminderScheduler:
    """Resolves and delivers reminders for all enabled users.

    `session` is an open async SQLAlchemy session (the caller is responsible
    for committing / rolling back).
    `panchang_cache` is the shared cache — reads are always cache-through.
    `delivery` is the fan-out delivery service.
    """

    def __init__(
        self,
        session: AsyncSession,
        panchang_cache: PanchangCache,
        delivery: DeliveryService,
        horizon_days: int = DEFAULT_HORIZON_DAYS,
    ) -> None:
        self._session = session
        self._cache = panchang_cache
        self._delivery = delivery
        self._horizon_days = horizon_days

    # ── public entry points ────────────────────────────────────────────────

    async def run_all(self, today: date | None = None) -> int:
        """Process every enabled Reminder. Returns the count of occurrences fired."""
        today = today or date.today()
        result = await self._session.execute(
            select(Reminder).where(Reminder.enabled.is_(True))
        )
        reminders = result.scalars().all()

        total_fired = 0
        for reminder in reminders:
            total_fired += await self._process(reminder, today)
        return total_fired

    async def run_for_reminder(self, reminder_id: UUID, today: date | None = None) -> int:
        """Process a single Reminder by ID. Returns occurrences fired."""
        today = today or date.today()
        result = await self._session.execute(
            select(Reminder).where(
                Reminder.id == str(reminder_id), Reminder.enabled.is_(True)
            )
        )
        reminder = result.scalar_one_or_none()
        if reminder is None:
            return 0
        return await self._process(reminder, today)

    # ── internal ──────────────────────────────────────────────────────────

    async def _process(self, reminder: Reminder, today: date) -> int:
        end = today + timedelta(days=self._horizon_days)
        spec = RecurrenceSpec.model_validate(reminder.recurrence)
        user_tz = ZoneInfo(reminder.timezone)
        month_scheme = MonthScheme(reminder.month_scheme)

        source = make_panchang_source(
            self._cache.get,
            lat=reminder.lat,
            lon=reminder.lon,
            tz=reminder.timezone,
            month_scheme=month_scheme,
        )

        occurrences = resolve(
            reminder_id=str(reminder.id),
            spec=spec,
            start=today,
            end=end,
            source=source,
            user_tz=user_tz,
        )

        # Load already-delivered keys for this reminder in one query.
        delivered_result = await self._session.execute(
            select(DeliveredOccurrence.idempotency_key).where(
                DeliveredOccurrence.reminder_id == str(reminder.id)
            )
        )
        already_delivered: set[str] = set(delivered_result.scalars().all())

        fired = 0
        now_utc = datetime.now(tz=UTC)

        for occ in occurrences:
            if occ.idempotency_key in already_delivered:
                continue  # idempotency: skip

            # Only fire occurrences whose fire_at is in the past or now.
            if occ.fire_at > now_utc:
                continue

            await self._deliver(reminder, occ, now_utc)
            fired += 1

        return fired

    async def _deliver(
        self,
        reminder: Reminder,
        occ: OccurrenceRead,
        now_utc: datetime,
    ) -> None:
        try:
            await self._delivery.send(occ, title=reminder.title, body=occ.occurrence_date)
        except Exception:
            log.exception("Delivery failed for key=%s", occ.idempotency_key)
            return

        # Record delivery — this is the idempotency write.
        record = DeliveredOccurrence(
            idempotency_key=occ.idempotency_key,
            reminder_id=str(reminder.id),
            occurrence_date=occ.occurrence_date,
            fire_at=occ.fire_at,
            delivered_at=now_utc,
        )
        self._session.add(record)
        # Flush so re-entrant calls within the same session see the record.
        await self._session.flush()
