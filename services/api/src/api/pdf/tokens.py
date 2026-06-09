"""PDF template tokens.

All visual values are TODO(design) placeholders.  The design team will replace
these with the final Aqualeo token values.  Layout primitives (page size,
column count, cell height) are authored here because they are required to
produce a structurally valid printable document — they are not aesthetic choices.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfTokens:
    # ── Page layout ───────────────────────────────────────────────────────────
    page_width_mm: float = 297.0  # A4 landscape width — TODO(design): confirm page size
    page_height_mm: float = 210.0  # A4 landscape height — TODO(design)
    margin_mm: float = 12.0  # uniform page margin — TODO(design)

    # ── Typography — size only; font family is TODO(design) ──────────────────
    month_title_size: float = 14.0  # TODO(design)
    weekday_label_size: float = 7.0  # TODO(design)
    day_number_size: float = 9.0  # TODO(design)
    tithi_size: float = 6.0  # TODO(design)
    festival_size: float = 5.5  # TODO(design)

    # ── Greyscale fill values (0-255) — TODO(design): replace with brand colors
    # All colour decisions are deferred to design.  Greyscale keeps the document
    # legible without requiring a colour palette decision.
    header_fill: int = 220  # TODO(design)
    weekend_fill: int = 245  # TODO(design)
    today_fill: int = 200  # TODO(design)
    festival_fill: int = 235  # TODO(design)
    cell_border: int = 180  # TODO(design)

    # ── Grid ─────────────────────────────────────────────────────────────────
    cols: int = 7  # days of week — fixed
    row_height_mm: float = 20.0  # TODO(design): adjust for content density


# Singleton used throughout the worker.  Replace at test time if needed.
PDF_TOKENS = PdfTokens()
