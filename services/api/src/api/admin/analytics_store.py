"""Analytics reporting store — fixture data for signups, active users, conversions.

Non-sensitive aggregate metrics only.  Birth/family data is never included.
A future step will replace this with queries against the analytics DB.
"""

from __future__ import annotations

from datetime import date, timedelta

from api.models.admin import ReportOut, ReportRow


def _generate_fixture(days: int, base_date: date | None = None) -> list[ReportRow]:
    """Generate deterministic fixture rows for the last N days."""
    end = base_date or date.today()
    rows = []
    for i in range(days - 1, -1, -1):
        d = end - timedelta(days=i)
        # Deterministic values based on the day-of-year so tests are stable
        doy = d.timetuple().tm_yday
        rows.append(
            ReportRow(
                date=d.isoformat(),
                signups=10 + (doy % 15),
                active_users=80 + (doy % 40),
                conversions=(doy % 5),
            )
        )
    return rows


_PERIOD_DAYS = {
    "last_7d": 7,
    "last_30d": 30,
    "last_90d": 90,
}


def get_report(period: str = "last_30d") -> ReportOut:
    days = _PERIOD_DAYS.get(period, 30)
    rows = _generate_fixture(days)
    totals = ReportRow(
        date="total",
        signups=sum(r.signups for r in rows),
        active_users=max(r.active_users for r in rows),
        conversions=sum(r.conversions for r in rows),
    )
    return ReportOut(period=period, rows=rows, totals=totals)
