# Component Contracts

> These are **seams**, not finished components. Each entry describes the
> props/slots a base component exposes so the design team can skin it without
> touching app logic, and so app code never needs to know how it's skinned.
>
> TODO(design): the design team supplies the skin (markup structure beyond the
> contracted slots, classNames, native styles). The contract — names, props,
> slots, a11y behaviour — is stable and owned by engineering.

Conventions used below:
- **Slots** are named regions that accept arbitrary content (children).
- **Props** configure behaviour/state, not appearance.
- **a11y** lists the accessibility behaviour the shell guarantees regardless of skin.
- **Tokens used** lists the named token groups the shell reads (never hardcodes).

---

## Nav

Top-level / section navigation.

- Slots: `brand`, `items` (collection of nav links), `actions` (e.g. search, profile)
- Props: `activeHref: string`, `orientation: "horizontal" | "vertical"`, `collapsed?: boolean`
- a11y: `<nav>` landmark with `aria-label`; current item marked `aria-current="page"`; full keyboard navigation (arrow keys within `orientation="vertical"`, Tab order otherwise)
- Tokens used: `color.*`, `spacing.*`, `typography.*`, `motion.*` (collapse/expand)

## SectionHeader

Heading block introducing a page section (e.g. "Today's Panchang").

- Slots: `title`, `subtitle?`, `actions?` (e.g. a "see all" link)
- Props: `level: 1 | 2 | 3 | 4` (maps to semantic heading level)
- a11y: renders a real `<h{level}>`; `actions` are independently focusable
- Tokens used: `typography.*`, `spacing.*`, `color.*`

## Card

Generic content container (e.g. a day cell, a festival entry).

- Slots: `media?`, `header?`, `body`, `footer?`
- Props: `interactive?: boolean` (renders as a link/button when true), `selected?: boolean`
- a11y: when `interactive`, exposes a single accessible name and is reachable via keyboard with a visible focus ring; `selected` reflected via `aria-pressed`/`aria-selected` as appropriate to context
- Tokens used: `color.*`, `radius.*`, `shadow.*`, `spacing.*`

## CTA (Call to Action)

Primary/secondary action surface (button or button-styled link).

- Slots: `label`, `icon?`
- Props: `variant: "primary" | "secondary" | "ghost" | "destructive"`, `size: "sm" | "md" | "lg"`, `disabled?: boolean`, `loading?: boolean`, `as?: "button" | "a"`
- a11y: native `<button>` or `<a>` semantics (never a styled `<div>`); `loading` exposes `aria-busy`; `disabled` is a real disabled state, not visual-only
- Tokens used: `color.*`, `radius.*`, `typography.*`, `spacing.*`, `motion.*`

## Footer

Page/site footer.

- Slots: `links` (collection), `legal?`, `social?`
- Props: none (purely structural)
- a11y: `<footer>` landmark (`contentinfo` role implied at the page level)
- Tokens used: `color.*`, `spacing.*`, `typography.*`

## Buttons

See **CTA** for the interactive button contract. "Buttons" here covers
non-CTA utility buttons (icon buttons, toggle buttons, segmented controls).

- Slots: `icon?`, `label?` (at least one required)
- Props: `variant: "default" | "ghost"`, `pressed?: boolean`, `disabled?: boolean`, `aria-label?: string` (required if no visible `label`)
- a11y: icon-only buttons MUST receive an accessible name via `aria-label`; toggle state via `aria-pressed`
- Tokens used: `color.*`, `radius.*`, `spacing.*`, `motion.*`

## ListRow

Single row in a list (e.g. a reminder, a search result, a settings entry).

- Slots: `leading?` (icon/avatar), `primary` (title), `secondary?` (subtitle/meta), `trailing?` (action/affordance)
- Props: `interactive?: boolean`, `selected?: boolean`, `as?: "li" | "div"`
- a11y: when part of a list, parent provides `<ul>/<ol>` and row renders `<li>`; interactive rows behave like **Card**
- Tokens used: `color.*`, `spacing.*`, `typography.*`, `border` (divider)

## Modal

Overlay dialog (confirmations, detail views, pickers).

- Slots: `header` (title + optional close), `body`, `footer?` (actions)
- Props: `open: boolean`, `onClose: () => void`, `labelledBy?: string`, `size: "sm" | "md" | "lg" | "fullscreen"`
- a11y: `role="dialog"` + `aria-modal="true"`; focus is trapped and restored on close; `Escape` closes (unless explicitly disabled); background is `inert`/`aria-hidden`
- Tokens used: `color.*`, `radius.*`, `shadow.*`, `spacing.*`, `zIndex.modal`, `motion.*`

## FormField

Labelled input wrapper (text, select, date, etc. — wraps any control).

- Slots: `label`, `control` (the input itself), `hint?`, `error?`
- Props: `id: string`, `required?: boolean`, `invalid?: boolean`, `description?: string`
- a11y: `<label htmlFor>` association; `aria-describedby` wires `hint`/`error` to the control; `aria-invalid` reflects `invalid`; errors are announced (`role="alert"` or `aria-live="polite"`)
- Tokens used: `color.*`, `spacing.*`, `typography.*`, `radius.*`, `border`

---

## Cross-cutting behaviour every shell guarantees (token-driven, not skin-driven)

- **Visible focus ring**: every interactive element exposes a focus-visible
  outline driven by `color.ring` — the skin may restyle it but cannot remove it.
- **Reduced motion**: any transition/animation reads `motion.*` durations
  through a hook that resolves to `0ms` under `prefers-reduced-motion: reduce`
  (web) / `UIAccessibility.isReduceMotionEnabled` (iOS) /
  `Settings.System` animator-scale checks (Android).
- **Semantic roles/landmarks**: enumerated per-component above; the skin
  changes appearance, never the underlying element/role.
