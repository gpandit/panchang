import { describe, it, expect } from "vitest";
import { formatTime, formatTimeRange } from "../../src/features/today/time";

describe("formatTime", () => {
  const MORNING = "2025-06-09T06:30:00+05:30"; // 06:30 IST
  const MIDNIGHT = "2025-06-10T01:15:00+05:30"; // 01:15 IST (past midnight)
  const NOON = "2025-06-09T12:00:00+05:30";

  it("formats 12h correctly", () => {
    const result = formatTime(NOON, "12h");
    expect(result).toMatch(/12:00\s*PM/i);
  });

  it("formats 24h correctly", () => {
    const result = formatTime(MORNING, "24h");
    expect(result).toBe("06:30");
  });

  it("formats 24plus: pre-6am hours get +24", () => {
    const result = formatTime(MIDNIGHT, "24plus");
    // 01:15 → 25:15
    expect(result).toBe("25:15");
  });

  it("formats 24plus: post-6am hours unchanged", () => {
    const result = formatTime(MORNING, "24plus");
    expect(result).toBe("06:30");
  });

  it("returns empty string for null", () => {
    expect(formatTime(null, "12h")).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(formatTime(undefined, "24h")).toBe("");
  });

  it("returns empty string for empty string", () => {
    expect(formatTime("", "24plus")).toBe("");
  });

  it("passes through unparseable values", () => {
    expect(formatTime("not-a-date", "12h")).toBe("not-a-date");
  });
});

describe("formatTimeRange", () => {
  const START = "2025-06-09T08:00:00+05:30";
  const END = "2025-06-09T10:00:00+05:30";

  it("formats a full range", () => {
    const result = formatTimeRange(START, END, "24h");
    expect(result).toBe("08:00 – 10:00");
  });

  it("returns empty for both null", () => {
    expect(formatTimeRange(null, null, "12h")).toBe("");
  });

  it("returns start only when end is null", () => {
    const result = formatTimeRange(START, null, "24h");
    expect(result).toBe("08:00");
  });
});
