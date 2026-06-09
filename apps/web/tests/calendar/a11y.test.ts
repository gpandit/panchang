/**
 * Accessibility semantics tests — file-based source assertions.
 * Verifies that the correct ARIA roles, labels, and structural elements
 * are present in the calendar component sources (no DOM renderer required).
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CAL_DIR = join(__dirname, "..", "..", "src", "features", "calendar");

const CALENDAR_COMPONENTS = [
  "CalendarScreen",
  "MonthNav",
  "MonthView",
  "DayCell",
  "DayView",
  "NoteEditor",
  "ReminderForm",
  "NoteList",
  "ReminderList",
];

function src(name: string): string {
  return readFileSync(join(CAL_DIR, `${name}.tsx`), "utf-8");
}

// ─── Design token contract ────────────────────────────────────────────────────

describe("calendar components — design token contract", () => {
  for (const component of CALENDAR_COMPONENTS) {
    it(`${component}.tsx carries TODO(design) comment and no hardcoded colours`, () => {
      const source = src(component);
      expect(source).toContain("TODO(design)");
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(source).not.toMatch(/rgba?\(/);
    });
  }
});

// ─── CalendarScreen ───────────────────────────────────────────────────────────

describe("CalendarScreen — accessibility structure", () => {
  it("has a <main> landmark with aria-label", () => {
    expect(src("CalendarScreen")).toContain('<main aria-label=');
  });

  it("shows a sync pending notice with role=status", () => {
    expect(src("CalendarScreen")).toContain('role="status"');
    expect(src("CalendarScreen")).toContain("pending sync");
  });
});

// ─── MonthNav ─────────────────────────────────────────────────────────────────

describe("MonthNav — accessibility structure", () => {
  it("uses <header> with aria-label", () => {
    const source = src("MonthNav");
    expect(source).toContain("<header");
    expect(source).toContain("aria-label");
  });

  it("contains a <time> element for the month label", () => {
    expect(src("MonthNav")).toContain("<time");
  });

  it("prev/next buttons have aria-label", () => {
    const source = src("MonthNav");
    expect(source).toContain('"Previous month"');
    expect(source).toContain('"Next month"');
  });

  it("scheme toggle uses role=group and role=radio with aria-checked", () => {
    const source = src("MonthNav");
    expect(source).toContain('role="group"');
    expect(source).toContain('role="radio"');
    expect(source).toContain("aria-checked");
  });

  it("stale-cache notice uses role=status", () => {
    expect(src("MonthNav")).toContain('role="status"');
  });
});

// ─── MonthView ────────────────────────────────────────────────────────────────

describe("MonthView — accessibility structure", () => {
  it("uses <section> with aria-label", () => {
    expect(src("MonthView")).toContain('<section aria-label=');
  });

  it("grid has role=grid with aria-label", () => {
    const source = src("MonthView");
    expect(source).toContain('role="grid"');
    expect(source).toContain("aria-label");
  });

  it("rows use role=row", () => {
    expect(src("MonthView")).toContain('role="row"');
  });

  it("column headers use role=columnheader", () => {
    expect(src("MonthView")).toContain('role="columnheader"');
  });

  it("loading state uses role=status", () => {
    expect(src("MonthView")).toContain('role="status"');
  });

  it("error state uses role=alert", () => {
    expect(src("MonthView")).toContain('role="alert"');
  });
});

// ─── DayCell ──────────────────────────────────────────────────────────────────

describe("DayCell — accessibility structure", () => {
  it("cell container uses role=gridcell", () => {
    expect(src("DayCell")).toContain('role="gridcell"');
  });

  it("button has aria-label, aria-pressed, aria-current", () => {
    const source = src("DayCell");
    expect(source).toContain("aria-label");
    expect(source).toContain("aria-pressed");
    expect(source).toContain("aria-current");
  });

  it("marker slots are aria-hidden", () => {
    expect(src("DayCell")).toContain('aria-hidden="true"');
  });

  it("uses data-marker attributes for automation hooks", () => {
    const source = src("DayCell");
    expect(source).toContain('data-marker="festival"');
    expect(source).toContain('data-marker="vrat"');
    expect(source).toContain('data-marker="note"');
    expect(source).toContain('data-marker="bookmark"');
  });
});

// ─── DayView ──────────────────────────────────────────────────────────────────

describe("DayView — accessibility structure", () => {
  it("uses <section> with aria-label", () => {
    expect(src("DayView")).toContain('<section\n      aria-label=');
  });

  it("uses <header> inside the section", () => {
    expect(src("DayView")).toContain("<header");
  });

  it("panchang summary uses <dl> with aria-label", () => {
    const source = src("DayView");
    expect(source).toContain("<dl");
    expect(source).toContain('aria-label="Panchang summary"');
  });

  it("tab buttons use role=tab and aria-selected", () => {
    const source = src("DayView");
    expect(source).toContain('role="tab"');
    expect(source).toContain("aria-selected");
  });

  it("tab panels use role=tabpanel and aria-labelledby", () => {
    const source = src("DayView");
    expect(source).toContain('role="tabpanel"');
    expect(source).toContain("aria-labelledby");
  });

  it("tablist uses role=tablist", () => {
    expect(src("DayView")).toContain('role="tablist"');
  });
});

// ─── NoteEditor ───────────────────────────────────────────────────────────────

describe("NoteEditor — form accessibility", () => {
  it("form has aria-label", () => {
    expect(src("NoteEditor")).toContain("aria-label={formLabel}");
  });

  it("textarea has aria-labelledby and aria-required", () => {
    const source = src("NoteEditor");
    expect(source).toContain("aria-labelledby");
    expect(source).toContain('aria-required="true"');
  });

  it("error message uses role=alert", () => {
    expect(src("NoteEditor")).toContain('role="alert"');
  });

  it("submit button has aria-disabled", () => {
    expect(src("NoteEditor")).toContain("aria-disabled");
  });
});

// ─── ReminderForm ─────────────────────────────────────────────────────────────

describe("ReminderForm — form accessibility", () => {
  it("form has aria-label", () => {
    expect(src("ReminderForm")).toContain("aria-label=");
  });

  it("title input has aria-required", () => {
    expect(src("ReminderForm")).toContain('aria-required="true"');
  });

  it("error message uses role=alert", () => {
    expect(src("ReminderForm")).toContain('role="alert"');
  });

  it("anchored date uses <time>", () => {
    expect(src("ReminderForm")).toContain("<time");
  });

  it("submit button has aria-disabled", () => {
    expect(src("ReminderForm")).toContain("aria-disabled");
  });
});

// ─── NoteList ─────────────────────────────────────────────────────────────────

describe("NoteList — list accessibility", () => {
  it("uses <ul> with aria-label", () => {
    const source = src("NoteList");
    expect(source).toContain("<ul");
    expect(source).toContain("aria-label");
  });

  it("pending note shows role=status", () => {
    expect(src("NoteList")).toContain('role="status"');
  });
});

// ─── ReminderList ─────────────────────────────────────────────────────────────

describe("ReminderList — list accessibility", () => {
  it("uses <ul> with aria-label", () => {
    const source = src("ReminderList");
    expect(source).toContain("<ul");
    expect(source).toContain("aria-label");
  });

  it("pending reminder shows role=status", () => {
    expect(src("ReminderList")).toContain('role="status"');
  });

  it("delete button has descriptive aria-label", () => {
    expect(src("ReminderList")).toContain("aria-label={`Delete reminder:");
  });

  it("anchored date uses <time>", () => {
    expect(src("ReminderList")).toContain("<time");
  });
});
