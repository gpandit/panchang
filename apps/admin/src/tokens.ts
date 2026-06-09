/**
 * Design token references — all visual values flow through here.
 * TODO(design): Replace placeholder values with the Aqualeo design system tokens.
 *
 * Components must consume these constants, never hard-code colour/spacing/font values.
 */

export const tokens = {
  // ── Colour ─────────────────────────────────────────────────────────────────
  color: {
    surface:        "var(--color-surface,        #ffffff)",       // TODO(design)
    surfaceAlt:     "var(--color-surface-alt,     #f5f5f5)",      // TODO(design)
    border:         "var(--color-border,          #e0e0e0)",      // TODO(design)
    text:           "var(--color-text,            #1a1a1a)",      // TODO(design)
    textMuted:      "var(--color-text-muted,      #6b6b6b)",      // TODO(design)
    primary:        "var(--color-primary,         #4f46e5)",      // TODO(design)
    primaryText:    "var(--color-primary-text,    #ffffff)",      // TODO(design)
    danger:         "var(--color-danger,          #dc2626)",      // TODO(design)
    warning:        "var(--color-warning,         #d97706)",      // TODO(design)
    success:        "var(--color-success,         #16a34a)",      // TODO(design)
    info:           "var(--color-info,            #0284c7)",      // TODO(design)
    // Status badge colours
    statusDraft:    "var(--color-status-draft,    #6b7280)",      // TODO(design)
    statusReview:   "var(--color-status-review,   #d97706)",      // TODO(design)
    statusPublished:"var(--color-status-published,#16a34a)",      // TODO(design)
    statusRejected: "var(--color-status-rejected, #dc2626)",      // TODO(design)
    // Flag status
    flagOpen:       "var(--color-flag-open,       #dc2626)",      // TODO(design)
    flagResolved:   "var(--color-flag-resolved,   #16a34a)",      // TODO(design)
    flagDismissed:  "var(--color-flag-dismissed,  #6b7280)",      // TODO(design)
  },

  // ── Typography ─────────────────────────────────────────────────────────────
  font: {
    family:   "var(--font-family,   system-ui, sans-serif)",      // TODO(design)
    sizeBase: "var(--font-size-base, 0.875rem)",                  // TODO(design)
    sizeSm:   "var(--font-size-sm,   0.75rem)",                   // TODO(design)
    sizeLg:   "var(--font-size-lg,   1rem)",                      // TODO(design)
    sizeXl:   "var(--font-size-xl,   1.25rem)",                   // TODO(design)
    weightNormal: "var(--font-weight-normal, 400)",               // TODO(design)
    weightMedium: "var(--font-weight-medium, 500)",               // TODO(design)
    weightBold:   "var(--font-weight-bold,   700)",               // TODO(design)
  },

  // ── Spacing ────────────────────────────────────────────────────────────────
  space: {
    xs:  "var(--space-xs,  0.25rem)",                             // TODO(design)
    sm:  "var(--space-sm,  0.5rem)",                              // TODO(design)
    md:  "var(--space-md,  1rem)",                                // TODO(design)
    lg:  "var(--space-lg,  1.5rem)",                              // TODO(design)
    xl:  "var(--space-xl,  2rem)",                                // TODO(design)
  },

  // ── Radius ─────────────────────────────────────────────────────────────────
  radius: {
    sm:  "var(--radius-sm,  0.25rem)",                            // TODO(design)
    md:  "var(--radius-md,  0.5rem)",                             // TODO(design)
    lg:  "var(--radius-lg,  0.75rem)",                            // TODO(design)
  },

  // ── Shadow ─────────────────────────────────────────────────────────────────
  shadow: {
    sm:  "var(--shadow-sm,  0 1px 2px rgba(0,0,0,0.05))",        // TODO(design)
    md:  "var(--shadow-md,  0 4px 6px rgba(0,0,0,0.07))",        // TODO(design)
  },
} as const;
