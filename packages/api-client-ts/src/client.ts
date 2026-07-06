/**
 * Typed fetch client for The Pandit API gateway.
 *
 * Usage:
 *   const client = new PanditApiClient({ baseUrl: "https://api.pandit.app", token: jwt });
 *   const res = await client.getDailyPanchang({ date: "2025-01-14", lat: 28.6139, lon: 77.2090, tz: "Asia/Kolkata" });
 */

import type {
  ApiResponse,
  DailyPanchangOut,
  FestivalOut,
  MarketplaceHealthOut,
  MonthCalendarOut,
  NoteIn,
  NoteOut,
  PaginatedResponse,
  PdfJobIn,
  PdfJobOut,
  ProfileOut,
  ProfileUpdateIn,
  ReminderIn,
  ReminderOut,
  SubscriptionOut,
} from "./types.js";

export interface PanditApiClientOptions {
  baseUrl: string;
  /** Bearer token. Set / update after auth. */
  token?: string;
}

export interface DailyPanchangParams {
  date: string; // "YYYY-MM-DD"
  lat: number;
  lon: number;
  tz: string;
  ayanamsa?: string;
  month_scheme?: string;
}

export interface MonthCalendarParams {
  year: number;
  month: number;
  lat: number;
  lon: number;
  tz: string;
  ayanamsa?: string;
  month_scheme?: string;
}

export interface FestivalListParams {
  year?: number;
  month?: number;
  page?: number;
  page_size?: number;
}

export class PanditApiClient {
  private baseUrl: string;
  token: string | undefined;

  constructor(options: PanditApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.token = options.token;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      ...(init?.headers as Record<string, string> | undefined),
    };
    const res = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { error?: { message?: string } };
      const msg = body?.error?.message ?? res.statusText;
      throw Object.assign(new Error(msg), { status: res.status, body });
    }
    return res.json() as Promise<T>;
  }

  private qs(params: Record<string, unknown>): string {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) p.set(k, String(v));
    }
    const s = p.toString();
    return s ? `?${s}` : "";
  }

  // ── Panchang ────────────────────────────────────────────────────────────────

  async getDailyPanchang(params: DailyPanchangParams): Promise<ApiResponse<DailyPanchangOut>> {
    return this.request(
      `/v1/panchang/daily${this.qs(params as unknown as Record<string, unknown>)}`,
    );
  }

  async getMonthCalendar(params: MonthCalendarParams): Promise<ApiResponse<MonthCalendarOut>> {
    return this.request(
      `/v1/panchang/month${this.qs(params as unknown as Record<string, unknown>)}`,
    );
  }

  // ── Festivals ───────────────────────────────────────────────────────────────

  async listFestivals(params?: FestivalListParams): Promise<PaginatedResponse<FestivalOut>> {
    return this.request(`/v1/festivals${this.qs((params ?? {}) as Record<string, unknown>)}`);
  }

  // ── Notes ───────────────────────────────────────────────────────────────────

  async listNotes(): Promise<ApiResponse<NoteOut[]>> {
    return this.request("/v1/notes");
  }

  async createNote(body: NoteIn): Promise<ApiResponse<NoteOut>> {
    return this.request("/v1/notes", { method: "POST", body: JSON.stringify(body) });
  }

  async updateNote(id: string, body: NoteIn): Promise<ApiResponse<NoteOut>> {
    return this.request(`/v1/notes/${id}`, { method: "PUT", body: JSON.stringify(body) });
  }

  async deleteNote(id: string): Promise<void> {
    await this.request(`/v1/notes/${id}`, { method: "DELETE" });
  }

  // ── Reminders ───────────────────────────────────────────────────────────────

  async listReminders(): Promise<ApiResponse<ReminderOut[]>> {
    return this.request("/v1/reminders");
  }

  async createReminder(body: ReminderIn): Promise<ApiResponse<ReminderOut>> {
    return this.request("/v1/reminders", { method: "POST", body: JSON.stringify(body) });
  }

  async deleteReminder(id: string): Promise<void> {
    await this.request(`/v1/reminders/${id}`, { method: "DELETE" });
  }

  // ── Profile ─────────────────────────────────────────────────────────────────

  async getProfile(): Promise<ApiResponse<ProfileOut>> {
    return this.request("/v1/profile");
  }

  async updateProfile(body: ProfileUpdateIn): Promise<ApiResponse<ProfileOut>> {
    return this.request("/v1/profile", { method: "PUT", body: JSON.stringify(body) });
  }

  // ── Subscription ────────────────────────────────────────────────────────────

  async getSubscription(): Promise<ApiResponse<SubscriptionOut>> {
    return this.request("/v1/subscription");
  }

  // ── PDF Jobs ────────────────────────────────────────────────────────────────

  async createPdfJob(body: PdfJobIn): Promise<ApiResponse<PdfJobOut>> {
    return this.request("/v1/pdf/jobs", { method: "POST", body: JSON.stringify(body) });
  }

  async getPdfJob(jobId: string): Promise<ApiResponse<PdfJobOut>> {
    return this.request(`/v1/pdf/jobs/${jobId}`);
  }

  // ── Marketplace (F4 — module skeleton) ─────────────────────────────────────
  // Domain endpoints (providers, verification, booking, payments, ...) land as
  // each WS-A/B/C/D/E step ships. Only the liveness probe exists today.

  async getMarketplaceHealthz(): Promise<MarketplaceHealthOut> {
    return this.request("/v1/marketplace/healthz");
  }
}
