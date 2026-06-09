/**
 * Notes & reminders — CRUD persistence tests.
 * Verifies that createNote / createReminder write to the local store and are
 * retrievable via readNotesStore / readRemindersStore.
 *
 * localStorage is stubbed via vi.stubGlobal so store operations persist
 * within each test (the environment is Node with no native localStorage).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createNote,
  createReminder,
  updateNote,
  deleteNote,
  deleteReminder,
  readNotesStore,
  readRemindersStore,
  writeNotesStore,
  writeRemindersStore,
} from "../../src/features/calendar/api";

// ─── localStorage stub (same pattern as offline.test.ts) ─────────────────────

const lsStore: Record<string, string> = {};
const localStorageMock = {
  getItem: (key: string) => lsStore[key] ?? null,
  setItem: (key: string, value: string) => {
    lsStore[key] = value;
  },
  removeItem: (key: string) => {
    delete lsStore[key];
  },
  clear: () => {
    Object.keys(lsStore).forEach((k) => delete lsStore[k]);
  },
  get length() {
    return Object.keys(lsStore).length;
  },
  key: (i: number) => Object.keys(lsStore)[i] ?? null,
};

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_NOTE_RESPONSE = {
  id: "server-note-1",
  date: "2026-06-09",
  body: "Morning puja done",
  tags: [] as string[],
  created_at: "2026-06-09T06:00:00Z",
  updated_at: "2026-06-09T06:00:00Z",
};

const MOCK_REMINDER_RESPONSE = {
  id: "server-rem-1",
  title: "Evening aarti",
  trigger_type: "gregorian" as const,
  trigger_value: "2026-06-09",
  advance_minutes: 15,
  next_fire_at: "2026-06-09T17:45:00Z",
  is_active: true,
};

// ─── createNote — online ──────────────────────────────────────────────────────

describe("createNote — online", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeNotesStore([]);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: MOCK_NOTE_RESPONSE }),
      }),
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("writes the server-returned note to the local store", async () => {
    await createNote({ date: "2026-06-09", body: "Morning puja done", tags: [] });
    const store = readNotesStore();
    expect(store).toHaveLength(1);
    expect(store[0]!.id).toBe("server-note-1");
    expect(store[0]!._pending).toBe(false);
  });

  it("returns a note with the correct body and date", async () => {
    const note = await createNote({ date: "2026-06-09", body: "Morning puja done", tags: [] });
    expect(note.body).toBe("Morning puja done");
    expect(note.date).toBe("2026-06-09");
  });

  it("stores bookmark note with 'bookmark' tag", async () => {
    const bookmarkResponse = { ...MOCK_NOTE_RESPONSE, id: "bm-1", tags: ["bookmark"] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: bookmarkResponse }),
      }),
    );
    const note = await createNote({ date: "2026-06-09", body: "Special day", tags: ["bookmark"] });
    expect(note.tags).toContain("bookmark");
    const store = readNotesStore();
    expect(store[0]!.tags).toContain("bookmark");
  });
});

// ─── createNote — offline ─────────────────────────────────────────────────────

describe("createNote — offline (fetch throws)", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeNotesStore([]);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("writes a pending note to local store when offline", async () => {
    const note = await createNote({ date: "2026-06-09", body: "Offline note", tags: [] });
    expect(note._pending).toBe(true);
    expect(note.id.startsWith("local-")).toBe(true);
    const store = readNotesStore();
    expect(store).toHaveLength(1);
    expect(store[0]!._pending).toBe(true);
  });

  it("pending note is retrievable after creation", async () => {
    await createNote({ date: "2026-06-09", body: "Offline note", tags: [] });
    const store = readNotesStore();
    const found = store.find((n) => n.date === "2026-06-09" && n.body === "Offline note");
    expect(found).toBeTruthy();
  });
});

// ─── updateNote — online ──────────────────────────────────────────────────────

describe("updateNote — online", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeNotesStore([
      {
        id: "server-note-1",
        date: "2026-06-09",
        body: "Old body",
        tags: [],
        created_at: "2026-06-09T06:00:00Z",
        updated_at: "2026-06-09T06:00:00Z",
      },
    ]);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: { ...MOCK_NOTE_RESPONSE, body: "New body" } }),
      }),
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("replaces the old note body in local store", async () => {
    await updateNote("server-note-1", { date: "2026-06-09", body: "New body", tags: [] });
    const store = readNotesStore();
    expect(store).toHaveLength(1);
    expect(store[0]!.body).toBe("New body");
  });
});

// ─── deleteNote — online ──────────────────────────────────────────────────────

describe("deleteNote — online", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeNotesStore([
      {
        id: "server-note-1",
        date: "2026-06-09",
        body: "To delete",
        tags: [],
        created_at: "",
        updated_at: "",
      },
    ]);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("removes the note from local store", async () => {
    await deleteNote("server-note-1");
    expect(readNotesStore()).toHaveLength(0);
  });
});

// ─── createReminder — online ──────────────────────────────────────────────────

describe("createReminder — online", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeRemindersStore([]);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: MOCK_REMINDER_RESPONSE }),
      }),
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("writes the server-returned reminder to the local store", async () => {
    await createReminder({
      title: "Evening aarti",
      trigger_type: "gregorian",
      trigger_value: "2026-06-09",
      advance_minutes: 15,
    });
    const store = readRemindersStore();
    expect(store).toHaveLength(1);
    expect(store[0]!.id).toBe("server-rem-1");
    expect(store[0]!._pending).toBe(false);
  });

  it("stores reminder with correct title and trigger", async () => {
    const r = await createReminder({
      title: "Evening aarti",
      trigger_type: "gregorian",
      trigger_value: "2026-06-09",
      advance_minutes: 15,
    });
    expect(r.title).toBe("Evening aarti");
    expect(r.trigger_value).toBe("2026-06-09");
    expect(r.advance_minutes).toBe(15);
  });
});

// ─── createReminder — offline ─────────────────────────────────────────────────

describe("createReminder — offline", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeRemindersStore([]);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("writes a pending reminder when offline", async () => {
    const r = await createReminder({
      title: "Morning puja",
      trigger_type: "gregorian",
      trigger_value: "2026-06-09",
      advance_minutes: 0,
    });
    expect(r._pending).toBe(true);
    const store = readRemindersStore();
    expect(store).toHaveLength(1);
    expect(store[0]!.title).toBe("Morning puja");
  });
});

// ─── deleteReminder — online ──────────────────────────────────────────────────

describe("deleteReminder — online", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.stubGlobal("localStorage", localStorageMock);
    writeRemindersStore([
      {
        id: "server-rem-1",
        title: "Old reminder",
        trigger_type: "gregorian",
        trigger_value: "2026-06-09",
        advance_minutes: 0,
        next_fire_at: null,
        is_active: true,
      },
    ]);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorageMock.clear();
  });

  it("removes the reminder from local store", async () => {
    await deleteReminder("server-rem-1");
    expect(readRemindersStore()).toHaveLength(0);
  });
});
