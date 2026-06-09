"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useCallback, useEffect, useState } from "react";
import { fetchFestivals } from "./api";
import { FestivalCard } from "./FestivalCard";
import { FestivalFiltersBar } from "./FestivalFilters";
import type { FestivalFilters, FestivalListResult } from "./types";

interface FestivalListScreenProps {
  /** SSR-prefetched initial result; client will re-fetch if null. */
  ssrData: FestivalListResult | null;
  token?: string;
}

export function FestivalListScreen({
  ssrData,
  token,
}: FestivalListScreenProps): React.JSX.Element {
  const [filters, setFilters] = useState<FestivalFilters>({});
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<FestivalListResult | null>(ssrData);
  const [loading, setLoading] = useState(ssrData === null);

  const load = useCallback(
    async (nextFilters: FestivalFilters, nextPage: number) => {
      setLoading(true);
      const r = await fetchFestivals(nextFilters, nextPage, 20, token);
      setResult(r);
      setLoading(false);
    },
    [token],
  );

  useEffect(() => {
    if (!ssrData) void load(filters, page);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleFiltersChange(next: FestivalFilters) {
    setFilters(next);
    setPage(1);
    void load(next, 1);
  }

  function handleNext() {
    const nextPage = page + 1;
    setPage(nextPage);
    void load(filters, nextPage);
  }

  function handlePrev() {
    if (page <= 1) return;
    const prevPage = page - 1;
    setPage(prevPage);
    void load(filters, prevPage);
  }

  return (
    <main aria-label="Festivals and vrats" className="flex flex-col min-h-screen">
      <header className="px-md py-sm border-b border-border">
        <h1 className="text-base font-semibold">Festivals &amp; Vrats</h1>
      </header>

      <FestivalFiltersBar filters={filters} onChange={handleFiltersChange} />

      <div className="flex-1 px-md py-sm">
        {loading ? (
          <p role="status" aria-live="polite" className="text-sm text-muted-foreground py-lg text-center">
            Loading…
          </p>
        ) : result?.error && result.items.length === 0 ? (
          <p role="alert" className="text-sm text-destructive py-lg text-center">
            Could not load festivals. {result.error}
          </p>
        ) : result?.items.length === 0 ? (
          <p className="text-sm text-muted-foreground py-lg text-center">
            No festivals found for the selected filters.
          </p>
        ) : (
          <ul className="flex flex-col gap-sm" aria-label="Festival list">
            {result?.items.map((f) => (
              <li key={f.id}>
                <FestivalCard festival={f} />
              </li>
            ))}
          </ul>
        )}
      </div>

      {result && (result.meta.page > 1 || result.meta.has_next) ? (
        <nav
          aria-label="Festival list pagination"
          className="flex items-center justify-between px-md py-sm border-t border-border"
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={handlePrev}
            className="text-sm px-sm py-xs rounded-sm border border-border disabled:opacity-50"
            aria-label="Previous page"
          >
            Previous
          </button>
          <span className="text-xs text-muted-foreground">
            Page {result.meta.page}
          </span>
          <button
            type="button"
            disabled={!result.meta.has_next}
            onClick={handleNext}
            className="text-sm px-sm py-xs rounded-sm border border-border disabled:opacity-50"
            aria-label="Next page"
          >
            Next
          </button>
        </nav>
      ) : null}
    </main>
  );
}
