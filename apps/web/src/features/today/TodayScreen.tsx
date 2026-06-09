"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import type { DailyPanchangView } from "@pandit/api-client-ts";
import { useTimeFormat, useBookmark, useTodayPanchang } from "./hooks";
import { TodayHeader } from "./TodayHeader";
import { SummaryCard } from "./SummaryCard";
import { PanchangDetailList } from "./PanchangDetailList";
import { MuhuratSection } from "./MuhuratSection";
import { FestivalSection } from "./FestivalSection";
import { TimeFormatToggle } from "./TimeFormatToggle";
import { AdvisorySection } from "./AdvisorySection";
import { HighlightsSection } from "./HighlightsSection";
import { DharmaCard } from "./DharmaCard";
import { ShareBookmarkBar } from "./ShareBookmarkBar";

interface TodayScreenProps {
  /** ISO date string, "YYYY-MM-DD". Defaults to today. */
  initialDate?: string;
  latitude: number;
  longitude: number;
  timezone: string;
  /** SSR-prefetched payload — used as immediate data until client fetch resolves. */
  ssrData?: DailyPanchangView | null;
}

export function TodayScreen({
  initialDate,
  latitude,
  longitude,
  timezone,
  ssrData = null,
}: TodayScreenProps): React.JSX.Element {
  const today = todayISODate();
  const [date, setDate] = useState(initialDate ?? today);

  const { data, loadState, fromCache, error, refresh } = useTodayPanchang({
    date,
    latitude,
    longitude,
    timezone,
  });

  // Show SSR data only while the client fetch is still in flight (idle/loading).
  // Once the fetch settles, use its result exclusively so the error state is
  // reachable even when ssrData was provided.
  const payload: DailyPanchangView | null =
    loadState === "idle" || loadState === "loading" ? (data ?? ssrData) : data;

  const [timeFormat, setTimeFormat] = useTimeFormat();
  const [bookmarked, toggleBookmark] = useBookmark(date);
  const router = useRouter();

  function navigateDay(delta: -1 | 1): void {
    const d = new Date(`${date}T12:00:00`);
    d.setDate(d.getDate() + delta);
    const next = d.toISOString().slice(0, 10);
    setDate(next);
    // Sync URL without a full navigation
    router.replace(`/today?date=${next}`, { scroll: false });
  }

  const handleLocationChange = useCallback(() => {
    // TODO: open location picker — wired here, UI deferred to design
    // Placeholder: navigate to the location settings route
    router.push("/settings/location");
  }, [router]);

  return (
    <main aria-label="Today's Panchang" className="flex flex-col min-h-screen bg-background">
      {/* Offline / stale-cache notice — shown whenever cached data is used,
          including the case where the server returned an error and a stale
          cache entry was served as fallback. */}
      {fromCache && (
        <div
          role="status"
          aria-live="polite"
          className="text-xs text-muted-foreground text-center px-md py-xs border-b border-border"
        >
          {error && error !== "offline"
            ? "Showing cached Panchang — live data unavailable right now"
            : "Showing cached Panchang — you may be offline"}
        </div>
      )}

      {payload ? (
        <>
          <TodayHeader
            locationLabel={payload.locationLabel}
            date={date}
            panchangHindiDate={payload.panchangHindiDate}
            onLocationChange={handleLocationChange}
            onPrevDay={() => navigateDay(-1)}
            onNextDay={() => navigateDay(1)}
            canGoBack={date > MIN_DATE}
            canGoForward={date < today}
          />

          {/* Time format toggle — sticky below header */}
          <div className="flex justify-end px-md py-xs border-b border-border sticky top-0 bg-background z-10">
            <TimeFormatToggle value={timeFormat} onChange={setTimeFormat} />
          </div>

          <div className="flex flex-col gap-sm flex-1">
            <SummaryCard data={payload} timeFormat={timeFormat} />
            <PanchangDetailList elements={payload.elements} timeFormat={timeFormat} />
            <MuhuratSection muhurats={payload.muhurats} timeFormat={timeFormat} />
            <FestivalSection festivals={payload.festivals} />
            <AdvisorySection advisories={payload.advisories} />
            <HighlightsSection highlights={payload.highlights} />
            {payload.dharmaCard ? <DharmaCard card={payload.dharmaCard} /> : null}
          </div>

          <ShareBookmarkBar
            date={date}
            locationLabel={payload.locationLabel}
            bookmarked={bookmarked}
            onBookmark={toggleBookmark}
          />
        </>
      ) : loadState === "loading" || loadState === "idle" ? (
        <TodayLoading />
      ) : (
        <TodayError error={error} onRetry={refresh} />
      )}
    </main>
  );
}

function TodayLoading(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Loading today's Panchang"
      aria-live="polite"
      className="flex flex-1 items-center justify-center p-xl text-muted-foreground"
    >
      Loading…
    </div>
  );
}

interface TodayErrorProps {
  error: string | null;
  onRetry: () => Promise<void>;
}

function TodayError({ error, onRetry }: TodayErrorProps): React.JSX.Element {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex flex-col flex-1 items-center justify-center gap-md p-xl text-center"
    >
      <p className="text-sm text-muted-foreground">
        {error === "offline"
          ? "You're offline and no cached Panchang is available for this day."
          : "Unable to load today's Panchang. Please try again."}
      </p>
      <button
        type="button"
        className="text-sm text-primary underline"
        onClick={() => void onRetry()}
        aria-label="Retry loading Panchang"
      >
        Retry
      </button>
    </div>
  );
}

function todayISODate(): string {
  return new Date().toISOString().slice(0, 10);
}

// Earliest navigable date — one year before the current date.
// The API does not guarantee precomputed data before this window.
const MIN_DATE = (() => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
})();
