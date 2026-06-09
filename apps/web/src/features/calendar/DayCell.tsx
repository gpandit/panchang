"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { CalendarDayCell } from "./types";

interface DayCellProps {
  cell: CalendarDayCell;
  isSelected: boolean;
  onSelect: (date: string) => void;
}

const MOON_MARKERS: Record<string, string> = {
  new: "○",    // TODO(design): replace with icon token
  full: "●",   // TODO(design): replace with icon token
};

export function DayCell({ cell, isSelected, onSelect }: DayCellProps): React.JSX.Element {
  const { date, dayOfMonth, isCurrentMonth, isToday, markers } = cell;

  const descParts: string[] = [date];
  if (markers.tithi) descParts.push(markers.tithi);
  if (markers.festivals.length) descParts.push(...markers.festivals);
  if (markers.vrats.length) descParts.push(...markers.vrats);
  if (markers.hasNote) descParts.push("has note");
  if (markers.hasBookmark) descParts.push("bookmarked");

  return (
    <div
      role="gridcell"
      className={[
        "relative flex flex-col p-xs min-h-[3.5rem] border-b border-r border-border",
        isCurrentMonth ? "bg-background text-foreground" : "bg-muted text-muted-foreground",
      ].join(" ")}
    >
      <button
        type="button"
        aria-label={descParts.join(", ")}
        aria-pressed={isSelected}
        aria-current={isToday ? "date" : undefined}
        onClick={() => onSelect(date)}
        className="flex flex-col items-start gap-xs w-full text-left"
      >
        <span
          className={[
            "text-sm leading-none",
            isToday ? "font-bold underline" : "",
          ].join(" ")}
        >
          {dayOfMonth}
        </span>

        {isCurrentMonth && markers.tithi && (
          <span
            aria-hidden="true"
            className="text-xs text-muted-foreground truncate max-w-full leading-tight"
          >
            {markers.tithi}
          </span>
        )}
      </button>

      {/* Data-driven marker slots — TODO(design): replace text with icon tokens */}
      {isCurrentMonth && (
        <div className="flex gap-xs mt-auto" aria-hidden="true">
          {MOON_MARKERS[markers.moonPhase] && (
            <span
              data-marker={`moon-${markers.moonPhase}`}
              className="text-xs leading-none"
              title={markers.moonPhase === "full" ? "Purnima" : "Amavasya"}
            >
              {MOON_MARKERS[markers.moonPhase]}
            </span>
          )}
          {markers.festivals.map((name) => (
            <span
              key={name}
              data-marker="festival"
              className="text-xs leading-none"
              title={name}
            >
              {/* TODO(design): festival icon token */}
              ✦
            </span>
          ))}
          {markers.vrats.map((name) => (
            <span
              key={name}
              data-marker="vrat"
              className="text-xs leading-none"
              title={name}
            >
              {/* TODO(design): vrat icon token */}
              ✧
            </span>
          ))}
          {markers.hasNote && (
            <span data-marker="note" className="text-xs leading-none" title="Note">
              {/* TODO(design): note icon token */}
              ¶
            </span>
          )}
          {markers.hasBookmark && (
            <span data-marker="bookmark" className="text-xs leading-none" title="Bookmarked">
              {/* TODO(design): bookmark icon token */}
              ⊠
            </span>
          )}
        </div>
      )}
    </div>
  );
}
