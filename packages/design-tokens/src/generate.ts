/**
 * Generates all client output formats from the single canonical schema
 * (./schema.ts). Run via `pnpm --filter @pandit/design-tokens build`.
 *
 * TODO(design): outputs carry placeholder values only. Regenerate after
 * the schema's *values* are replaced — names must stay stable.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { flatten, tokens, type TokenEntry } from "./schema.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(__dirname, "..", "generated");

const HEADER =
  "AUTO-GENERATED from packages/design-tokens/src/schema.ts — do not edit by hand.\nTODO(design): values are neutral placeholders pending the Aqualeo design system.";

function cssVarName(entry: TokenEntry): string {
  return `--${entry.name.replace(/\./g, "-")}`;
}

function camel(name: string): string {
  return name
    .split(/[.-]/)
    .map((part, i) => (i === 0 ? part : part.charAt(0).toUpperCase() + part.slice(1)))
    .join("");
}

function generateCss(entries: TokenEntry[]): string {
  const lines = entries.map((e) => `  ${cssVarName(e)}: ${e.value};`);
  return `/* ${HEADER.split("\n").join("\n   ")} */\n:root {\n${lines.join("\n")}\n}\n`;
}

function generateTailwindPreset(entries: TokenEntry[]): string {
  const byGroup = new Map<string, TokenEntry[]>();
  for (const e of entries) {
    const group = e.name.split(".")[0]!;
    byGroup.set(group, [...(byGroup.get(group) ?? []), e]);
  }
  const ref = (e: TokenEntry) => `"var(${cssVarName(e)})"`;
  const obj = (group: string) =>
    `{\n${(byGroup.get(group) ?? [])
      .map((e) => `        "${e.name.split(".").slice(1).join("-")}": ${ref(e)},`)
      .join("\n")}\n      }`;

  return `// ${HEADER.split("\n").join("\n// ")}
/** @type {import("tailwindcss").Config["theme"]} */
export const tokenPreset = {
  extend: {
    colors: ${obj("color")},
    fontFamily: {
      base: ["var(--typography-font-family-base)"],
      display: ["var(--typography-font-family-display)"],
      devanagari: ["var(--typography-font-family-devanagari)"],
    },
    fontSize: {
      xs: "var(--typography-scale-xs)",
      sm: "var(--typography-scale-sm)",
      base: "var(--typography-scale-base)",
      lg: "var(--typography-scale-lg)",
      xl: "var(--typography-scale-xl)",
      "2xl": "var(--typography-scale-2xl)",
      "3xl": "var(--typography-scale-3xl)",
    },
    spacing: ${obj("spacing")},
    borderRadius: ${obj("radius")},
    boxShadow: ${obj("shadow")},
    transitionDuration: {
      fast: "var(--motion-duration-fast)",
      base: "var(--motion-duration-base)",
      slow: "var(--motion-duration-slow)",
    },
    zIndex: ${obj("zIndex")},
    screens: ${obj("breakpoint")},
  },
};
`;
}

function generateSwift(entries: TokenEntry[]): string {
  const byGroup = new Map<string, TokenEntry[]>();
  for (const e of entries) {
    const group = e.name.split(".")[0]!;
    byGroup.set(group, [...(byGroup.get(group) ?? []), e]);
  }
  const enumFor = (group: string) =>
    `    enum ${group.charAt(0).toUpperCase() + group.slice(1)} {\n${(byGroup.get(group) ?? [])
      .map(
        (e) =>
          `        /// TODO(design): placeholder. Token: "${e.name}"\n        static let ${camel(e.name.split(".").slice(1).join("-"))} = "${e.value}"`,
      )
      .join("\n")}\n    }`;

  return `// ${HEADER.split("\n").join("\n// ")}
import Foundation

/// Namespaced design tokens, mirroring packages/design-tokens/src/schema.ts.
/// Native screens reference these by name — never hardcode visual values.
public enum DesignTokens {
${Object.keys(Object.fromEntries(byGroup))
  .map(enumFor)
  .join("\n")}
}
`;
}

function generateKotlin(entries: TokenEntry[]): string {
  const byGroup = new Map<string, TokenEntry[]>();
  for (const e of entries) {
    const group = e.name.split(".")[0]!;
    byGroup.set(group, [...(byGroup.get(group) ?? []), e]);
  }
  const objectFor = (group: string) =>
    `    object ${group.replaceAll(/^[a-z]/g, (c) => c.toUpperCase())} {\n${(byGroup.get(group) ?? [])
      .map(
        (e) =>
          `        // TODO(design): placeholder. Token: "${e.name}"\n        const val ${camel(e.name.split(".").slice(1).join("-"))}: String = "${e.value}"`,
      )
      .join("\n")}\n    }`;

  return `// ${HEADER.split("\n").join("\n// ")}
package com.pandit.designtokens

/**
 * Namespaced design tokens, mirroring packages/design-tokens/src/schema.ts.
 * Compose theme wires MaterialTheme to these — never hardcode visual values.
 */
object DesignTokens {
${Object.keys(Object.fromEntries(byGroup))
  .map(objectFor)
  .join("\n")}
}
`;
}

export function generateAll(): Record<string, string> {
  const entries = flatten(tokens);
  return {
    "tokens.css": generateCss(entries),
    "tailwind-preset.js": generateTailwindPreset(entries),
    "DesignTokens.swift": generateSwift(entries),
    "DesignTokens.kt": generateKotlin(entries),
  };
}

function main(): void {
  mkdirSync(OUT_DIR, { recursive: true });
  for (const [filename, content] of Object.entries(generateAll())) {
    writeFileSync(join(OUT_DIR, filename), content, "utf-8");
    console.log(`wrote generated/${filename}`);
  }
}

const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) main();
