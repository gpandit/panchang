"use client";

import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

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
      className="flex rounded-md border border-border overflow-hidden"
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
            className={[
              "px-sm py-xs text-sm flex-1",
              isSelected ? "bg-primary text-primary-foreground" : "bg-background text-foreground",
            ].join(" ")}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
