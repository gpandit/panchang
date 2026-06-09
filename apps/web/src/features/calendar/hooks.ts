"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchMonthCalendar,
  syncNotesFromAPI,
  syncRemindersFromAPI,
  createNote as apiCreateNote,
  updateNote as apiUpdateNote,
  deleteNote as apiDeleteNote,
  createReminder as apiCreateReminder,
  deleteReminder as apiDeleteReminder,
  readNotesStore,
  readRemindersStore,
  flushSyncQueue,
  getSyncQueueLength,
  type NoteInput,
  type ReminderInput,
} from "./api";
import { buildDayGrid } from "./markers";
import type { CalendarDayCell, CalendarMonthData, LocalNote, LocalReminder } from "./types";

export type LoadState = "idle" | "loading" | "success" | "error";

// ─── Month calendar ───────────────────────────────────────────────────────────

export interface UseMonthCalendarParams {
  year: number;
  month: number; // 1-12
  lat: number;
  lon: number;
  tz: string;
  ayanamsa?: string;
  monthScheme?: string;
}

export interface UseMonthCalendarResult {
  data: CalendarMonthData | null;
  cells: CalendarDayCell[];
  loadState: LoadState;
  fromCache: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useMonthCalendar(
  params: UseMonthCalendarParams,
  notes: LocalNote[],
): UseMonthCalendarResult {
  const todayISO = new Date().toISOString().slice(0, 10);
  const [data, setData] = useState<CalendarMonthData | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [fromCache, setFromCache] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (force = false) => {
      setLoadState("loading");
      const result = await fetchMonthCalendar({ ...params, forceRefresh: force });
      setData(result.data);
      setFromCache(result.fromCache);
      setError(result.error ?? null);
      setLoadState(result.data ? "success" : "error");
    },
    [
      params.year,
      params.month,
      params.lat,
      params.lon,
      params.tz,
      params.ayanamsa,
      params.monthScheme,
    ],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  const cells = data ? buildDayGrid(data, notes, todayISO) : [];

  return {
    data,
    cells,
    loadState,
    fromCache,
    error,
    refresh: useCallback(() => load(true), [load]),
  };
}

// ─── Notes store ──────────────────────────────────────────────────────────────

export interface UseNotesResult {
  notes: LocalNote[];
  loadState: LoadState;
  createNote: (noteIn: NoteInput) => Promise<void>;
  updateNote: (id: string, noteIn: NoteInput) => Promise<void>;
  deleteNote: (id: string) => Promise<void>;
}

export function useNotes(token?: string): UseNotesResult {
  const [notes, setNotes] = useState<LocalNote[]>(() => readNotesStore());
  const [loadState, setLoadState] = useState<LoadState>("idle");

  const reload = useCallback(() => setNotes(readNotesStore()), []);

  useEffect(() => {
    setLoadState("loading");
    syncNotesFromAPI(token)
      .then(() => {
        reload();
        setLoadState("success");
      })
      .catch(() => {
        reload();
        setLoadState("error");
      });
  }, [token, reload]);

  const handleCreate = useCallback(
    async (noteIn: NoteInput) => {
      await apiCreateNote(noteIn, token);
      reload();
    },
    [token, reload],
  );
  const handleUpdate = useCallback(
    async (id: string, noteIn: NoteInput) => {
      await apiUpdateNote(id, noteIn, token);
      reload();
    },
    [token, reload],
  );
  const handleDelete = useCallback(
    async (id: string) => {
      await apiDeleteNote(id, token);
      reload();
    },
    [token, reload],
  );

  return {
    notes,
    loadState,
    createNote: handleCreate,
    updateNote: handleUpdate,
    deleteNote: handleDelete,
  };
}

// ─── Reminders store ──────────────────────────────────────────────────────────

export interface UseRemindersResult {
  reminders: LocalReminder[];
  loadState: LoadState;
  createReminder: (r: ReminderInput) => Promise<void>;
  deleteReminder: (id: string) => Promise<void>;
}

export function useReminders(token?: string): UseRemindersResult {
  const [reminders, setReminders] = useState<LocalReminder[]>(() => readRemindersStore());
  const [loadState, setLoadState] = useState<LoadState>("idle");

  const reload = useCallback(() => setReminders(readRemindersStore()), []);

  useEffect(() => {
    setLoadState("loading");
    syncRemindersFromAPI(token)
      .then(() => {
        reload();
        setLoadState("success");
      })
      .catch(() => {
        reload();
        setLoadState("error");
      });
  }, [token, reload]);

  const handleCreate = useCallback(
    async (r: ReminderInput) => {
      await apiCreateReminder(r, token);
      reload();
    },
    [token, reload],
  );
  const handleDelete = useCallback(
    async (id: string) => {
      await apiDeleteReminder(id, token);
      reload();
    },
    [token, reload],
  );

  return { reminders, loadState, createReminder: handleCreate, deleteReminder: handleDelete };
}

// ─── Offline sync ─────────────────────────────────────────────────────────────

export interface UseOfflineSyncResult {
  pendingCount: number;
  syncNow: () => Promise<void>;
}

export function useOfflineSync(token?: string): UseOfflineSyncResult {
  const [pendingCount, setPendingCount] = useState(() => getSyncQueueLength());

  const flush = useCallback(async () => {
    await flushSyncQueue(token);
    setPendingCount(getSyncQueueLength());
  }, [token]);

  useEffect(() => {
    window.addEventListener("online", flush as EventListener);
    if (navigator.onLine && getSyncQueueLength() > 0) void flush();
    return () => window.removeEventListener("online", flush as EventListener);
  }, [flush]);

  return { pendingCount, syncNow: flush };
}
