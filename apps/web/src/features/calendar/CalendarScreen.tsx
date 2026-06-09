"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { MonthScheme } from "@pandit/api-client-ts";
import { useMonthCalendar, useNotes, useReminders, useOfflineSync } from "./hooks";
import { MonthNav } from "./MonthNav";
import { MonthView } from "./MonthView";
import { DayView } from "./DayView";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export interface CalendarScreenProps {
  latitude: number;
  longitude: number;
  timezone: string;
  locationLabel: string;
  /** Optional: initial month to display. Defaults to the current month. */
  initialYear?: number;
  initialMonth?: number; // 1-12
  token?: string;
}

export function CalendarScreen({
  latitude,
  longitude,
  timezone,
  locationLabel,
  initialYear,
  initialMonth,
  token,
}: CalendarScreenProps): React.JSX.Element {
  const today = new Date();
  const [year, setYear] = useState(initialYear ?? today.getFullYear());
  const [month, setMonth] = useState(initialMonth ?? today.getMonth() + 1);
  const [monthScheme, setMonthScheme] = useState<MonthScheme>("amanta");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const router = useRouter();

  // ── Data hooks ───────────────────────────────────────────────────────────
  const { notes, createNote, updateNote, deleteNote } = useNotes(token);
  const { reminders, createReminder, deleteReminder } = useReminders(token);
  const { cells, loadState, fromCache, error, refresh } = useMonthCalendar(
    { year, month, lat: latitude, lon: longitude, tz: timezone, monthScheme },
    notes,
  );
  const { pendingCount } = useOfflineSync(token);

  // ── Navigation ───────────────────────────────────────────────────────────
  function prevMonth(): void {
    if (month === 1) { setYear((y) => y - 1); setMonth(12); }
    else setMonth((m) => m - 1);
    setSelectedDate(null);
  }

  function nextMonth(): void {
    if (month === 12) { setYear((y) => y + 1); setMonth(1); }
    else setMonth((m) => m + 1);
    setSelectedDate(null);
  }

  const handleLocationChange = useCallback(() => {
    router.push("/settings/location");
  }, [router]);

  const handleSchemeChange = useCallback((scheme: MonthScheme) => {
    setMonthScheme(scheme);
  }, []);

  // ── Selected cell ────────────────────────────────────────────────────────
  const selectedCell = selectedDate ? (cells.find((c) => c.date === selectedDate) ?? null) : null;

  const monthLabel = `${MONTH_NAMES[month - 1]} ${year}`;

  return (
    <main aria-label="Calendar" className="flex flex-col min-h-screen bg-background">
      {/* Offline sync notice */}
      {pendingCount > 0 && (
        <div
          role="status"
          aria-live="polite"
          className="text-xs text-muted-foreground text-center px-md py-xs border-b border-border"
        >
          {pendingCount} change{pendingCount !== 1 ? "s" : ""} pending sync
        </div>
      )}

      {/* Month navigation */}
      <MonthNav
        year={year}
        month={month}
        monthScheme={monthScheme}
        onPrevMonth={prevMonth}
        onNextMonth={nextMonth}
        onSchemeChange={handleSchemeChange}
        onLocationChange={handleLocationChange}
        locationLabel={locationLabel}
        fromCache={fromCache}
      />

      {/* Month grid */}
      <MonthView
        cells={cells}
        selectedDate={selectedDate}
        onSelectDate={(date) => setSelectedDate((prev) => prev === date ? null : date)}
        monthLabel={monthLabel}
        loadState={loadState}
        error={error}
        onRetry={refresh}
      />

      {/* Day detail panel — shown when a date is selected */}
      {selectedCell && (
        <DayView
          cell={selectedCell}
          notes={notes}
          reminders={reminders}
          onClose={() => setSelectedDate(null)}
          onCreateNote={async (noteIn) => { await createNote(noteIn); }}
          onUpdateNote={async (id, noteIn) => { await updateNote(id, noteIn); }}
          onDeleteNote={async (id) => { await deleteNote(id); }}
          onCreateReminder={async (r) => { await createReminder(r); }}
          onDeleteReminder={async (id) => { await deleteReminder(id); }}
        />
      )}
    </main>
  );
}
