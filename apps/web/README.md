# apps/web — The Pandit Web App

**Status: minimal scaffold (Stage 0, Step 0.3) — full app build is Stage 3.**

Stack: Next.js (App Router) · TypeScript · Tailwind CSS

This surface is a thin client. All Panchang data comes from `services/api`.
No Panchang computation happens here.

Design tokens are consumed from `@pandit/design-tokens` — do not hardcode
visual values; Tailwind is wired to the generated token preset
(`tailwind.config.ts`) which resolves to CSS custom properties
(`src/app/globals.css` imports `@pandit/design-tokens/css`).

This scaffold exists primarily to host the themeable component shells
described in `packages/design-tokens/CONTRACT.md`. See
`/__dev/components` (`src/app/__dev/components/page.tsx`) for the structural
preview — every shell is intentionally unstyled beyond tokens and
accessibility behaviour, marked `// TODO(design): skin via Aqualeo design system`.
