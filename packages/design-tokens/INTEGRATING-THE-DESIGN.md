# Integrating the Aqualeo Design System

This document is for whoever lands the real design system (the Aqualeo team,
or an engineer integrating their deliverables). It describes the **only**
two things that should change, and why nothing else needs to.

## The seam

App logic references **named tokens** and **contracted component slots/props**
(see [CONTRACT.md](./CONTRACT.md)) — never raw colours, fonts, spacing, or
markup structure. That indirection is the seam. Replacing what's on the design
side of the seam should require **zero changes** on the logic side.

## What you replace

### 1. Token *values* in `src/schema.ts`

Every entry in the schema (`packages/design-tokens/src/schema.ts`) currently
holds a neutral placeholder marked `TODO(design)`. Replace the `value` of each
entry with the real Aqualeo value:

- Keep every **name** (`color.primary`, `spacing.md`, `motion.duration-base`, …)
  exactly as-is — app code, native code, and Tailwind all reference tokens by
  name.
- You may **add** new named tokens if the design system needs slots that don't
  exist yet (e.g. a new semantic colour). Don't repurpose an existing name for
  a different meaning.
- Remove the `todoDesign: true` marker only for entries you've supplied a real
  value for, and delete the `TODO(design)` comment headers once the whole
  schema is real.

Then regenerate every client output from the single source:

```sh
pnpm --filter @pandit/design-tokens build
```

This rewrites `generated/tokens.css`, `generated/tailwind-preset.js`,
`generated/DesignTokens.swift`, and `generated/DesignTokens.kt` — the four
formats web, the Tailwind config, iOS, and Android consume. The
token-generation test (`tests/generate.test.ts`) asserts these stay in sync
with the schema; run `pnpm --filter @pandit/design-tokens test` to confirm.

### 2. Component *skins*

Each base component shell (web: `apps/web/src/components/primitives/*`; native:
the SwiftUI views / Compose composables that implement the contracts in
[CONTRACT.md](./CONTRACT.md)) is intentionally unstyled beyond structure,
tokens, and accessibility behaviour, and is marked:

```
// TODO(design): skin via Aqualeo design system
```

Skinning means supplying the visual layer — markup/view structure for
decorative elements, classNames/styles that consume the new token values,
imagery, icons, motion. It does **not** mean changing the props, slots, or
accessibility guarantees the contract specifies; those are the part app code
depends on.

## What should need zero changes

- Screen/route composition, navigation, state management, data fetching.
- Any code that references a component via its contracted props/slots.
- Any code that references a token by name.

If you find yourself needing to change app logic to fit the new design, the
seam has a gap — raise it as a contract change (update CONTRACT.md +
schema.ts together) rather than special-casing the design system in app code.

## Pending work that activates once real tokens land

`tests/generate.test.ts` includes a skipped contrast-ratio test
(`"WCAG contrast ratios — cannot evaluate meaningfully on neutral
placeholders"`). Un-skip it and implement the WCAG AA assertions
(4.5:1 for text, 3:1 for large text/UI) for the real `color.*` pairs once they
exist — placeholder grayscale values would make that check meaningless today.
