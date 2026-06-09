/**
 * Data-fetching and offline persistence for the Calendar feature.
 *
 * Strategy:
 *  - Month calendar: localStorage cache (TTL 7 days); falls back to cache on
 *    network failure.
 *  - Notes & reminders: localStorage as the primary store (offline-first);
 *    API is synced in the background and on reconnect.
 *  - Sync queue: pending mutations are stored in localStorage and flushed
 *    when `flushSyncQueue` is called (on reconnect or explicit user action).
 */

import type { NoteOut, ReminderOut } from "@pandit/api-client-ts";
import type {
  CalendarMonthData,
  DailyPanchangOut,
  FestivalOut,
  LocalNote,
  LocalReminder,
  SyncOp,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

// ─── Month calendar cache ─────────────────────────────────────────────────────

const MONTH_CACHE_PREFIX = "pandit:cal-month:";
const MONTH_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

interface MonthCacheEntry {
  data: CalendarMonthData;
  storedAt: number;
}

function monthCacheKey(year: number, month: number, lat: number, lon: number, scheme: string): string {
  const gLat = Math.round(lat * 100) / 100;
  const gLon = Math.round(lon * 100) / 100;
  return `${MONTH_CACHE_PREFIX}${year}-${String(month).padStart(2, "0")}:${gLat},${gLon}:${scheme}`;
}

function readMonthCache(key: string): CalendarMonthData | null {
  try {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const entry = JSON.parse(raw) as MonthCacheEntry;
    if (Date.now() - entry.storedAt > MONTH_CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return entry.data;
  } catch {
    return null;
  }
}

function writeMonthCache(key: string, data: CalendarMonthData): void {
  try {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(key, JSON.stringify({ data, storedAt: Date.now() } satisfies MonthCacheEntry));
  } catch { /* quota exceeded */ }
}

// ─── Month calendar fetch ─────────────────────────────────────────────────────

export interface FetchMonthParams {
  year: number;
  month: number;
  lat: number;
  lon: number;
  tz: string;
  ayanamsa?: string;
  monthScheme?: string;
  forceRefresh?: boolean;
}

export interface FetchMonthResult {
  data: CalendarMonthData | null;
  fromCache: boolean;
  error?: string;
}

export async function fetchMonthCalendar(params: FetchMonthParams): Promise<FetchMonthResult> {
  const scheme = params.monthScheme ?? "amanta";
  const key = monthCacheKey(params.year, params.month, params.lat, params.lon, scheme);

  if (!params.forceRefresh) {
    const cached = readMonthCache(key);
    if (cached) return { data: cached, fromCache: true };
  }

  const qs = new URLSearchParams({
    year: String(params.year),
    month: String(params.month),
    lat: String(params.lat),
    lon: String(params.lon),
    tz: params.tz,
    ...(params.ayanamsa ? { ayanamsa: params.ayanamsa } : {}),
    ...(params.monthScheme ? { month_scheme: params.monthScheme } : {}),
  });

  try {
    const [monthRes, festRes] = await Promise.all([
      fetch(`${API_BASE}/v1/panchang/month?${qs.toString()}`),
      fetch(`${API_BASE}/v1/festivals?year=${params.year}&month=${params.month}`),
    ]);

    if (!monthRes.ok) {
      const stale = readMonthCache(key);
      if (stale) return { data: stale, fromCache: true, error: `HTTP ${monthRes.status}` };
      return { data: null, fromCache: false, error: `HTTP ${monthRes.status}` };
    }

    const monthJson = (await monthRes.json()) as {
      data: { year: number; month: number; days: DailyPanchangOut[] };
    };
    const festivals: FestivalOut[] = festRes.ok
      ? (((await festRes.json()) as { data: FestivalOut[] }).data ?? [])
      : [];

    const data: CalendarMonthData = {
      year: monthJson.data.year,
      month: monthJson.data.month,
      days: monthJson.data.days,
      festivals,
    };

    writeMonthCache(key, data);
    return { data, fromCache: false };
  } catch (err) {
    const stale = readMonthCache(key);
    if (stale) return { data: stale, fromCache: true, error: "offline" };
    return {
      data: null,
      fromCache: false,
      error: err instanceof Error ? err.message : "network error",
    };
  }
}

// ─── Notes local store ────────────────────────────────────────────────────────

export const NOTES_STORE_KEY = "pandit:notes";

export function readNotesStore(): LocalNote[] {
  try {
    if (typeof localStorage === "undefined") return [];
    const raw = localStorage.getItem(NOTES_STORE_KEY);
    return raw ? (JSON.parse(raw) as LocalNote[]) : [];
  } catch {
    return [];
  }
}

export function writeNotesStore(notes: LocalNote[]): void {
  try {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(NOTES_STORE_KEY, JSON.stringify(notes));
  } catch { /* quota exceeded */ }
}

// ─── Reminders local store ────────────────────────────────────────────────────

export const REMINDERS_STORE_KEY = "pandit:reminders";

export function readRemindersStore(): LocalReminder[] {
  try {
    if (typeof localStorage === "undefined") return [];
    const raw = localStorage.getItem(REMINDERS_STORE_KEY);
    return raw ? (JSON.parse(raw) as LocalReminder[]) : [];
  } catch {
    return [];
  }
}

export function writeRemindersStore(reminders: LocalReminder[]): void {
  try {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(REMINDERS_STORE_KEY, JSON.stringify(reminders));
  } catch { /* quota exceeded */ }
}

// ─── Sync queue ───────────────────────────────────────────────────────────────

export const SYNC_QUEUE_KEY = "pandit:sync-queue";

function readSyncQueue(): SyncOp[] {
  try {
    if (typeof localStorage === "undefined") return [];
    const raw = localStorage.getItem(SYNC_QUEUE_KEY);
    return raw ? (JSON.parse(raw) as SyncOp[]) : [];
  } catch {
    return [];
  }
}

function writeSyncQueue(queue: SyncOp[]): void {
  try {
    if (typeof localStorage === "undefined") return;
    if (queue.length === 0) localStorage.removeItem(SYNC_QUEUE_KEY);
    else localStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(queue));
  } catch { /* quota */ }
}

function enqueueSyncOp(op: SyncOp): void {
  const queue = readSyncQueue();
  queue.push(op);
  writeSyncQueue(queue);
}

function dequeueSyncOp(opId: string): void {
  writeSyncQueue(readSyncQueue().filter((o) => o.opId !== opId));
}

export function getSyncQueueLength(): number {
  return readSyncQueue().length;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeLocalId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Notes API operations ─────────────────────────────────────────────────────

export interface NoteInput {
  date: string;
  body: string;
  tags: string[];
}

/** Fetch all notes from API and merge into the local store. */
export async function syncNotesFromAPI(token?: string): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/v1/notes`, {
      headers: authHeaders(token),
    });
    if (!res.ok) return;
    const json = (await res.json()) as { data: NoteOut[] };
    const pending = readNotesStore().filter((n) => n._pending);
    const merged = dedup([
      ...json.data.map<LocalNote>((n) => ({ ...n, _pending: false })),
      ...pending,
    ]);
    writeNotesStore(merged);
  } catch { /* offline — keep local store as-is */ }
}

/**
 * Create a note. Optimistically writes to the local store.
 * If the network call fails, queues the operation for later sync.
 */
export async function createNote(noteIn: NoteInput, token?: string): Promise<LocalNote> {
  const tempId = makeLocalId();
  const now = new Date().toISOString();
  const local: LocalNote = {
    id: tempId, date: noteIn.date, body: noteIn.body, tags: noteIn.tags,
    created_at: now, updated_at: now, _pending: true,
  };

  writeNotesStore([...readNotesStore(), local]);

  try {
    const res = await fetch(`${API_BASE}/v1/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      body: JSON.stringify(noteIn),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = (await res.json()) as { data: NoteOut };
    const server: LocalNote = { ...json.data, _pending: false };
    writeNotesStore([...readNotesStore().filter((n) => n.id !== tempId), server]);
    return server;
  } catch {
    enqueueSyncOp({ opId: makeLocalId(), type: "create_note", payload: { note: noteIn, tempId } });
    return local;
  }
}

/** Update a note. Optimistic + offline queue. */
export async function updateNote(id: string, noteIn: NoteInput, token?: string): Promise<LocalNote> {
  const now = new Date().toISOString();
  const store = readNotesStore();
  const existing = store.find((n) => n.id === id);
  const updated: LocalNote = existing
    ? { ...existing, ...noteIn, updated_at: now }
    : { id, ...noteIn, created_at: now, updated_at: now, _pending: true };

  writeNotesStore([...store.filter((n) => n.id !== id), updated]);

  try {
    if (id.startsWith("local-")) throw new Error("pending — no server id yet");
    const res = await fetch(`${API_BASE}/v1/notes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      body: JSON.stringify(noteIn),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = (await res.json()) as { data: NoteOut };
    const server: LocalNote = { ...json.data, _pending: false };
    writeNotesStore([...readNotesStore().filter((n) => n.id !== id), server]);
    return server;
  } catch {
    enqueueSyncOp({ opId: makeLocalId(), type: "update_note", payload: { id, note: noteIn } });
    return updated;
  }
}

/** Delete a note. Optimistic + offline queue. */
export async function deleteNote(id: string, token?: string): Promise<void> {
  writeNotesStore(readNotesStore().filter((n) => n.id !== id));
  try {
    if (id.startsWith("local-")) return;
    const res = await fetch(`${API_BASE}/v1/notes/${id}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch {
    if (!id.startsWith("local-")) {
      enqueueSyncOp({ opId: makeLocalId(), type: "delete_note", payload: { id } });
    }
  }
}

// ─── Reminders API operations ─────────────────────────────────────────────────

export interface ReminderInput {
  title: string;
  trigger_type: "gregorian" | "tithi" | "nakshatra";
  trigger_value: string;
  advance_minutes: number;
}

/** Fetch all reminders from API and merge into the local store. */
export async function syncRemindersFromAPI(token?: string): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/v1/reminders`, {
      headers: authHeaders(token),
    });
    if (!res.ok) return;
    const json = (await res.json()) as { data: ReminderOut[] };
    const pending = readRemindersStore().filter((r) => r._pending);
    const merged = dedup([
      ...json.data.map<LocalReminder>((r) => ({ ...r, _pending: false })),
      ...pending,
    ]);
    writeRemindersStore(merged);
  } catch { /* offline */ }
}

/** Create a reminder. Optimistic + offline queue. */
export async function createReminder(reminderIn: ReminderInput, token?: string): Promise<LocalReminder> {
  const tempId = makeLocalId();
  const local: LocalReminder = {
    id: tempId, ...reminderIn, next_fire_at: null, is_active: true, _pending: true,
  };
  writeRemindersStore([...readRemindersStore(), local]);

  try {
    const res = await fetch(`${API_BASE}/v1/reminders`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders(token) },
      body: JSON.stringify(reminderIn),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = (await res.json()) as { data: ReminderOut };
    const server: LocalReminder = { ...json.data, _pending: false };
    writeRemindersStore([...readRemindersStore().filter((r) => r.id !== tempId), server]);
    return server;
  } catch {
    enqueueSyncOp({
      opId: makeLocalId(),
      type: "create_reminder",
      payload: { reminder: reminderIn, tempId },
    });
    return local;
  }
}

/** Delete a reminder. Optimistic + offline queue. */
export async function deleteReminder(id: string, token?: string): Promise<void> {
  writeRemindersStore(readRemindersStore().filter((r) => r.id !== id));
  try {
    if (id.startsWith("local-")) return;
    const res = await fetch(`${API_BASE}/v1/reminders/${id}`, {
      method: "DELETE",
      headers: authHeaders(token),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch {
    if (!id.startsWith("local-")) {
      enqueueSyncOp({ opId: makeLocalId(), type: "delete_reminder", payload: { id } });
    }
  }
}

// ─── Sync queue flush ─────────────────────────────────────────────────────────

/** Process all queued mutations against the API. Safe to call repeatedly. */
export async function flushSyncQueue(token?: string): Promise<void> {
  const queue = readSyncQueue();
  if (queue.length === 0) return;

  for (const op of queue) {
    try {
      if (op.type === "create_note") {
        const { note, tempId } = op.payload as { note: NoteInput; tempId: string };
        const res = await fetch(`${API_BASE}/v1/notes`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders(token) },
          body: JSON.stringify(note),
        });
        if (!res.ok) continue;
        const json = (await res.json()) as { data: NoteOut };
        const server: LocalNote = { ...json.data, _pending: false };
        writeNotesStore([...readNotesStore().filter((n) => n.id !== tempId), server]);
        dequeueSyncOp(op.opId);
      } else if (op.type === "update_note") {
        const { id, note } = op.payload as { id: string; note: NoteInput };
        const res = await fetch(`${API_BASE}/v1/notes/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...authHeaders(token) },
          body: JSON.stringify(note),
        });
        if (!res.ok) continue;
        const json = (await res.json()) as { data: NoteOut };
        const server: LocalNote = { ...json.data, _pending: false };
        writeNotesStore([...readNotesStore().filter((n) => n.id !== id), server]);
        dequeueSyncOp(op.opId);
      } else if (op.type === "delete_note") {
        const { id } = op.payload as { id: string };
        const res = await fetch(`${API_BASE}/v1/notes/${id}`, { method: "DELETE", headers: authHeaders(token) });
        if (!res.ok) continue;
        dequeueSyncOp(op.opId);
      } else if (op.type === "create_reminder") {
        const { reminder, tempId } = op.payload as { reminder: ReminderInput; tempId: string };
        const res = await fetch(`${API_BASE}/v1/reminders`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders(token) },
          body: JSON.stringify(reminder),
        });
        if (!res.ok) continue;
        const json = (await res.json()) as { data: ReminderOut };
        const server: LocalReminder = { ...json.data, _pending: false };
        writeRemindersStore([...readRemindersStore().filter((r) => r.id !== tempId), server]);
        dequeueSyncOp(op.opId);
      } else if (op.type === "delete_reminder") {
        const { id } = op.payload as { id: string };
        const res = await fetch(`${API_BASE}/v1/reminders/${id}`, { method: "DELETE", headers: authHeaders(token) });
        if (!res.ok) continue;
        dequeueSyncOp(op.opId);
      }
    } catch { /* leave in queue for next attempt */ }
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function dedup<T extends { id: string }>(items: T[]): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}
