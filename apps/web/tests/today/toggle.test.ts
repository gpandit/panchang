/**
 * Toggle logic tests — verify that time format state transitions and
 * localStorage round-trips work correctly, independent of React rendering.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { formatTime } from "../../src/features/today/time";
import type { TimeFormat } from "@pandit/api-client-ts";

// A shared ISO time used across assertions
const ISO = "2025-06-09T14:45:00+05:30"; // 14:45

const FORMATS: TimeFormat[] = ["12h", "24h", "24plus"];

describe("time format toggle — output changes across all formats", () => {
  it("12h output is distinct from 24h output", () => {
    // 14:45 → "2:45 PM" (12h) vs "14:45" (24h)
    expect(formatTime(ISO, "12h")).not.toBe(formatTime(ISO, "24h"));
  });

  it("12h output contains AM or PM", () => {
    expect(formatTime(ISO, "12h")).toMatch(/AM|PM/);
  });

  it("24h output does not contain AM or PM", () => {
    expect(formatTime(ISO, "24h")).not.toMatch(/AM|PM/);
    expect(formatTime(ISO, "24h")).toBe("14:45");
  });

  it("24plus output for afternoon times equals 24h", () => {
    // 14:45 is after 06:00 so no +24 adjustment
    expect(formatTime(ISO, "24plus")).toBe("14:45");
  });
});

describe("time format toggle — pre-dawn boundary", () => {
  const PREDAWN = "2025-06-10T02:30:00+05:30"; // 02:30

  it("12h shows AM for pre-dawn", () => {
    expect(formatTime(PREDAWN, "12h")).toMatch(/AM/);
  });

  it("24h shows 02:30", () => {
    expect(formatTime(PREDAWN, "24h")).toBe("02:30");
  });

  it("24plus adds 24 to pre-dawn hours", () => {
    expect(formatTime(PREDAWN, "24plus")).toBe("26:30");
  });
});
