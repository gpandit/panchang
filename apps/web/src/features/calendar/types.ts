import type { DailyPanchangOut, FestivalOut, NoteIn, ReminderIn } from "@pandit/api-client-ts";

export type { DailyPanchangOut, FestivalOut };

export type MoonPhase = "new" | "waxing" | "full" | "waning";

export interface DayCellMarkers {
  tithi: string | null;
  moonPhase: MoonPhase;
  festivals: string[];   // non-vrat festival names
  vrats: string[];       // vrat/fast names (festivals tagged "vrat")
  hasNote: boolean;
  hasBookmark: boolean;
}

export interface CalendarDayCell {
  date: string;              // "YYYY-MM-DD"
  dayOfMonth: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  markers: DayCellMarkers;
  panchang: DailyPanchangOut | null; // null for padding cells
}

export interface CalendarMonthData {
  year: number;
  month: number;  // 1-12
  days: DailyPanchangOut[];
  festivals: FestivalOut[];
}

/** NoteOut extended with a client-only pending flag for offline-queued ops. */
export interface LocalNote {
  id: string;
  date: string;
  body: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  _pending?: boolean;
}

/** ReminderOut extended with a client-only pending flag. */
export interface LocalReminder {
  id: string;
  title: string;
  trigger_type: "gregorian" | "tithi" | "nakshatra";
  trigger_value: string;
  advance_minutes: number;
  next_fire_at: string | null;
  is_active: boolean;
  _pending?: boolean;
}

export type SyncOpType =
  | "create_note"
  | "update_note"
  | "delete_note"
  | "create_reminder"
  | "delete_reminder";

export interface SyncOp {
  opId: string;
  type: SyncOpType;
  payload:
    | { note: NoteIn; tempId: string }          // create_note
    | { id: string; note: NoteIn }              // update_note
    | { id: string }                            // delete_note | delete_reminder
    | { reminder: ReminderIn; tempId: string }; // create_reminder
}
