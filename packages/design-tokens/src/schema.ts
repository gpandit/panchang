/**
 * Canonical design token schema — THE single source of truth.
 *
 * Visual theme: Festival direction — saffron/maroon/gold on cream (web + mobile),
 * Aqualeo dark/aqua for the admin console.
 * Fonts: Marcellus (display) + Mukta (body/sans) from Google Fonts.
 *
 * Names and structure are the stable seam that app code, native code,
 * and generators all depend on. Do not rename tokens; update values only.
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
 * Festival direction palette: saffron/maroon/gold on cream.
 * Semantic mappings:
 *   primary    = maroon  (#7C1D2B) — nav rail, header bands, CTA backgrounds
 *   accent     = saffron (#DC5F1B) — highlights, icons, active states
 *   secondary  = gold    (#C4912F) — labels, borders, ornamental details
 *   background = cream   (#FFF6EA) — page canvas
 *   foreground = ink     (#3A1A11) — body text
 *   muted      = warm mid (#9E7A63) — secondary text, placeholders
 */
export const tokens: TokenSchema = {
  color: group("color", {
    // Core semantic roles
    primary: "#7C1D2B",
    "primary-foreground": "#FFF6EA",
    secondary: "#C4912F",
    "secondary-foreground": "#3A1A11",
    background: "#FFF6EA",
    foreground: "#3A1A11",
    muted: "#FFEFD9",
    "muted-foreground": "#9E7A63",
    accent: "#DC5F1B",
    "accent-foreground": "#ffffff",
    destructive: "#B23A1E",
    "destructive-foreground": "#ffffff",
    border: "rgba(124,29,43,0.16)",
    ring: "#DC5F1B",
    // Domain-specific
    auspicious: "#5C6B36",
    inauspicious: "#B23A1E",
    // Extended palette (consumed via CSS variables directly)
    "maroon-deep": "#5A1320",
    "maroon-mid": "#611521",
    "saffron-hi": "#EE7A2D",
    "gold-hi": "#E0A93E",
    "gold-deep": "#9A6E1E",
    "gold-pale": "#EAD7A6",
    paper: "#FFFFFF",
    warm: "#FFEFD9",
    "warm-2": "#FCE7CC",
    ink: "#3A1A11",
    body: "#6A4231",
    mute: "#9E7A63",
    faint: "#C2A488",
    "line-soft": "rgba(124,29,43,0.08)",
    "auspicious-bg": "rgba(92,107,54,0.10)",
    "inauspicious-bg": "rgba(178,58,30,0.08)",
  }),
  typography: group("typography", {
    "font-family-base": "'Mukta', system-ui, sans-serif",
    "font-family-display": "'Marcellus', Georgia, serif",
    "font-family-devanagari": "'Mukta', system-ui, sans-serif",
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
    sm: "0.375rem",
    md: "0.625rem",
    lg: "0.875rem",
    full: "9999px",
  }),
  shadow: group("shadow", {
    sm: "0 1px 2px rgba(90,19,32,0.08)",
    md: "0 4px 12px rgba(90,19,32,0.12)",
    lg: "0 14px 36px -24px rgba(90,19,32,0.50)",
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
