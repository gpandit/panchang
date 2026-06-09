/**
 * Structure, data-binding, and accessibility contract tests for the Today screen.
 * Following the same pattern as primitives.test.ts — file-based assertions that
 * verify contracts without requiring a DOM renderer.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FEATURES_DIR = join(__dirname, "..", "..", "src", "features", "today");

const TODAY_COMPONENTS = [
  "TodayScreen",
  "TodayHeader",
  "SummaryCard",
  "PanchangDetailList",
  "ExplainModal",
  "MuhuratSection",
  "FestivalSection",
  "TimeFormatToggle",
  "AdvisorySection",
  "HighlightsSection",
  "DharmaCard",
  "ShareBookmarkBar",
];

describe("today screen — design token contract", () => {
  for (const component of TODAY_COMPONENTS) {
    it(`${component}.tsx carries the design TODO and no hardcoded colours`, () => {
      const source = readFileSync(join(FEATURES_DIR, `${component}.tsx`), "utf-8");
      expect(source).toContain("TODO(design): skin via Aqualeo design system");
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(source).not.toMatch(/rgba?\(/);
    });
  }
});

describe("today screen — accessibility semantics present in source", () => {
  it("TodayScreen has a <main> landmark with aria-label", () => {
    const source = readFileSync(join(FEATURES_DIR, "TodayScreen.tsx"), "utf-8");
    expect(source).toContain('<main aria-label=');
  });

  it("TodayHeader uses <header> and <time> elements", () => {
    const source = readFileSync(join(FEATURES_DIR, "TodayHeader.tsx"), "utf-8");
    expect(source).toContain("<header");
    expect(source).toContain("<time");
    expect(source).toContain("aria-label");
  });

  it("SummaryCard uses <section> with aria-label and <dl> for solar events", () => {
    const source = readFileSync(join(FEATURES_DIR, "SummaryCard.tsx"), "utf-8");
    expect(source).toContain('<section aria-label=');
    expect(source).toContain("<dl");
  });

  it("PanchangDetailList uses <section> and <ul> structure with tappable buttons", () => {
    const source = readFileSync(join(FEATURES_DIR, "PanchangDetailList.tsx"), "utf-8");
    expect(source).toContain('<section aria-label=');
    expect(source).toContain("<ul");
    expect(source).toContain('type="button"');
    expect(source).toContain("aria-label");
  });

  it("TimeFormatToggle uses role=group and role=radio", () => {
    const source = readFileSync(join(FEATURES_DIR, "TimeFormatToggle.tsx"), "utf-8");
    expect(source).toContain('role="group"');
    expect(source).toContain('role="radio"');
    expect(source).toContain("aria-checked");
  });

  it("ShareBookmarkBar has role=toolbar and aria-pressed on bookmark", () => {
    const source = readFileSync(join(FEATURES_DIR, "ShareBookmarkBar.tsx"), "utf-8");
    expect(source).toContain('role="toolbar"');
    expect(source).toContain("aria-pressed");
  });

  it("TodayScreen has loading state with role=status", () => {
    const source = readFileSync(join(FEATURES_DIR, "TodayScreen.tsx"), "utf-8");
    expect(source).toContain('role="status"');
  });

  it("TodayScreen has error state with role=alert", () => {
    const source = readFileSync(join(FEATURES_DIR, "TodayScreen.tsx"), "utf-8");
    expect(source).toContain('role="alert"');
  });
});

describe("today screen — data wiring present", () => {
  it("SummaryCard renders summaryTitle, panchangHindiDate, sunrise, sunset", () => {
    const source = readFileSync(join(FEATURES_DIR, "SummaryCard.tsx"), "utf-8");
    expect(source).toContain("data.summaryTitle");
    expect(source).toContain("data.panchangHindiDate");
    expect(source).toContain("data.sunrise");
    expect(source).toContain("data.sunset");
  });

  it("PanchangDetailList maps over elements", () => {
    const source = readFileSync(join(FEATURES_DIR, "PanchangDetailList.tsx"), "utf-8");
    expect(source).toContain("elements.filter");
  });

  it("MuhuratSection maps over muhurats", () => {
    const source = readFileSync(join(FEATURES_DIR, "MuhuratSection.tsx"), "utf-8");
    expect(source).toContain("muhurats.map");
  });

  it("FestivalSection maps over festivals", () => {
    const source = readFileSync(join(FEATURES_DIR, "FestivalSection.tsx"), "utf-8");
    expect(source).toContain("festivals.map");
  });

  it("AdvisorySection filters advisories by category", () => {
    const source = readFileSync(join(FEATURES_DIR, "AdvisorySection.tsx"), "utf-8");
    expect(source).toContain('category === "good"');
    expect(source).toContain('category === "avoid"');
  });

  it("HighlightsSection maps over highlights", () => {
    const source = readFileSync(join(FEATURES_DIR, "HighlightsSection.tsx"), "utf-8");
    expect(source).toContain("highlights.map");
  });
});

describe("today screen — offline wiring", () => {
  it("TodayScreen shows a cache notice when fromCache is true", () => {
    const source = readFileSync(join(FEATURES_DIR, "TodayScreen.tsx"), "utf-8");
    expect(source).toContain("fromCache");
    expect(source).toContain("cached Panchang");
  });

  it("api.ts writes to localStorage after a successful fetch", () => {
    const source = readFileSync(join(FEATURES_DIR, "api.ts"), "utf-8");
    expect(source).toContain("writeCache");
    expect(source).toContain("localStorage.setItem");
  });

  it("api.ts falls back to cache on network error", () => {
    const source = readFileSync(join(FEATURES_DIR, "api.ts"), "utf-8");
    expect(source).toContain("readCache");
    expect(source).toContain('"offline"');
  });
});
