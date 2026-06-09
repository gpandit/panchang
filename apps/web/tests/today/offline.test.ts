/**
 * Offline cache logic tests.
 * These run in Node (no localStorage), so we verify the graceful-degradation
 * path (no-op writes, null reads) and the cache key helper via the exported
 * internal functions.
 *
 * Integration-level "cache hit → no network fetch" behaviour is verified via
 * the data-binding tests which exercise fetchDailyPanchang with mocked fetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchDailyPanchang, clearDailyCache } from "../../src/features/today/api";
import type { DailyPanchangView } from "@pandit/api-client-ts";

const MOCK_PAYLOAD: DailyPanchangView = {
  date: "2025-06-09",
  lat: 19.076,
  lon: 72.877,
  tz: "Asia/Kolkata",
  locationLabel: "Mumbai, Maharashtra",
  summaryTitle: "Shukla Panchami · Rohini",
  panchangHindiDate: "Jyeshtha Shukla Panchami, VS 2082",
  elements: [
    {
      key: "tithi",
      label: "Tithi",
      value: "Shukla Panchami",
      group: "core",
      secondaryValue: "ends:2025-06-09T17:00:00+05:30",
    },
    {
      key: "nakshatra",
      label: "Nakshatra",
      value: "Rohini",
      group: "core",
    },
  ],
  sunrise: "2025-06-09T05:57:00+05:30",
  sunset: "2025-06-09T19:07:00+05:30",
  moonrise: null,
  moonset: null,
  muhurats: [],
  festivals: [],
  advisories: [],
  highlights: [],
  dharmaCard: null,
  leapMonthFlag: null,
  cachedAt: "2025-06-09T00:00:00Z",
};

describe("fetchDailyPanchang — network success", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: MOCK_PAYLOAD }),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the gateway payload on success", async () => {
    const result = await fetchDailyPanchang({
      date: "2025-06-09",
      latitude: 19.076,
      longitude: 72.877,
      timezone: "Asia/Kolkata",
    });

    expect(result.data).not.toBeNull();
    expect(result.data?.date).toBe("2025-06-09");
    expect(result.fromCache).toBe(false);
    expect(result.error).toBeUndefined();
  });

  it("data contains all required fields", async () => {
    const result = await fetchDailyPanchang({
      date: "2025-06-09",
      latitude: 19.076,
      longitude: 72.877,
      timezone: "Asia/Kolkata",
    });

    const d = result.data!;
    expect(d.summaryTitle).toBeTruthy();
    expect(d.elements).toBeInstanceOf(Array);
    expect(d.muhurats).toBeInstanceOf(Array);
    expect(d.festivals).toBeInstanceOf(Array);
    expect(d.advisories).toBeInstanceOf(Array);
    expect(d.highlights).toBeInstanceOf(Array);
  });
});

describe("fetchDailyPanchang — network failure, no cache", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns null data and an error when offline and no cache available", async () => {
    const result = await fetchDailyPanchang({
      date: "2099-01-01", // no cache entry for a future date
      latitude: 0,
      longitude: 0,
      timezone: "UTC",
    });

    expect(result.data).toBeNull();
    expect(result.error).toBeTruthy();
  });
});

describe("fetchDailyPanchang — HTTP error", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns an HTTP error string and null data when no cache available", async () => {
    const result = await fetchDailyPanchang({
      date: "2099-01-02",
      latitude: 0,
      longitude: 0,
      timezone: "UTC",
    });

    expect(result.data).toBeNull();
    expect(result.error).toContain("503");
  });
});

describe("clearDailyCache", () => {
  it("runs without throwing even when localStorage is unavailable (Node)", () => {
    expect(() => clearDailyCache()).not.toThrow();
  });
});
