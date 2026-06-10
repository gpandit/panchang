/**
 * Aqualeo design system tokens — dark canvas, single aqua accent.
 * Per spec §10.2: admin console uses Aqualeo (dark/aqua) while the
 * consumer app uses the Festival direction (saffron/maroon/gold).
 *
 * All colour values are direct from the Aqualeo admin design prototype.
 * Components consume these; never hardcode colour/spacing/font values.
 */

export const tokens = {
  // ── Colour ─────────────────────────────────────────────────────────────────
  color: {
    // Surfaces — dark canvas hierarchy
    surface: "#141A1F",       // panel background
    surfaceAlt: "#0D1115",    // page/canvas background
    surfaceRaised: "#1C252C", // elevated card / popover
    surfaceCard: "#161D23",   // card background

    // Borders
    border: "rgba(255,255,255,0.08)",
    borderHi: "rgba(255,255,255,0.14)",

    // Text
    text: "#E7EEF1",          // primary text
    textBody: "#A7B5BE",      // body / secondary text
    textMuted: "#7C8B95",     // muted text
    textFaint: "#56646D",     // placeholder / disabled

    // Accent — single aqua
    primary: "#33D6C2",
    primaryText: "#0D1115",   // dark text on aqua background
    primaryDim: "rgba(51,214,194,0.14)",
    primaryLine: "rgba(51,214,194,0.40)",

    // Semantic
    danger: "#E05C5C",
    warning: "#E0B341",
    success: "#33D6C2",       // aqua doubles as success
    info: "#2A91B8",

    // Content lifecycle status badges
    statusDraft: "#8A99A3",
    statusReview: "#E0B341",
    statusPublished: "#33D6C2",
    statusRejected: "#E05C5C",

    // Flag queue status
    flagOpen: "#E05C5C",
    flagResolved: "#33D6C2",
    flagDismissed: "#56646D",
  },

  // ── Typography ─────────────────────────────────────────────────────────────
  font: {
    family: "'Hanken Grotesk', system-ui, sans-serif",
    mono: "'Jost', ui-monospace, monospace",
    sizeBase: "0.875rem",
    sizeSm: "0.75rem",
    sizeLg: "1rem",
    sizeXl: "1.25rem",
    size2xl: "1.5rem",
    weightNormal: "400",
    weightMedium: "500",
    weightBold: "700",
  },

  // ── Spacing ────────────────────────────────────────────────────────────────
  space: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem",
  },

  // ── Radius ─────────────────────────────────────────────────────────────────
  radius: {
    sm: "0.5rem",
    md: "0.625rem",
    lg: "0.875rem",
  },

  // ── Shadow ─────────────────────────────────────────────────────────────────
  shadow: {
    sm: "0 1px 3px rgba(0,0,0,0.3)",
    md: "0 4px 12px rgba(0,0,0,0.4)",
  },
} as const;
