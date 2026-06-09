"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useCallback, useState } from "react";
import { enqueuePdfJob, waitForPdfJob } from "./api";
import type { PdfPanelState } from "./types";

interface PdfCalendarPanelProps {
  /** Pre-filled from user profile/settings. */
  defaultYear?: number;
  lat: number;
  lon: number;
  tz: string;
  /** Gold-tier bearer token. Panel renders a tier-gate message if absent. */
  token?: string;
}

const INITIAL_STATE: PdfPanelState = {
  status: "idle",
  jobId: null,
  downloadUrl: null,
  error: null,
};

export function PdfCalendarPanel({
  defaultYear,
  lat,
  lon,
  tz,
  token,
}: PdfCalendarPanelProps): React.JSX.Element {
  const year = defaultYear ?? new Date().getFullYear();
  const [state, setState] = useState<PdfPanelState>(INITIAL_STATE);

  const handleGenerate = useCallback(async () => {
    if (!token) return;
    setState({ status: "queued", jobId: null, downloadUrl: null, error: null });

    try {
      const job = await enqueuePdfJob({ year, lat, lon, tz }, token);
      setState((s) => ({ ...s, jobId: job.job_id, status: "processing" }));

      const done = await waitForPdfJob(job.job_id, token);
      if (done.status === "done" && done.download_url) {
        setState({ status: "done", jobId: job.job_id, downloadUrl: done.download_url, error: null });
      } else {
        setState({ status: "failed", jobId: job.job_id, downloadUrl: null, error: "Generation failed." });
      }
    } catch (err) {
      setState({
        status: "failed",
        jobId: null,
        downloadUrl: null,
        error: err instanceof Error ? err.message : "Unknown error",
      });
    }
  }, [token, year, lat, lon, tz]);

  async function handleShare(): Promise<void> {
    if (!state.downloadUrl) return;
    const text = `${year} Hindu Panchang Calendar — The Pandit`;
    if (navigator.share) {
      try {
        await navigator.share({ title: text, text, url: state.downloadUrl });
      } catch {
        // User cancelled
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(state.downloadUrl);
    } catch {
      // noop
    }
  }

  if (!token) {
    return (
      <section
        aria-label="Print calendar"
        className="rounded-lg border border-border px-md py-md flex flex-col gap-sm"
      >
        <h2 className="text-sm font-semibold">Printable Calendar</h2>
        <p className="text-xs text-muted-foreground">
          12-month printable PDF is available on the Gold plan.
        </p>
      </section>
    );
  }

  return (
    <section
      aria-label="Print calendar"
      className="rounded-lg border border-border px-md py-md flex flex-col gap-sm"
    >
      <h2 className="text-sm font-semibold">Printable Calendar — {year}</h2>
      <p className="text-xs text-muted-foreground">
        Generates a 12-month PDF with Panchang data for your location.
      </p>

      {state.status === "idle" && (
        <button
          type="button"
          className="text-sm px-sm py-xs rounded-sm border border-border self-start"
          onClick={() => void handleGenerate()}
        >
          Generate PDF
        </button>
      )}

      {(state.status === "queued" || state.status === "processing") && (
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
          {state.status === "queued" ? "Queued…" : "Generating — this may take a moment…"}
        </p>
      )}

      {state.status === "done" && state.downloadUrl && (
        <div className="flex flex-col gap-xs">
          <div className="flex items-center gap-sm">
            <a
              href={state.downloadUrl}
              download={`panchang-${year}.pdf`}
              className="text-sm text-primary px-sm py-xs rounded-sm border border-border"
            >
              Download PDF
            </a>
            <button
              type="button"
              className="text-sm px-sm py-xs rounded-sm border border-border"
              onClick={() => void handleShare()}
              aria-label="Share calendar PDF"
            >
              Share
            </button>
          </div>
          <button
            type="button"
            className="text-xs text-muted-foreground self-start"
            onClick={() => setState(INITIAL_STATE)}
          >
            Generate again
          </button>
        </div>
      )}

      {state.status === "failed" && (
        <div className="flex flex-col gap-xs">
          <p role="alert" className="text-sm text-destructive">
            {state.error ?? "Generation failed. Please try again."}
          </p>
          <button
            type="button"
            className="text-sm px-sm py-xs rounded-sm border border-border self-start"
            onClick={() => setState(INITIAL_STATE)}
          >
            Try again
          </button>
        </div>
      )}
    </section>
  );
}
