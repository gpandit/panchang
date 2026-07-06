/**
 * Smoke tests for @pandit/api-client-ts.
 *
 * Verifies that the package compiles and key type exports are accessible.
 */

import { describe, expect, it } from "vitest";
import type {
  AngaSpanOut,
  DailyPanchangOut,
  LocationOut,
  MarketplaceHealthOut,
  SubscriptionOut,
  SubscriptionTier,
} from "../src/index.js";

describe("@pandit/api-client-ts type exports", () => {
  it("DailyPanchangOut shape is constructable", () => {
    const span: AngaSpanOut = { index: 1, name: "Pratipada", start: null, end: null };

    const day: Partial<DailyPanchangOut> = {
      date: "2025-04-14",
      lat: 28.6139,
      lon: 77.209,
      tz: "Asia/Kolkata",
      ayanamsa: "lahiri",
      month_scheme: "amanta",
      tithi: [span],
      cached: false,
    };

    expect(day.date).toBe("2025-04-14");
    expect(day.ayanamsa).toBe("lahiri");
    expect((day.tithi ?? [])[0]?.name).toBe("Pratipada");
  });

  it("SubscriptionTier values are valid", () => {
    const tiers: SubscriptionTier[] = ["basic", "silver", "gold"];
    expect(tiers).toHaveLength(3);
  });

  it("LocationOut has required fields", () => {
    const loc: LocationOut = {
      id: "loc-1",
      name: "Mumbai",
      lat: 18.9667,
      lon: 72.8333,
      tz: "Asia/Kolkata",
      is_default: true,
    };
    expect(loc.tz).toBe("Asia/Kolkata");
  });

  it("SubscriptionOut features is a string array", () => {
    const sub: SubscriptionOut = {
      user_id: "u1",
      tier: "silver",
      valid_until: null,
      features: ["daily_panchang", "month_calendar"],
    };
    expect(sub.features).toContain("daily_panchang");
  });

  it("module index exports are defined", async () => {
    const mod = await import("../src/index.js");
    expect(mod).toBeDefined();
  });

  it("MarketplaceHealthOut shape is constructable", () => {
    const health: MarketplaceHealthOut = { status: "ok" };
    expect(health.status).toBe("ok");
  });
});
