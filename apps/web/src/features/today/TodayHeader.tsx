// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { Location } from "@pandit/api-client-ts";

interface TodayHeaderProps {
  locationLabel: string;
  location: Location;
  date: string; // "YYYY-MM-DD" — the Panchang date being viewed
  panchangHindiDate: string; // Formatted traditional date string
  onLocationChange?: () => void;
  onPrevDay?: () => void;
  onNextDay?: () => void;
  /** Disable forward navigation when viewing the furthest cached day. */
  canGoForward?: boolean;
  canGoBack?: boolean;
}

export function TodayHeader({
  locationLabel,
  date,
  panchangHindiDate,
  onLocationChange,
  onPrevDay,
  onNextDay,
  canGoForward = true,
  canGoBack = true,
}: TodayHeaderProps): React.JSX.Element {
  return (
    <header className="flex flex-col gap-xs px-md py-sm" aria-label="Date and location">
      {/* Location row */}
      <div className="flex items-center justify-between gap-sm">
        <div>
          <span className="text-sm text-muted-foreground" aria-label="Current location">
            {locationLabel}
          </span>
        </div>
        {onLocationChange ? (
          <button
            type="button"
            className="text-sm text-primary underline"
            onClick={onLocationChange}
            aria-label="Change location"
          >
            Change
          </button>
        ) : null}
      </div>

      {/* Date navigation row */}
      <div className="flex items-center justify-between gap-sm">
        <button
          type="button"
          className="text-sm px-sm py-xs rounded-sm border border-border"
          onClick={onPrevDay}
          disabled={!canGoBack}
          aria-label="Previous day"
        >
          ‹
        </button>

        <div className="flex flex-col items-center gap-xs flex-1">
          <time
            dateTime={date}
            className="text-lg font-display"
            aria-label={`Gregorian date: ${date}`}
          >
            {formatGregorianDate(date)}
          </time>
          <span className="text-sm text-muted-foreground">{panchangHindiDate}</span>
        </div>

        <button
          type="button"
          className="text-sm px-sm py-xs rounded-sm border border-border"
          onClick={onNextDay}
          disabled={!canGoForward}
          aria-label="Next day"
        >
          ›
        </button>
      </div>
    </header>
  );
}

function formatGregorianDate(date: string): string {
  try {
    const d = new Date(`${date}T12:00:00`); // noon to avoid TZ edge cases
    return d.toLocaleDateString("en-IN", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return date;
  }
}
