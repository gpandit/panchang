/**
 * Canonical design token schema — THE single source of truth.
 *
 * TODO(design): every value below is a neutral placeholder. The Aqualeo
 * design team replaces these values only; names and structure are the
 * stable seam that app code, native code, and generators all depend on.
 *
 * Do NOT add real colours, fonts, scales, shadows, motion curves, etc.
 * here. Add a *named slot* with a placeholder value and move on.
 */

export interface TokenEntry {
  /** Stable name referenced by app code, e.g. "color.primary". */
  name: string;
  /** Neutral placeholder value, valid enough to render without crashing. */
  value: string;
  /** Always true until the design system lands. */
  todoDesign: true;
}

export type TokenGroup = Record<string, TokenEntry>;

export interface TokenSchema {
  color: TokenGroup;
  typography: TokenGroup;
  spacing: TokenGroup;
  radius: TokenGroup;
  shadow: TokenGroup;
  motion: TokenGroup;
  zIndex: TokenGroup;
  breakpoint: TokenGroup;
}

function group(prefix: string, entries: Record<string, string>): TokenGroup {
  const out: TokenGroup = {};
  for (const [key, value] of Object.entries(entries)) {
    out[key] = { name: `${prefix}.${key}`, value, todoDesign: true };
  }
  return out;
}

/**
 * Neutral placeholder values. Each is a syntactically valid value for its
 * category (so the app renders without errors) but carries no design intent —
 * grayscale colours, system fonts, an unscaled spacing ramp, zero motion.
 */
export const tokens: TokenSchema = {
  color: group("color", {
    primary: "#808080",
    "primary-foreground": "#ffffff",
    secondary: "#a0a0a0",
    "secondary-foreground": "#ffffff",
    background: "#ffffff",
    foreground: "#1a1a1a",
    muted: "#e0e0e0",
    "muted-foreground": "#5a5a5a",
    accent: "#c0c0c0",
    "accent-foreground": "#1a1a1a",
    destructive: "#b00020",
    "destructive-foreground": "#ffffff",
    border: "#d0d0d0",
    ring: "#808080",
    auspicious: "#808080",
    inauspicious: "#808080",
  }),
  typography: group("typography", {
    "font-family-base": "system-ui, sans-serif",
    "font-family-display": "system-ui, sans-serif",
    "font-family-devanagari": "system-ui, sans-serif",
    "weight-regular": "400",
    "weight-medium": "500",
    "weight-bold": "700",
    "scale-xs": "0.75rem",
    "scale-sm": "0.875rem",
    "scale-base": "1rem",
    "scale-lg": "1.125rem",
    "scale-xl": "1.25rem",
    "scale-2xl": "1.5rem",
    "scale-3xl": "1.875rem",
    "leading-tight": "1.2",
    "leading-normal": "1.5",
    "leading-relaxed": "1.75",
  }),
  spacing: group("spacing", {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem",
    "2xl": "3rem",
  }),
  radius: group("radius", {
    sm: "0.125rem",
    md: "0.25rem",
    lg: "0.5rem",
    full: "9999px",
  }),
  shadow: group("shadow", {
    sm: "0 1px 2px rgba(0,0,0,0.08)",
    md: "0 2px 6px rgba(0,0,0,0.10)",
    lg: "0 6px 16px rgba(0,0,0,0.12)",
  }),
  motion: group("motion", {
    "duration-fast": "100ms",
    "duration-base": "200ms",
    "duration-slow": "320ms",
    "easing-standard": "cubic-bezier(0.2, 0, 0, 1)",
    "easing-decelerate": "cubic-bezier(0, 0, 0, 1)",
    "easing-accelerate": "cubic-bezier(0.3, 0, 1, 1)",
  }),
  zIndex: group("zIndex", {
    base: "0",
    dropdown: "1000",
    sticky: "1100",
    overlay: "1200",
    modal: "1300",
    toast: "1400",
  }),
  breakpoint: group("breakpoint", {
    sm: "640px",
    md: "768px",
    lg: "1024px",
    xl: "1280px",
    "2xl": "1536px",
  }),
};

export function flatten(schema: TokenSchema): TokenEntry[] {
  return Object.values(schema).flatMap((g) => Object.values(g));
}
