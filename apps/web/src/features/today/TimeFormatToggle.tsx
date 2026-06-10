"use client";

import type { JSX } from "react";
import type { TimeFormat } from "@pandit/api-client-ts";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

const OPTIONS: { value: TimeFormat; label: string; ariaLabel: string }[] = [
  { value: "12h", label: "12h", ariaLabel: "12-hour clock" },
  { value: "24h", label: "24h", ariaLabel: "24-hour clock" },
  { value: "24plus", label: "24+", ariaLabel: "24-plus clock (past-midnight hours continue)" },
];

interface TimeFormatToggleProps {
  value: TimeFormat;
  onChange: (f: TimeFormat) => void;
}

export function TimeFormatToggle({ value, onChange }: TimeFormatToggleProps): JSX.Element {
  return (
    <div
      role="group"
      aria-label="Time display format"
      className="flex rounded-full overflow-hidden p-0.5"
      style={{ background: "var(--color-warm)", border: "1px solid var(--color-border)" }}
    >
      {OPTIONS.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={opt.ariaLabel}
            onClick={() => onChange(opt.value)}
            className="px-3 py-1.5 text-xs font-semibold rounded-full transition-all"
            style={{
              background: isSelected ? "var(--color-primary)" : "transparent",
              color: isSelected ? "var(--color-primary-foreground)" : "var(--color-body)",
              letterSpacing: "0.02em",
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
