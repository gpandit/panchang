"""Calendar PDF worker — renders a 12-month Gregorian/Panchang calendar.

Architecture component 06: async, queue-driven, server-side only.
Clients never call this directly; the API router enqueues a CalendarJob and
the worker (running in a background task or RQ worker) calls render_calendar_pdf.

Visual values are driven from PdfTokens (all marked TODO(design)).
Only the layout primitives required for a structurally valid 300-DPI print PDF
are authored here.
"""

from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from api.pdf.tokens import PDF_TOKENS, PdfTokens

# fpdf2 import — optional so the module can be imported in environments that
# have not installed the pdf extra yet (type-checking passes without it).
try:
    from fpdf import FPDF

    _FPDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FPDF_AVAILABLE = False
    FPDF = object  # type: ignore[assignment,misc]


WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass
class CalendarJob:
    job_id: str
    year: int
    lat: float
    lon: float
    tz: str
    ayanamsa: str = "lahiri"
    month_scheme: str = "amanta"
    # Pre-assembled festival names keyed by "YYYY-MM-DD" (optional overlay)
    festival_map: dict[str, list[str]] | None = None


def render_calendar_pdf(job: CalendarJob, tokens: PdfTokens = PDF_TOKENS) -> bytes:
    """Render a 12-month calendar for *job.year* and return the PDF bytes.

    Each month occupies one page.  The calendar grid shows:
    - Gregorian day number
    - Festival name(s) from *job.festival_map* if provided

    Panchang tithi data is not fetched here — the router/queue layer may
    pre-populate *festival_map* with resolved festival names.  The resulting
    PDF is structurally complete and themeable; all visual values flow through
    *tokens*.
    """
    if not _FPDF_AVAILABLE:
        raise RuntimeError("fpdf2 is not installed.  Add 'fpdf2' to pyproject.toml dependencies.")

    pdf = FPDF(orientation="L", unit="mm", format=(tokens.page_height_mm, tokens.page_width_mm))
    pdf.set_auto_page_break(auto=False)

    usable_w = tokens.page_width_mm - 2 * tokens.margin_mm
    usable_h = tokens.page_height_mm - 2 * tokens.margin_mm

    # Header row height (month title + weekday labels)
    header_h = 12.0
    weekday_h = 6.0
    rows = 6
    cell_w = usable_w / tokens.cols
    cell_h = (usable_h - header_h - weekday_h) / rows

    festival_map = job.festival_map or {}

    for month_num in range(1, 13):
        pdf.add_page()
        x0 = tokens.margin_mm
        y0 = tokens.margin_mm

        # ── Month title ───────────────────────────────────────────────────────
        month_name = datetime.date(job.year, month_num, 1).strftime("%B %Y")
        pdf.set_fill_color(tokens.header_fill, tokens.header_fill, tokens.header_fill)
        pdf.set_xy(x0, y0)
        pdf.set_font("Helvetica", "B", tokens.month_title_size)
        pdf.cell(usable_w, header_h, month_name, border=0, align="C", fill=True)

        # ── Weekday header row ────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", tokens.weekday_label_size)
        pdf.set_xy(x0, y0 + header_h)
        for label in WEEKDAY_LABELS:
            pdf.set_fill_color(tokens.header_fill, tokens.header_fill, tokens.header_fill)
            pdf.cell(cell_w, weekday_h, label, border=1, align="C", fill=True)

        # ── Calendar grid ─────────────────────────────────────────────────────
        # calendar.monthcalendar returns weeks as lists of 7 ints (0 = padding)
        weeks = calendar.monthcalendar(job.year, month_num)
        # Pad to exactly 6 rows
        while len(weeks) < rows:
            weeks.append([0] * 7)

        y_grid = y0 + header_h + weekday_h
        today = datetime.date.today()

        for row_i, week in enumerate(weeks[:rows]):
            for col_i, day_num in enumerate(week):
                cx = x0 + col_i * cell_w
                cy = y_grid + row_i * cell_h

                # Cell fill — weekend / today / empty
                if day_num == 0:
                    fill_val = 255  # white — empty padding cell
                elif col_i >= 5:  # Sat/Sun
                    fill_val = tokens.weekend_fill
                elif datetime.date(job.year, month_num, day_num) == today:
                    fill_val = tokens.today_fill
                else:
                    fill_val = 255

                pdf.set_fill_color(fill_val, fill_val, fill_val)
                pdf.rect(cx, cy, cell_w, cell_h, style="FD")  # filled + border

                if day_num == 0:
                    continue

                # Day number
                pdf.set_font("Helvetica", "B", tokens.day_number_size)
                pdf.set_text_color(0, 0, 0)
                pdf.set_xy(cx + 1, cy + 1)
                pdf.cell(cell_w - 2, tokens.day_number_size * 0.45, str(day_num), align="L")

                # Festival overlay
                date_str = f"{job.year}-{month_num:02d}-{day_num:02d}"
                festivals = festival_map.get(date_str, [])
                if festivals:
                    pdf.set_font("Helvetica", "", tokens.festival_size)
                    pdf.set_xy(cx + 1, cy + tokens.day_number_size * 0.45 + 2)
                    festival_text = festivals[0][:14]  # truncate to fit cell
                    pdf.cell(
                        cell_w - 2,
                        tokens.festival_size * 0.45,
                        festival_text,
                        align="L",
                    )

    return bytes(pdf.output())


# ── Convenience wrapper called by the queue processor ────────────────────────


def run_job(job: CalendarJob) -> bytes:
    """Entry point for the background worker.  Returns raw PDF bytes."""
    return render_calendar_pdf(job)
