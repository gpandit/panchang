/**
 * Smoke tests for @pandit/api-client-ts.
 *
 * These verify that the package compiles and exports are accessible.
 * Full integration tests against the live API are added in Stage 2.
 */

import { describe, it, expect } from "vitest";
import type { PanchangDay, Location, Ayanamsa, MonthScheme } from "../src/index.js";

describe("@pandit/api-client-ts type exports", () => {
  it("PanchangDay shape is constructable", () => {
    const location: Location = {
      latitude: 18.9667,
      longitude: 72.8333,
      timezone: "Asia/Kolkata",
    };

    const day: PanchangDay = {
      date: "2025-04-14",
      location,
      ayanamsa: "lahiri" satisfies Ayanamsa,
      monthScheme: "amanta" satisfies MonthScheme,
      tithi: null,
      nakshatra: null,
      yoga: null,
      karana: null,
      sunrise: null,
      sunset: null,
      moonrise: null,
      moonset: null,
      leapMonthFlag: null,
    };

    expect(day.date).toBe("2025-04-14");
    expect(day.ayanamsa).toBe("lahiri");
    expect(day.location.timezone).toBe("Asia/Kolkata");
  });

  it("module index exports are defined", async () => {
    const mod = await import("../src/index.js");
    // The module only exports types — the namespace object is defined even if empty at runtime
    expect(mod).toBeDefined();
  });
});
