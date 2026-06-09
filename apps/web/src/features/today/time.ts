/**
 * Time formatting for the Today screen.
 * "24-plus" means hours continue past midnight (e.g. 25:30 instead of 01:30)
 * to align with traditional Panchang representation of the pre-dawn hours.
 *
 * All functions are pure and operate on ISO 8601 datetime strings.
 */

import type { TimeFormat } from "@pandit/api-client-ts";

/**
 * Format a single ISO 8601 datetime string according to the chosen mode.
 * Returns "" if the input is null/undefined/empty.
 *
 * We extract hours/minutes directly from the ISO string rather than using
 * Date.getHours(), because the gateway always returns times already expressed
 * in the user's local timezone (e.g. "...T06:30:00+05:30"). Using getHours()
 * would shift to the JS runtime's system timezone instead.
 */
export function formatTime(iso: string | null | undefined, mode: TimeFormat): string {
  if (!iso) return "";

  // Match the time portion: THH:mm (with optional seconds and offset)
  const match = iso.match(/T(\d{2}):(\d{2})/);
  if (!match) return iso; // pass through if unparseable

  const hours = parseInt(match[1]!, 10);
  const minutes = parseInt(match[2]!, 10);

  if (isNaN(hours) || isNaN(minutes)) return iso;

  if (mode === "12h") {
    const period = hours < 12 ? "AM" : "PM";
    const h = hours % 12 || 12;
    return `${h}:${pad(minutes)} ${period}`;
  }

  if (mode === "24h") {
    return `${pad(hours)}:${pad(minutes)}`;
  }

  // 24-plus: if hour < 6 we treat it as "next Panchang day" and add 24
  const adjustedHours = hours < 6 ? hours + 24 : hours;
  return `${pad(adjustedHours)}:${pad(minutes)}`;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/**
 * Format a time range from two ISO strings.
 * Returns "" if both are empty.
 */
export function formatTimeRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
  mode: TimeFormat,
): string {
  const start = formatTime(startIso, mode);
  const end = formatTime(endIso, mode);
  if (!start && !end) return "";
  if (!end) return start;
  if (!start) return `–${end}`;
  return `${start} – ${end}`;
}
