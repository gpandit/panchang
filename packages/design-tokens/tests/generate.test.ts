import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { flatten, tokens } from "../src/schema.js";
import { generateAll } from "../src/generate.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const GENERATED_DIR = join(__dirname, "..", "generated");

describe("token generation", () => {
  const entries = flatten(tokens);

  it("produces a non-empty schema with only TODO(design) placeholder entries", () => {
    expect(entries.length).toBeGreaterThan(0);
    for (const entry of entries) {
      expect(entry.todoDesign).toBe(true);
      expect(entry.value.length).toBeGreaterThan(0);
    }
  });

  it("emits all four output formats", () => {
    const outputs = generateAll();
    expect(Object.keys(outputs).sort()).toEqual(
      ["DesignTokens.kt", "DesignTokens.swift", "tailwind-preset.js", "tokens.css"].sort(),
    );
  });

  it("every token name appears as a CSS variable and in both native outputs", () => {
    const outputs = generateAll();
    for (const entry of entries) {
      const cssVar = `--${entry.name.replace(/\./g, "-")}`;
      expect(outputs["tokens.css"]).toContain(cssVar);
      expect(outputs["DesignTokens.swift"]).toContain(`Token: "${entry.name}"`);
      expect(outputs["DesignTokens.kt"]).toContain(`Token: "${entry.name}"`);
    }
  });

  it("Tailwind preset references CSS variables for the groups it maps", () => {
    const outputs = generateAll();
    expect(outputs["tailwind-preset.js"]).toContain("var(--color-primary)");
    expect(outputs["tailwind-preset.js"]).toContain("var(--spacing-md)");
    expect(outputs["tailwind-preset.js"]).toContain("var(--radius-md)");
    expect(outputs["tailwind-preset.js"]).toContain("var(--shadow-md)");
  });

  it("checked-in generated/ outputs are in sync with the schema (run build to regenerate)", () => {
    const outputs = generateAll();
    for (const filename of Object.keys(outputs)) {
      const path = join(GENERATED_DIR, filename);
      expect(existsSync(path), `${filename} missing — run the build script`).toBe(true);
      expect(readFileSync(path, "utf-8")).toBe(outputs[filename]);
    }
  });
});

describe("contrast check (pending real tokens)", () => {
  it.skip("WCAG contrast ratios — cannot evaluate meaningfully on neutral placeholders; enable once Aqualeo colour tokens land", () => {
    // TODO(design): once real color.* values are supplied, assert pairs like
    // (background, foreground), (primary, primary-foreground), etc. meet
    // WCAG AA contrast ratios (4.5:1 text, 3:1 large text/UI). Placeholder
    // grayscale values are not a meaningful signal of the final design.
  });
});
