/**
 * PDF job lifecycle: enqueue a job, poll for completion, get download URL.
 * All processing happens server-side — the client only tracks status.
 */

import type { PdfJobIn, PdfJobOut } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function enqueuePdfJob(jobIn: PdfJobIn, token: string): Promise<PdfJobOut> {
  const res = await fetch(`${API_BASE}/v1/pdf/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify(jobIn),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}${text ? `: ${text}` : ""}`);
  }
  const json = (await res.json()) as { data: PdfJobOut };
  return json.data;
}

export async function pollPdfJob(jobId: string, token: string): Promise<PdfJobOut> {
  const res = await fetch(`${API_BASE}/v1/pdf/jobs/${encodeURIComponent(jobId)}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = (await res.json()) as { data: PdfJobOut };
  return json.data;
}

/** Poll until the job reaches a terminal state or *maxAttempts* is exhausted. */
export async function waitForPdfJob(
  jobId: string,
  token: string,
  intervalMs = 2000,
  maxAttempts = 60,
): Promise<PdfJobOut> {
  for (let i = 0; i < maxAttempts; i++) {
    const job = await pollPdfJob(jobId, token);
    if (job.status === "done" || job.status === "failed") return job;
    await new Promise<void>((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("PDF job timed out");
}
