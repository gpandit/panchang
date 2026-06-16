/**
 * Thin API client for the temple-admin console.
 * Auth + config calls go to /temple/v1; the JWT is set once via setToken().
 */

const BASE = "/temple/v1";

let _token: string | null = null;

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 204) return undefined as unknown as T;

  if (!resp.ok) {
    let msg: string;
    try {
      const errData = await resp.json();
      const detail = errData?.detail?.message ?? errData?.detail;
      msg =
        typeof detail === "string"
          ? detail
          : detail != null
            ? JSON.stringify(detail)
            : `HTTP ${resp.status}`;
    } catch {
      msg = (await resp.text().catch(() => "")) || `HTTP ${resp.status}`;
    }
    throw new Error(msg);
  }

  return (await resp.json()) as T;
}

// ── Types (mirror api.models.temple) ─────────────────────────────────────────

export interface TempleLocation {
  label: string;
  lat: number;
  lon: number;
  tz: string;
}

export interface AartiEntry {
  key: string;
  name: string;
  dev: string;
  time: string;
  note: string;
  nat?: Record<string, string>;
}

export interface TempleEvent {
  id: string;
  title: string;
  title_dev?: string | null;
  date: string;
  time?: string | null;
  description?: string | null;
}

export interface TempleConfig {
  id: string;
  name: string;
  name_dev: string;
  tagline: string;
  location: TempleLocation;
  aarti: AartiEntry[];
  events: TempleEvent[];
  updated_at: string;
  updated_by?: string | null;
}

export interface TempleConfigIn {
  location: TempleLocation;
  aarti: AartiEntry[];
  events: TempleEvent[];
}

export interface LoginOut {
  token: string;
  temple_id: string;
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const auth = {
  login: (email: string, password: string) =>
    request<LoginOut>("POST", "/auth/login", { email, password }),
  me: () => request<TempleConfig>("GET", "/auth/me"),
};

export const temple = {
  get: () => request<TempleConfig>("GET", "/temple"),
  update: (data: TempleConfigIn) => request<TempleConfig>("PUT", "/temple", data),
};
