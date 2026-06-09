"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { MonthScheme } from "@pandit/api-client-ts";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const MIN_YEAR_OFFSET = -2;
const MAX_YEAR_OFFSET = 1;

interface MonthNavProps {
  year: number;
  month: number; // 1-12
  monthScheme: MonthScheme;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onSchemeChange: (scheme: MonthScheme) => void;
  onLocationChange: () => void;
  locationLabel: string;
  fromCache?: boolean;
}

export function MonthNav({
  year,
  month,
  monthScheme,
  onPrevMonth,
  onNextMonth,
  onSchemeChange,
  onLocationChange,
  locationLabel,
  fromCache = false,
}: MonthNavProps): React.JSX.Element {
  const today = new Date();
  const todayYear = today.getFullYear();

  const canGoPrev = year > todayYear + MIN_YEAR_OFFSET || (year === todayYear + MIN_YEAR_OFFSET && month > 1);
  const canGoNext = year < todayYear + MAX_YEAR_OFFSET || (year === todayYear + MAX_YEAR_OFFSET && month < 12);

  const label = `${MONTH_NAMES[month - 1]} ${year}`;

  return (
    <header
      aria-label="Calendar navigation"
      className="flex flex-col gap-xs px-md py-sm border-b border-border"
    >
      {/* Month navigation row */}
      <div className="flex items-center justify-between gap-sm">
        <button
          type="button"
          aria-label="Previous month"
          disabled={!canGoPrev}
          onClick={onPrevMonth}
          className="p-xs text-foreground disabled:text-muted-foreground"
        >
          {/* TODO(design): replace with icon token */}
          ‹
        </button>

        <h1 className="text-lg font-semibold text-foreground">
          <time dateTime={`${year}-${String(month).padStart(2, "0")}`}>{label}</time>
        </h1>

        <button
          type="button"
          aria-label="Next month"
          disabled={!canGoNext}
          onClick={onNextMonth}
          className="p-xs text-foreground disabled:text-muted-foreground"
        >
          {/* TODO(design): replace with icon token */}
          ›
        </button>
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between gap-sm flex-wrap">
        {/* Location */}
        <button
          type="button"
          aria-label={`Change location: currently ${locationLabel}`}
          onClick={onLocationChange}
          className="text-sm text-muted-foreground underline"
        >
          {locationLabel}
        </button>

        {/* Amanta / Purnimanta toggle */}
        <div
          role="group"
          aria-label="Month scheme"
          className="flex gap-xs"
        >
          {(["amanta", "purnimanta"] as MonthScheme[]).map((scheme) => (
            <button
              key={scheme}
              type="button"
              role="radio"
              aria-checked={monthScheme === scheme}
              onClick={() => onSchemeChange(scheme)}
              className="text-xs px-sm py-xs border border-border rounded-md aria-[checked=true]:bg-accent aria-[checked=true]:text-accent-foreground"
            >
              {scheme === "amanta" ? "Amanta" : "Purnimanta"}
            </button>
          ))}
        </div>
      </div>

      {/* Offline / stale cache notice */}
      {fromCache && (
        <p role="status" aria-live="polite" className="text-xs text-muted-foreground">
          Showing cached calendar — you may be offline
        </p>
      )}
    </header>
  );
}
