"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { CalendarDayCell } from "./types";
import { DayCell } from "./DayCell";

const DOW_SHORT = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
const DOW_FULL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

interface MonthViewProps {
  cells: CalendarDayCell[];
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  monthLabel: string; // "June 2026" — for aria-label
  loadState: "idle" | "loading" | "success" | "error";
  error: string | null;
  onRetry: () => Promise<void>;
}

export function MonthView({
  cells,
  selectedDate,
  onSelectDate,
  monthLabel,
  loadState,
  error,
  onRetry,
}: MonthViewProps): React.JSX.Element {
  if (loadState === "loading" || loadState === "idle") {
    return (
      <div
        role="status"
        aria-label="Loading calendar"
        aria-live="polite"
        className="flex flex-1 items-center justify-center p-xl text-muted-foreground"
      >
        Loading…
      </div>
    );
  }

  if (loadState === "error" && !cells.length) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        className="flex flex-col flex-1 items-center justify-center gap-md p-xl text-center"
      >
        <p className="text-sm text-muted-foreground">
          {error === "offline"
            ? "You're offline and no cached calendar is available."
            : "Unable to load calendar. Please try again."}
        </p>
        <button
          type="button"
          onClick={() => void onRetry()}
          className="text-sm text-primary underline"
          aria-label="Retry loading calendar"
        >
          Retry
        </button>
      </div>
    );
  }

  // Split cells into rows of 7
  const rows: CalendarDayCell[][] = [];
  for (let i = 0; i < cells.length; i += 7) {
    rows.push(cells.slice(i, i + 7));
  }

  return (
    <section aria-label={`Calendar for ${monthLabel}`} className="flex flex-col">
      {/* Day-of-week header */}
      <div role="row" className="grid grid-cols-7 border-t border-l border-border">
        {DOW_SHORT.map((short, i) => (
          <div
            key={short}
            role="columnheader"
            aria-label={DOW_FULL[i]}
            className="p-xs text-xs text-center text-muted-foreground font-medium border-b border-r border-border"
          >
            {short}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div
        role="grid"
        aria-label={`${monthLabel} dates`}
        aria-rowcount={rows.length}
        aria-colcount={7}
        className="border-l border-border"
      >
        {rows.map((week, rowIdx) => (
          <div
            key={week[0]!.date}
            role="row"
            aria-rowindex={rowIdx + 1}
            className="grid grid-cols-7"
          >
            {week.map((cell, colIdx) => (
              <DayCell
                key={cell.date}
                cell={cell}
                isSelected={cell.date === selectedDate}
                onSelect={onSelectDate}
                // Pass aria-colindex via data attr; DayCell wraps in gridcell
                aria-colindex={colIdx + 1}
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
