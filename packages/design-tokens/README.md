# packages/design-tokens — Design Token Pipeline

**Status: placeholder values — replaced by the Aqualeo design system in Stage 3.**

`src/schema.ts` is the single canonical token schema (colour, type scale,
spacing, radii, shadow, motion, z-index, breakpoints) — every entry holds a
neutral placeholder value marked `TODO(design)`. `src/generate.ts` emits it
into the four formats each client consumes, written to `generated/`:

| Output                          | Consumer                          |
|---------------------------------|-----------------------------------|
| `tokens.css`                    | Web — CSS custom properties       |
| `tailwind-preset.js`            | Web — Tailwind theme preset       |
| `DesignTokens.swift`            | iOS — namespaced Swift constants  |
| `DesignTokens.kt`               | Android — namespaced Kotlin object|

Run `pnpm --filter @pandit/design-tokens build` (or `generate` to skip the
TS build) to regenerate all four from the schema. `tests/generate.test.ts`
asserts they stay in sync.

See also:
- [CONTRACT.md](./CONTRACT.md) — the base components the design team will skin, as contracts (props/slots/a11y), not finished components.
- [INTEGRATING-THE-DESIGN.md](./INTEGRATING-THE-DESIGN.md) — what the design team replaces (token values + skins) and why nothing else should change.

`tokens.placeholder.json` is kept as a legacy flat reference; `src/schema.ts`
is now the source of truth that generates everything.

## Rules

- Do NOT fill in real values. Do NOT invent colours, fonts, spacing, motion, or imagery.
- Reference tokens **by name** in all app code (CSS variables, Tailwind theme keys, Swift `DesignTokens`, Kotlin `DesignTokens`).
- When the Aqualeo design system is delivered: replace `schema.ts` *values* (keep names), regenerate, and supply component skins. No app-logic changes required — see INTEGRATING-THE-DESIGN.md.
