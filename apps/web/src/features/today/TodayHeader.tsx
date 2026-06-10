import type { JSX } from "react";
import { MapPin, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";

interface TodayHeaderProps {
  locationLabel: string;
  date: string; // "YYYY-MM-DD" — the Panchang date being viewed
  panchangHindiDate: string;
  weekday: string;
  onLocationChange?: () => void;
  onPrevDay?: () => void;
  onNextDay?: () => void;
  canGoForward?: boolean;
  canGoBack?: boolean;
}

export function TodayHeader({
  locationLabel,
  date,
  panchangHindiDate,
  weekday,
  onLocationChange,
  onPrevDay,
  onNextDay,
  canGoForward = true,
  canGoBack = true,
}: TodayHeaderProps): JSX.Element {
  const { day, month, year } = parseDate(date);

  return (
    <header
      className="arch-motif relative flex flex-col gap-0 pb-10"
      style={{
        background: "linear-gradient(160deg, #7C1D2B, #5A1320)",
        borderRadius: "0 0 1.75rem 1.75rem",
      }}
      aria-label="Date and location"
    >
      {/* top bar: location + day nav */}
      <div className="flex items-center justify-between px-6 pt-4 pb-0">
        <button
          type="button"
          className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold transition-opacity hover:opacity-80"
          style={{
            border: "1px solid rgba(255,255,255,0.25)",
            background: "rgba(255,255,255,0.10)",
            color: "#FFF1E0",
          }}
          onClick={onLocationChange}
          aria-label="Change location"
        >
          <MapPin size={14} style={{ color: "#E0A93E" }} aria-hidden="true" />
          <span className="max-w-[160px] truncate">{locationLabel}</span>
          <ChevronDown size={13} style={{ color: "rgba(255,241,224,0.7)" }} aria-hidden="true" />
        </button>

        {/* day navigation */}
        <div className="flex items-center gap-2">
          <NavBtn
            onClick={onPrevDay}
            disabled={!canGoBack}
            aria-label="Previous day"
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </NavBtn>
          <NavBtn
            onClick={onNextDay}
            disabled={!canGoForward}
            aria-label="Next day"
          >
            <ChevronRight size={16} aria-hidden="true" />
          </NavBtn>
        </div>
      </div>

      {/* centred date display */}
      <div className="mt-3 flex flex-col items-center text-center">
        <p
          className="text-xs font-bold uppercase tracking-widest"
          style={{ color: "#E0A93E", letterSpacing: "0.2em" }}
        >
          {weekday} · Today
        </p>
        <time
          dateTime={date}
          className="mt-1.5 font-display leading-none"
          style={{ fontFamily: "'Marcellus', Georgia, serif", fontSize: "2.4rem", color: "#FFF6EA" }}
        >
          {weekday}, {day} {month}
        </time>
        <p
          className="mt-1.5 font-display"
          style={{
            fontFamily: "'Marcellus', Georgia, serif",
            fontSize: "1.1rem",
            color: "rgba(255,241,224,0.85)",
          }}
        >
          {panchangHindiDate}
          <span className="ml-2" style={{ color: "#E0A93E" }}>
            {year}
          </span>
        </p>
      </div>
    </header>
  );
}

function NavBtn({
  children,
  onClick,
  disabled,
  "aria-label": ariaLabel,
}: {
  children: JSX.Element;
  onClick: (() => void) | undefined;
  disabled: boolean | undefined;
  "aria-label": string;
}): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className="flex h-9 w-9 items-center justify-center rounded-full transition-opacity disabled:opacity-30"
      style={{
        background: "rgba(255,255,255,0.10)",
        border: "1px solid rgba(255,255,255,0.18)",
        color: "#FFF1E0",
      }}
    >
      {children}
    </button>
  );
}

function parseDate(iso: string): { day: string; month: string; year: string } {
  try {
    const d = new Date(`${iso}T12:00:00`);
    return {
      day: String(d.getDate()),
      month: d.toLocaleDateString("en-IN", { month: "long" }),
      year: String(d.getFullYear()),
    };
  } catch {
    return { day: "", month: "", year: iso };
  }
}
