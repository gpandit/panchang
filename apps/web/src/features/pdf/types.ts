import type { PdfJobIn, PdfJobOut } from "@pandit/api-client-ts";

export type { PdfJobIn, PdfJobOut };

export type PdfJobStatus = "idle" | "queued" | "processing" | "done" | "failed";

export interface PdfPanelState {
  status: PdfJobStatus;
  jobId: string | null;
  downloadUrl: string | null;
  error: string | null;
}
