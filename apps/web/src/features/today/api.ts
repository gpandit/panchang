/**
 * Data fetching for the Today screen.
 * All Panchang data comes from the gateway — never computed on the client.
 *
 * Offline strategy: after a successful fetch, the payload is written to
 * localStorage under a date+location key. On a subsequent load with no network
 * the cached payload is returned so the user can still view today's Panchang.
 */

import type { DailyPanchangView } from "@pandit/api-client-ts";

// Injected at build time; falls back to relative path for local dev.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

const CACHE_KEY_PREFIX = "pandit:daily:";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 h

interface CacheEntry {
  payload: DailyPanchangView;
  storedAt: number;
}

function cacheKey(date: string, lat: number, lon: number): string {
  // Round coordinates to ~1 km grid to improve cache hit rate
  const gridLat = Math.round(lat * 100) / 100;
  const gridLon = Math.round(lon * 100) / 100;
  return `${CACHE_KEY_PREFIX}${date}:${gridLat},${gridLon}`;
}

function readCache(key: string): DailyPanchangView | null {
  try {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const entry: CacheEntry = JSON.parse(raw) as CacheEntry;
    if (Date.now() - entry.storedAt > CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return entry.payload;
  } catch {
    return null;
  }
}

function writeCache(key: string, payload: DailyPanchangView): void {
  try {
    if (typeof localStorage === "undefined") return;
    const entry: CacheEntry = { payload, storedAt: Date.now() };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // Storage quota exceeded or unavailable — degrade gracefully
  }
}

export interface FetchDailyOptions {
  date: string; // "YYYY-MM-DD"
  latitude: number;
  longitude: number;
  timezone: string; // IANA
  ayanamsa?: string;
  monthScheme?: string;
  /** Skip localStorage cache even if a fresh entry exists. */
  forceRefresh?: boolean;
}

export interface FetchDailyResult {
  data: DailyPanchangView | null;
  fromCache: boolean;
  error?: string;
}

/**
 * Fetch today's Panchang view payload from the gateway.
 * Falls back to localStorage cache when the network is unavailable.
 */
export async function fetchDailyPanchang(opts: FetchDailyOptions): Promise<FetchDailyResult> {
  const key = cacheKey(opts.date, opts.latitude, opts.longitude);

  if (!opts.forceRefresh) {
    const cached = readCache(key);
    if (cached) return { data: cached, fromCache: true };
  }

  const params = new URLSearchParams({
    date: opts.date,
    lat: String(opts.latitude),
    lon: String(opts.longitude),
    tz: opts.timezone,
    ...(opts.ayanamsa ? { ayanamsa: opts.ayanamsa } : {}),
    ...(opts.monthScheme ? { month_scheme: opts.monthScheme } : {}),
  });

  try {
    const res = await fetch(`${API_BASE}/v1/panchang/daily?${params.toString()}`, {
      // Next.js ISR: revalidate every hour server-side
      next: { revalidate: 3600 },
    });

    if (!res.ok) {
      // Network available but server error — try stale cache
      const stale = readCache(key);
      if (stale) return { data: stale, fromCache: true, error: `HTTP ${res.status}` };
      return { data: null, fromCache: false, error: `HTTP ${res.status}` };
    }

    const json = (await res.json()) as { data: DailyPanchangView };
    writeCache(key, json.data);
    return { data: json.data, fromCache: false };
  } catch (err) {
    // No network — try cache
    const stale = readCache(key);
    if (stale) {
      return { data: stale, fromCache: true, error: "offline" };
    }
    const message = err instanceof Error ? err.message : "network error";
    return { data: null, fromCache: false, error: message };
  }
}

/** Evict all daily Panchang entries from localStorage. */
export function clearDailyCache(): void {
  try {
    if (typeof localStorage === "undefined") return;
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(CACHE_KEY_PREFIX)) keys.push(k);
    }
    keys.forEach((k) => localStorage.removeItem(k));
  } catch {
    // noop
  }
}
