import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PRIMITIVES_DIR = join(__dirname, "..", "src", "components", "primitives");

const CONTRACTED_COMPONENTS = [
  "nav",
  "section-header",
  "card",
  "cta",
  "footer",
  "icon-button",
  "list-row",
  "modal",
  "form-field",
];

describe("themeable primitive shells", () => {
  for (const file of CONTRACTED_COMPONENTS) {
    it(`${file}.tsx is unstyled beyond tokens and carries the design TODO`, () => {
      const source = readFileSync(join(PRIMITIVES_DIR, `${file}.tsx`), "utf-8");
      expect(source).toContain("TODO(design): skin via Aqualeo design system");
      // No hex/rgb literals — visual values must flow through named tokens / Tailwind theme keys.
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(source).not.toMatch(/rgba?\(/);
    });
  }
});
