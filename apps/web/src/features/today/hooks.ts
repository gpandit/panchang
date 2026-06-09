"use client";

import { useState, useEffect, useCallback } from "react";
import type { TimeFormat, DailyPanchangView } from "@pandit/api-client-ts";
import { fetchDailyPanchang, type FetchDailyOptions } from "./api";

// ─── Time format toggle ────────────────────────────────────────────────────

const TIME_FORMAT_KEY = "pandit:timeFormat";
const DEFAULT_FORMAT: TimeFormat = "12h";

function readStoredFormat(): TimeFormat {
  try {
    const v = localStorage.getItem(TIME_FORMAT_KEY);
    if (v === "12h" || v === "24h" || v === "24plus") return v;
  } catch {
    // noop
  }
  return DEFAULT_FORMAT;
}

export function useTimeFormat(): [TimeFormat, (f: TimeFormat) => void] {
  const [format, setFormat] = useState<TimeFormat>(DEFAULT_FORMAT);

  useEffect(() => {
    setFormat(readStoredFormat());
  }, []);

  const setAndPersist = useCallback((f: TimeFormat) => {
    setFormat(f);
    try {
      localStorage.setItem(TIME_FORMAT_KEY, f);
    } catch {
      // noop
    }
  }, []);

  return [format, setAndPersist];
}

// ─── Bookmark ──────────────────────────────────────────────────────────────

const BOOKMARK_KEY_PREFIX = "pandit:bookmark:";

export function useBookmark(date: string): [boolean, () => void] {
  const key = `${BOOKMARK_KEY_PREFIX}${date}`;
  const [bookmarked, setBookmarked] = useState(false);

  useEffect(() => {
    try {
      setBookmarked(localStorage.getItem(key) === "1");
    } catch {
      // noop
    }
  }, [key]);

  const toggle = useCallback(() => {
    setBookmarked((prev) => {
      const next = !prev;
      try {
        if (next) localStorage.setItem(key, "1");
        else localStorage.removeItem(key);
      } catch {
        // noop
      }
      return next;
    });
  }, [key]);

  return [bookmarked, toggle];
}

// ─── Today data ────────────────────────────────────────────────────────────

export type LoadState = "idle" | "loading" | "success" | "error";

export interface UseTodayResult {
  data: DailyPanchangView | null;
  loadState: LoadState;
  fromCache: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useTodayPanchang(opts: FetchDailyOptions): UseTodayResult {
  const [data, setData] = useState<DailyPanchangView | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [fromCache, setFromCache] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (forceRefresh = false) => {
      setLoadState("loading");
      const result = await fetchDailyPanchang({ ...opts, forceRefresh });
      setData(result.data);
      setFromCache(result.fromCache);
      setError(result.error ?? null);
      // A stale-cache hit (data present AND error set) is still treated as
      // "success" for rendering, but the error string is preserved so callers
      // can show a stale-data notice alongside the content.
      setLoadState(result.data ? "success" : "error");
    },
    [opts.date, opts.latitude, opts.longitude, opts.timezone],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  const refresh = useCallback(() => load(true), [load]);

  return { data, loadState, fromCache, error, refresh };
}
