/**
 * Pure functions for deriving calendar day-cell markers from API payloads.
 * No Panchang math lives here — all values are read from server-provided data.
 */

import type { DailyPanchangOut, FestivalOut } from "@pandit/api-client-ts";
import type {
  CalendarDayCell,
  CalendarMonthData,
  DayCellMarkers,
  LocalNote,
  MoonPhase,
} from "./types";

export function deriveMoonPhase(day: DailyPanchangOut): MoonPhase {
  const tithiIndex = day.tithi[0]?.index ?? 0;
  if (tithiIndex === 30 || tithiIndex === 0) return "new";   // Amavasya
  if (tithiIndex === 15) return "full";                       // Purnima
  const paksha = day.calendrical.paksha.toLowerCase();
  return paksha.includes("shukla") ? "waxing" : "waning";
}

export function deriveDayCellMarkers(
  day: DailyPanchangOut,
  allFestivals: FestivalOut[],
  allNotes: LocalNote[],
): DayCellMarkers {
  const dayFestivals = allFestivals.filter((f) => f.date === day.date);
  const festivals = dayFestivals.filter((f) => !f.tags.includes("vrat")).map((f) => f.name);
  const vrats = dayFestivals.filter((f) => f.tags.includes("vrat")).map((f) => f.name);
  const hasNote = allNotes.some((n) => n.date === day.date && !n.tags.includes("bookmark"));
  const hasBookmark = allNotes.some((n) => n.date === day.date && n.tags.includes("bookmark"));

  return {
    tithi: day.tithi[0]?.name ?? null,
    moonPhase: deriveMoonPhase(day),
    festivals,
    vrats,
    hasNote,
    hasBookmark,
  };
}

function isoDate(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function emptyMarkers(): DayCellMarkers {
  return { tithi: null, moonPhase: "waxing", festivals: [], vrats: [], hasNote: false, hasBookmark: false };
}

/**
 * Build a 42-cell (6×7) grid for the month view.
 * Padding cells from the previous and next months are included with
 * isCurrentMonth=false and null panchang data.
 */
export function buildDayGrid(
  data: CalendarMonthData,
  notes: LocalNote[],
  todayISO: string,
): CalendarDayCell[] {
  const { year, month, days, festivals } = data;
  const dayMap = new Map<string, DailyPanchangOut>(days.map((d) => [d.date, d]));

  // Use UTC constructor to avoid local-timezone day shifts
  const firstDow = new Date(Date.UTC(year, month - 1, 1)).getUTCDay(); // 0=Sun
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();

  const prevYear = month === 1 ? year - 1 : year;
  const prevMonth = month === 1 ? 12 : month - 1;
  const daysInPrevMonth = new Date(Date.UTC(prevYear, prevMonth, 0)).getUTCDate();

  const nextYear = month === 12 ? year + 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;

  const cells: CalendarDayCell[] = [];

  // Leading padding from previous month
  for (let i = 0; i < firstDow; i++) {
    const dom = daysInPrevMonth - (firstDow - 1 - i);
    const dateStr = isoDate(prevYear, prevMonth, dom);
    cells.push({ date: dateStr, dayOfMonth: dom, isCurrentMonth: false, isToday: dateStr === todayISO, markers: emptyMarkers(), panchang: null });
  }

  // Current month
  for (let dom = 1; dom <= daysInMonth; dom++) {
    const dateStr = isoDate(year, month, dom);
    const panchang = dayMap.get(dateStr) ?? null;
    cells.push({
      date: dateStr,
      dayOfMonth: dom,
      isCurrentMonth: true,
      isToday: dateStr === todayISO,
      markers: panchang ? deriveDayCellMarkers(panchang, festivals, notes) : emptyMarkers(),
      panchang,
    });
  }

  // Trailing padding to fill the last row
  const trailing = (7 - (cells.length % 7)) % 7;
  for (let i = 1; i <= trailing; i++) {
    const dateStr = isoDate(nextYear, nextMonth, i);
    cells.push({ date: dateStr, dayOfMonth: i, isCurrentMonth: false, isToday: dateStr === todayISO, markers: emptyMarkers(), panchang: null });
  }

  return cells;
}
