/**
 * Offline behaviour tests.
 * Verifies that:
 *  1. The month calendar is served from localStorage cache when the network fails.
 *  2. Notes in the local store are readable when offline.
 *  3. Notes created offline are queued and flushed (synced) when the network
 *     becomes available via flushSyncQueue.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  fetchMonthCalendar,
  createNote,
  readNotesStore,
  writeNotesStore,
  flushSyncQueue,
  NOTES_STORE_KEY,
  SYNC_QUEUE_KEY,
} from "../../src/features/calendar/api";
import type { CalendarMonthData } from "../../src/features/calendar/types";

// ─── localStorage stub ────────────────────────────────────────────────────────

const store: Record<string, string> = {};

const localStorageMock = {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => {
    store[key] = value;
  },
  removeItem: (key: string) => {
    delete store[key];
  },
  clear: () => {
    Object.keys(store).forEach((k) => delete store[k]);
  },
  get length() {
    return Object.keys(store).length;
  },
  key: (i: number) => Object.keys(store)[i] ?? null,
};

// ─── Month calendar fixture ───────────────────────────────────────────────────

const JUNE_2026: CalendarMonthData = {
  year: 2026,
  month: 6,
  days: [
    {
      date: "2026-06-01",
      lat: 19.076,
      lon: 72.877,
      tz: "Asia/Kolkata",
      ayanamsa: "lahiri",
      month_scheme: "amanta",
      sun_longitude: 0,
      moon_longitude: 0,
      ayanamsa_value: 0,
      tithi: [{ index: 10, name: "Shukla Dashami", start: null, end: null }],
      nakshatra: [{ index: 1, name: "Ashwini", start: null, end: null }],
      yoga: [],
      karana: [],
      vara: { index: 1, name: "Somavar", start: null, end: null },
      day_events: {
        sunrise: {
          iso: "2026-06-01T06:00:00+05:30",
          hour_24: "06:00:00",
          hour_12: "6:00:00 AM",
          hour_24_plus: "06:00:00",
        },
        sunset: {
          iso: "2026-06-01T18:30:00+05:30",
          hour_24: "18:30:00",
          hour_12: "6:30:00 PM",
          hour_24_plus: "18:30:00",
        },
        moonrise: null,
        moonset: null,
      },
      muhurat: [],
      choghadiya: [],
      hora: [],
      calendrical: {
        shaka_samvat: 1946,
        vikram_samvat: 2082,
        gujarati_samvat: 2081,
        samvatsara: "Krodhi",
        ritu: "Grishma",
        ayana: "Uttarayana",
        lunar_month: "Jyeshtha",
        is_adhika_month: false,
        is_kshaya_month: false,
        paksha: "Shukla",
        moon_rashi: "Vrishabha",
        sun_rashi: "Mithuna",
      },
      cached: false,
    },
  ],
  festivals: [],
};

// ─── Tests: month calendar cache ──────────────────────────────────────────────

describe("fetchMonthCalendar — served from cache when offline", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("returns cached data and fromCache=true when fetch throws", async () => {
    // Seed the cache with a successful response
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: JUNE_2026 }),
      }),
    );
    await fetchMonthCalendar({
      year: 2026,
      month: 6,
      lat: 19.076,
      lon: 72.877,
      tz: "Asia/Kolkata",
    });

    // Now go offline
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const result = await fetchMonthCalendar({
      year: 2026,
      month: 6,
      lat: 19.076,
      lon: 72.877,
      tz: "Asia/Kolkata",
      forceRefresh: true,
    });

    expect(result.fromCache).toBe(true);
    expect(result.data).not.toBeNull();
    expect(result.error).toBe("offline");
  });

  it("month data from cache contains correct year and month", async () => {
    // Seed cache
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: JUNE_2026 }),
      }),
    );
    await fetchMonthCalendar({
      year: 2026,
      month: 6,
      lat: 19.076,
      lon: 72.877,
      tz: "Asia/Kolkata",
    });

    // Offline read
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const result = await fetchMonthCalendar({
      year: 2026,
      month: 6,
      lat: 19.076,
      lon: 72.877,
      tz: "Asia/Kolkata",
      forceRefresh: true,
    });
    expect(result.data?.year).toBe(2026);
    expect(result.data?.month).toBe(6);
  });

  it("returns null data and error when no cache exists and offline", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const result = await fetchMonthCalendar({
      year: 2099,
      month: 1,
      lat: 0,
      lon: 0,
      tz: "UTC",
    });
    expect(result.data).toBeNull();
    expect(result.error).toBeTruthy();
  });
});

// ─── Tests: notes offline read ────────────────────────────────────────────────

describe("notes local store — readable when offline", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("a note written directly to the store is readable without network", () => {
    writeNotesStore([
      {
        id: "n-offline-1",
        date: "2026-06-09",
        body: "Offline note",
        tags: [],
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      },
    ]);
    const notes = readNotesStore();
    expect(notes).toHaveLength(1);
    expect(notes[0]!.body).toBe("Offline note");
  });

  it("a note created offline (fetch throws) is in the local store", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await createNote({ date: "2026-06-09", body: "Created offline", tags: [] });
    const notes = readNotesStore();
    expect(notes.some((n) => n.body === "Created offline")).toBe(true);
  });
});

// ─── Tests: sync on reconnect ─────────────────────────────────────────────────

describe("flushSyncQueue — syncs pending notes on reconnect", () => {
  const SERVER_NOTE = {
    id: "server-100",
    date: "2026-06-09",
    body: "Synced note",
    tags: [],
    created_at: "2026-06-09T10:00:00Z",
    updated_at: "2026-06-09T10:00:00Z",
  };

  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("flushSyncQueue replaces local pending id with server id after reconnect", async () => {
    // 1. Create note while offline → lands in queue
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const localNote = await createNote({ date: "2026-06-09", body: "Synced note", tags: [] });
    expect(localNote._pending).toBe(true);
    const tempId = localNote.id;

    // 2. Reconnect — flush queue
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: SERVER_NOTE }),
      }),
    );
    await flushSyncQueue();

    // 3. Temp id should be replaced by server id
    const finalStore = readNotesStore();
    expect(finalStore.some((n) => n.id === tempId)).toBe(false);
    expect(finalStore.some((n) => n.id === "server-100")).toBe(true);
    expect(finalStore.find((n) => n.id === "server-100")?._pending).toBe(false);
  });

  it("sync queue is empty after successful flush", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await createNote({ date: "2026-06-09", body: "Pending", tags: [] });
    const queueBefore = localStorageMock.getItem(SYNC_QUEUE_KEY);
    expect(queueBefore).toBeTruthy();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: SERVER_NOTE }),
      }),
    );
    await flushSyncQueue();

    const queueAfter = localStorageMock.getItem(SYNC_QUEUE_KEY);
    // Either removed or empty array
    const parsed = queueAfter ? (JSON.parse(queueAfter) as unknown[]) : [];
    expect(parsed).toHaveLength(0);
  });

  it("does not throw and leaves queue intact when flush network call fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await createNote({ date: "2026-06-09", body: "Will stay pending", tags: [] });

    // Still offline during flush — should not throw
    await expect(flushSyncQueue()).resolves.not.toThrow();

    const store = readNotesStore();
    expect(store.some((n) => n._pending)).toBe(true);
  });
});
