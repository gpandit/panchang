/**
 * Thin API client for the admin console.
 * All calls go to the gateway; the token is set once via setToken().
 */

const BASE = "/admin/v1";

let _token: string | null = null;

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  base = BASE,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;

  const resp = await fetch(`${base}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 204) return undefined as unknown as T;

  const data = await resp.json();
  if (!resp.ok) {
    const msg =
      data?.detail?.message ?? data?.detail ?? `HTTP ${resp.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data as T;
}

// ── Types ──────────────────────────────────────────────────────────────────────

export type ContentStatus = "draft" | "review" | "published" | "rejected";
export type FlagStatus = "open" | "in_review" | "resolved" | "dismissed";
export type AdminRole = "viewer" | "editor" | "publisher" | "super_admin";

export interface ContentVersion {
  version: number;
  status: ContentStatus;
  changed_by: string;
  changed_at: string;
  snapshot: Record<string, unknown>;
}

export interface FestivalRecord {
  id: string;
  status: ContentStatus;
  versions: ContentVersion[];
  current: FestivalIn;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface FestivalIn {
  name: string;
  slug: string;
  date: string;
  description?: string;
  body?: string;
  puja?: string;
  katha?: string;
  tags: string[];
  region?: string;
  locale?: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actor_id: string;
  actor_email?: string;
  action: string;
  resource_type: string;
  resource_id: string;
  detail: Record<string, unknown>;
}

export interface FlagRecord {
  id: string;
  resource_type: string;
  resource_id: string;
  reason: string;
  details?: string;
  reported_by: string;
  reported_at: string;
  status: FlagStatus;
  reviewed_by?: string;
  reviewed_at?: string;
  resolution_note?: string;
}

export interface ReportRow {
  date: string;
  signups: number;
  active_users: number;
  conversions: number;
}

export interface ReportOut {
  period: string;
  rows: ReportRow[];
  totals: ReportRow;
}

// ── Content endpoints ──────────────────────────────────────────────────────────

export const content = {
  list: (status?: ContentStatus) =>
    request<FestivalRecord[]>("GET", `/content/festivals${status ? `?status_filter=${status}` : ""}`),

  get: (id: string) =>
    request<FestivalRecord>("GET", `/content/festivals/${id}`),

  create: (data: FestivalIn) =>
    request<FestivalRecord>("POST", `/content/festivals`, data),

  update: (id: string, data: FestivalIn) =>
    request<FestivalRecord>("PUT", `/content/festivals/${id}`, data),

  submitReview: (id: string) =>
    request<FestivalRecord>("POST", `/content/festivals/${id}/submit-review`),

  publish: (id: string) =>
    request<FestivalRecord>("POST", `/content/festivals/${id}/publish`),

  reject: (id: string) =>
    request<FestivalRecord>("POST", `/content/festivals/${id}/reject`),

  delete: (id: string) =>
    request<void>("DELETE", `/content/festivals/${id}`),

  audit: (params?: { resource_type?: string; resource_id?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params ?? {}).filter(([, v]) => v != null) as [string, string][],
    ).toString();
    return request<AuditEntry[]>("GET", `/content/audit${qs ? `?${qs}` : ""}`);
  },
};

// ── Flag endpoints ─────────────────────────────────────────────────────────────

export const flags = {
  list: (status?: FlagStatus) =>
    request<FlagRecord[]>("GET", `/flags${status ? `?status_filter=${status}` : ""}`),

  get: (id: string) =>
    request<FlagRecord>("GET", `/flags/${id}`),

  report: (data: { resource_type: string; resource_id: string; reason: string; details?: string }) =>
    request<FlagRecord>("POST", `/flags/report`, data),

  resolve: (id: string, action: "resolve" | "dismiss", note?: string) =>
    request<FlagRecord>("POST", `/flags/${id}/resolve`, { action, resolution_note: note }),
};

// ── Reporting endpoints ────────────────────────────────────────────────────────

export const reporting = {
  overview: (period: "last_7d" | "last_30d" | "last_90d" = "last_30d") =>
    request<ReportOut>("GET", `/reporting/overview?period=${period}`),
};
