/**
 * Data fetching for the Festivals feature.
 * All data comes from the gateway — never computed on the client.
 */

import type { FestivalDetailOut, FestivalOut, PaginatedMeta, PaginatedResponse } from "@pandit/api-client-ts";
import type { FestivalDetailResult, FestivalFilters, FestivalListResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

const LIST_CACHE_PREFIX = "pandit:festivals:";
const LIST_CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

interface ListCacheEntry {
  items: FestivalOut[];
  meta: PaginatedMeta;
  storedAt: number;
}

function listCacheKey(filters: FestivalFilters, page: number, pageSize: number): string {
  return `${LIST_CACHE_PREFIX}${filters.year ?? ""}:${filters.region ?? ""}:${filters.locale ?? ""}:${page}:${pageSize}`;
}

function readListCache(key: string): { items: FestivalOut[]; meta: PaginatedMeta } | null {
  try {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const entry = JSON.parse(raw) as ListCacheEntry;
    if (Date.now() - entry.storedAt > LIST_CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return { items: entry.items, meta: entry.meta };
  } catch {
    return null;
  }
}

function writeListCache(key: string, items: FestivalOut[], meta: PaginatedMeta): void {
  try {
    if (typeof localStorage === "undefined") return;
    const entry: ListCacheEntry = { items, meta, storedAt: Date.now() };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // quota exceeded
  }
}

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchFestivals(
  filters: FestivalFilters = {},
  page = 1,
  pageSize = 20,
  token?: string,
  forceRefresh?: boolean,
): Promise<FestivalListResult> {
  const cacheKey = listCacheKey(filters, page, pageSize);
  if (!forceRefresh) {
    const cached = readListCache(cacheKey);
    if (cached) return { items: cached.items, meta: cached.meta, fromCache: true };
  }

  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (filters.year) qs.set("year", String(filters.year));
  if (filters.region) qs.set("region", filters.region);
  if (filters.locale) qs.set("locale", filters.locale);

  try {
    const res = await fetch(`${API_BASE}/v1/festivals?${qs.toString()}`, {
      headers: authHeaders(token),
      next: { revalidate: 3600 },
    });
    if (!res.ok) {
      const stale = readListCache(cacheKey);
      if (stale) return { items: stale.items, meta: stale.meta, fromCache: true, error: `HTTP ${res.status}` };
      return { items: [], meta: emptyMeta(page, pageSize), fromCache: false, error: `HTTP ${res.status}` };
    }
    const json = (await res.json()) as PaginatedResponse<FestivalOut>;
    writeListCache(cacheKey, json.data, json.meta);
    return { items: json.data, meta: json.meta, fromCache: false };
  } catch (err) {
    const stale = readListCache(cacheKey);
    if (stale) return { items: stale.items, meta: stale.meta, fromCache: true, error: "offline" };
    return {
      items: [],
      meta: emptyMeta(page, pageSize),
      fromCache: false,
      error: err instanceof Error ? err.message : "network error",
    };
  }
}

export async function fetchFestivalDetail(
  festivalId: string,
  token?: string,
): Promise<FestivalDetailResult> {
  try {
    const res = await fetch(`${API_BASE}/v1/festivals/${encodeURIComponent(festivalId)}`, {
      headers: authHeaders(token),
      next: { revalidate: 3600 },
    });
    if (!res.ok) {
      if (res.status === 404) return { festival: null, error: "not_found" };
      return { festival: null, error: `HTTP ${res.status}` };
    }
    const json = (await res.json()) as { data: FestivalDetailOut };
    return { festival: json.data };
  } catch (err) {
    return { festival: null, error: err instanceof Error ? err.message : "network error" };
  }
}

function emptyMeta(page: number, pageSize: number): PaginatedMeta {
  return { total: 0, page, page_size: pageSize, has_next: false };
}
