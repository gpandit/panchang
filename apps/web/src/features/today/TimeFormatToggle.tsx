"use client";

import type { JSX } from "react";
import type { TimeFormat } from "@pandit/api-client-ts";

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
      style={{ background: "#FFEFD9", border: "1px solid rgba(124,29,43,0.16)" }}
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
              background: isSelected ? "#7C1D2B" : "transparent",
              color: isSelected ? "#FFF6EA" : "#6A4231",
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
