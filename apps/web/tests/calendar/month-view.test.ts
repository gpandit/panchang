/**
 * Month view — data-binding tests.
 * Verifies that buildDayGrid correctly derives DayCellMarkers from
 * API fixtures without recomputing any Panchang values.
 */

import { describe, it, expect } from "vitest";
import {
  buildDayGrid,
  deriveMoonPhase,
  deriveDayCellMarkers,
} from "../../src/features/calendar/markers";
import type { CalendarMonthData, LocalNote } from "../../src/features/calendar/types";
import type { DailyPanchangOut, FestivalOut } from "@pandit/api-client-ts";

// ─── Minimal fixture builders ─────────────────────────────────────────────────

function makeDay(
  date: string,
  tithiIndex: number,
  tithiName: string,
  paksha: string,
): DailyPanchangOut {
  return {
    date,
    lat: 19.076,
    lon: 72.877,
    tz: "Asia/Kolkata",
    ayanamsa: "lahiri",
    month_scheme: "amanta",
    sun_longitude: 0,
    moon_longitude: 0,
    ayanamsa_value: 0,
    tithi: [{ index: tithiIndex, name: tithiName, start: null, end: null }],
    nakshatra: [{ index: 1, name: "Ashwini", start: null, end: null }],
    yoga: [],
    karana: [],
    vara: { index: 1, name: "Somavar", start: null, end: null },
    day_events: {
      sunrise: {
        iso: `${date}T06:00:00+05:30`,
        hour_24: "06:00:00",
        hour_12: "6:00:00 AM",
        hour_24_plus: "06:00:00",
      },
      sunset: {
        iso: `${date}T18:30:00+05:30`,
        hour_24: "18:30:00",
        hour_12: "6:30:00 PM",
        hour_24_plus: "18:30:00",
      },
      moonrise: null,
      moonset: null,
    },
    muhurat: [],
    choghadiya: [],
    hora: [],
    calendrical: {
      shaka_samvat: 1946,
      vikram_samvat: 2082,
      gujarati_samvat: 2081,
      samvatsara: "Krodhi",
      ritu: "Grishma",
      ayana: "Uttarayana",
      lunar_month: "Jyeshtha",
      is_adhika_month: false,
      is_kshaya_month: false,
      paksha,
      moon_rashi: "Vrishabha",
      sun_rashi: "Mithuna",
    },
    cached: false,
  };
}

function makeFestival(date: string, name: string, tags: string[] = []): FestivalOut {
  return {
    id: `fest-${date}-${name}`,
    name,
    date,
    description: null,
    tags,
    region: null,
    locale: null,
  };
}

// ─── deriveMoonPhase ──────────────────────────────────────────────────────────

describe("deriveMoonPhase", () => {
  it("returns 'new' for Amavasya (tithi 30)", () => {
    const day = makeDay("2026-06-01", 30, "Amavasya", "Krishna");
    expect(deriveMoonPhase(day)).toBe("new");
  });

  it("returns 'full' for Purnima (tithi 15)", () => {
    const day = makeDay("2026-06-11", 15, "Purnima", "Shukla");
    expect(deriveMoonPhase(day)).toBe("full");
  });

  it("returns 'waxing' for Shukla paksha (non-special tithi)", () => {
    const day = makeDay("2026-06-07", 5, "Shukla Panchami", "Shukla");
    expect(deriveMoonPhase(day)).toBe("waxing");
  });

  it("returns 'waning' for Krishna paksha", () => {
    const day = makeDay("2026-06-16", 2, "Krishna Dwitiya", "Krishna");
    expect(deriveMoonPhase(day)).toBe("waning");
  });
});

// ─── deriveDayCellMarkers ─────────────────────────────────────────────────────

describe("deriveDayCellMarkers", () => {
  const baseDay = makeDay("2026-06-07", 5, "Shukla Panchami", "Shukla");

  it("extracts tithi name from the first tithi element", () => {
    const markers = deriveDayCellMarkers(baseDay, [], []);
    expect(markers.tithi).toBe("Shukla Panchami");
  });

  it("splits festivals and vrats by the 'vrat' tag", () => {
    const festivals = [
      makeFestival("2026-06-07", "Ganga Dussehra"),
      makeFestival("2026-06-07", "Nirjala Ekadashi", ["vrat"]),
    ];
    const markers = deriveDayCellMarkers(baseDay, festivals, []);
    expect(markers.festivals).toEqual(["Ganga Dussehra"]);
    expect(markers.vrats).toEqual(["Nirjala Ekadashi"]);
  });

  it("only matches festivals on the exact date", () => {
    const festivals = [makeFestival("2026-06-08", "Other Day Festival")];
    const markers = deriveDayCellMarkers(baseDay, festivals, []);
    expect(markers.festivals).toHaveLength(0);
  });

  it("sets hasNote=true when a non-bookmark note exists for the date", () => {
    const notes: LocalNote[] = [
      { id: "n1", date: "2026-06-07", body: "test", tags: [], created_at: "", updated_at: "" },
    ];
    const markers = deriveDayCellMarkers(baseDay, [], notes);
    expect(markers.hasNote).toBe(true);
    expect(markers.hasBookmark).toBe(false);
  });

  it("sets hasBookmark=true when a bookmark note exists for the date", () => {
    const notes: LocalNote[] = [
      {
        id: "n2",
        date: "2026-06-07",
        body: "saved",
        tags: ["bookmark"],
        created_at: "",
        updated_at: "",
      },
    ];
    const markers = deriveDayCellMarkers(baseDay, [], notes);
    expect(markers.hasNote).toBe(false);
    expect(markers.hasBookmark).toBe(true);
  });

  it("does not set hasNote for notes on a different date", () => {
    const notes: LocalNote[] = [
      { id: "n3", date: "2026-06-08", body: "other", tags: [], created_at: "", updated_at: "" },
    ];
    const markers = deriveDayCellMarkers(baseDay, [], notes);
    expect(markers.hasNote).toBe(false);
  });
});

// ─── buildDayGrid ─────────────────────────────────────────────────────────────

describe("buildDayGrid — grid structure", () => {
  const june2026: CalendarMonthData = {
    year: 2026,
    month: 6,
    days: [
      makeDay("2026-06-01", 10, "Shukla Dashami", "Shukla"),
      makeDay("2026-06-07", 5, "Shukla Panchami", "Shukla"),
      makeDay("2026-06-11", 15, "Purnima", "Shukla"),
    ],
    festivals: [makeFestival("2026-06-07", "Ganga Dussehra")],
  };

  it("always produces a multiple-of-7 count of cells", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    expect(cells.length % 7).toBe(0);
  });

  it("contains exactly 30 current-month cells for June", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    const currentMonth = cells.filter((c) => c.isCurrentMonth);
    expect(currentMonth).toHaveLength(30);
  });

  it("marks today correctly", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    const todayCell = cells.find((c) => c.date === "2026-06-09");
    expect(todayCell?.isToday).toBe(true);
    const otherCell = cells.find((c) => c.date === "2026-06-08");
    expect(otherCell?.isToday).toBe(false);
  });

  it("binds tithi marker for days present in the API payload", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    const cell = cells.find((c) => c.date === "2026-06-07");
    expect(cell?.markers.tithi).toBe("Shukla Panchami");
  });

  it("binds festival marker for the correct date", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    const cell = cells.find((c) => c.date === "2026-06-07");
    expect(cell?.markers.festivals).toContain("Ganga Dussehra");
  });

  it("marks Purnima cell as moonPhase=full", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    const cell = cells.find((c) => c.date === "2026-06-11");
    expect(cell?.markers.moonPhase).toBe("full");
  });

  it("padding cells have isCurrentMonth=false", () => {
    const cells = buildDayGrid(june2026, [], "2026-06-09");
    const padding = cells.filter((c) => !c.isCurrentMonth);
    expect(padding.length).toBeGreaterThan(0);
    padding.forEach((c) => {
      expect(c.panchang).toBeNull();
    });
  });

  it("propagates hasNote from the notes array", () => {
    const notes: LocalNote[] = [
      { id: "n1", date: "2026-06-01", body: "test", tags: [], created_at: "", updated_at: "" },
    ];
    const cells = buildDayGrid(june2026, notes, "2026-06-09");
    const cell = cells.find((c) => c.date === "2026-06-01");
    expect(cell?.markers.hasNote).toBe(true);
  });
});
