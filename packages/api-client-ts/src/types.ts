/**
 * Shared API types for The Pandit platform.
 *
 * Generated from services/api OpenAPI spec (docs/openapi.json).
 * Do NOT edit by hand — run `npm run generate` to regenerate.
 *
 * Spec version: 1.0.0
 */

// ─── Common envelope ─────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  meta?: Record<string, unknown> | null;
}

export interface ApiError {
  code: string;
  message: string;
  details?: unknown | null;
}

export interface ApiErrorResponse {
  error: ApiError;
}

export interface PaginatedMeta {
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginatedMeta;
}

// ─── Auth / tiers ─────────────────────────────────────────────────────────────

export type SubscriptionTier = "basic" | "silver" | "gold";

// ─── Panchang ─────────────────────────────────────────────────────────────────

export type Ayanamsa = "lahiri";
export type MonthScheme = "amanta" | "purnimanta";

export interface TimeValueOut {
  iso: string; // ISO-8601 timestamp with offset
  hour_24: string; // "HH:MM:SS"
  hour_12: string; // "hh:MM:SS AM/PM"
  hour_24_plus: string; // "HH:MM:SS" where HH may exceed 23
}

export interface AngaSpanOut {
  index: number;
  name: string;
  start: TimeValueOut | null;
  end: TimeValueOut | null;
}

export interface DayEventsOut {
  sunrise: TimeValueOut;
  sunset: TimeValueOut;
  moonrise: TimeValueOut | null;
  moonset: TimeValueOut | null;
}

export interface CalendricalOut {
  shaka_samvat: number;
  vikram_samvat: number;
  gujarati_samvat: number;
  samvatsara: string;
  ritu: string;
  ayana: string;
  lunar_month: string;
  is_adhika_month: boolean;
  is_kshaya_month: boolean;
  paksha: string;
  moon_rashi: string;
  sun_rashi: string;
}

export interface PeriodOut {
  name: string;
  start: TimeValueOut;
  end: TimeValueOut;
}

export interface ChoghadiyaOut {
  name: string;
  start: TimeValueOut;
  end: TimeValueOut;
  is_day: boolean;
}

/** Full Panchang for one (date, location, settings) day — the primary API payload. */
export interface DailyPanchangOut {
  date: string; // "YYYY-MM-DD"
  lat: number;
  lon: number;
  tz: string; // IANA timezone
  ayanamsa: string;
  month_scheme: string;

  sun_longitude: number;
  moon_longitude: number;
  ayanamsa_value: number;

  tithi: AngaSpanOut[];
  nakshatra: AngaSpanOut[];
  yoga: AngaSpanOut[];
  karana: AngaSpanOut[];
  vara: AngaSpanOut;

  day_events: DayEventsOut;
  muhurat: PeriodOut[];
  choghadiya: ChoghadiyaOut[];
  hora: PeriodOut[];
  calendrical: CalendricalOut;

  /** True when the response was served from the edge/in-process cache. */
  cached: boolean;
}

export interface MonthCalendarOut {
  year: number;
  month: number;
  days: DailyPanchangOut[];
}

// ─── Festivals ───────────────────────────────────────────────────────────────

export interface FestivalOut {
  id: string;
  name: string;
  date: string; // "YYYY-MM-DD"
  description: string | null;
  tags: string[];
  region: string | null;
  locale: string | null;
}

/** Full festival record including CMS prose — returned by the detail endpoint. */
export interface FestivalDetailOut extends FestivalOut {
  body: string | null;
  puja: string | null;
  katha: string | null;
}

// ─── Notes / Bookmarks ───────────────────────────────────────────────────────

export interface NoteIn {
  date: string; // "YYYY-MM-DD"
  body: string;
  tags: string[];
}

export interface NoteOut extends NoteIn {
  id: string;
  created_at: string; // ISO-8601
  updated_at: string;
}

// ─── Reminders ───────────────────────────────────────────────────────────────

export interface ReminderIn {
  title: string;
  trigger_type: "gregorian" | "tithi" | "nakshatra";
  trigger_value: string;
  advance_minutes: number;
}

export interface ReminderOut extends ReminderIn {
  id: string;
  next_fire_at: string | null; // ISO-8601
  is_active: boolean;
}

// ─── Profile / Locations ─────────────────────────────────────────────────────

export interface LocationIn {
  name: string;
  lat: number;
  lon: number;
  tz: string;
  is_default: boolean;
}

export interface LocationOut extends LocationIn {
  id: string;
}

export interface ProfileOut {
  user_id: string;
  email: string | null;
  display_name: string | null;
  default_ayanamsa: string;
  default_month_scheme: string;
  locations: LocationOut[];
}

export interface ProfileUpdateIn {
  display_name?: string | null;
  default_ayanamsa?: string | null;
  default_month_scheme?: string | null;
}

// ─── Subscription ────────────────────────────────────────────────────────────

export interface SubscriptionOut {
  user_id: string;
  tier: SubscriptionTier;
  valid_until: string | null; // ISO-8601
  features: string[];
}

// ─── PDF Jobs ────────────────────────────────────────────────────────────────

export interface PdfJobIn {
  year: number;
  lat: number;
  lon: number;
  tz: string;
  ayanamsa?: string;
  month_scheme?: string;
}

export interface PdfJobOut {
  job_id: string;
  status: "queued" | "processing" | "done" | "failed";
  download_url: string | null;
  created_at: string; // ISO-8601
}

// ─── Today / Daily view types (Step 3.2) ─────────────────────────────────────
// View-ready aggregate payload produced by the gateway for the Today screen.
// Clients must never recompute Panchang — always read from the API.

/** Which clock display the user has chosen. Persisted client-side. */
export type TimeFormat = "12h" | "24h" | "24plus";

export interface MuhuratWindow {
  name: string;
  startTime: string; // ISO 8601
  endTime: string;
  type: "auspicious" | "inauspicious";
  description?: string;
}

export interface Festival {
  name: string;
  type: "festival" | "vrat" | "ekadashi" | "other";
  description?: string;
  significance?: string;
}

export interface Advisory {
  category: "good" | "avoid";
  label: string;
  detail?: string;
}

export interface DailyHighlight {
  label: string;
  value: string;
  detail?: string;
}

export interface DharmaCard {
  title: string;
  body: string;
  attribution?: string;
}

export interface PanchangElement {
  key: string;
  label: string;
  value: string;
  /** Optional secondary value; prefix "ends:" is resolved to a formatted time. */
  secondaryValue?: string;
  group: "core" | "solar" | "lunar" | "other";
  explanation?: string; // CMS-sourced
}

// ─── Marketplace (F4 — module skeleton + router registration) ───────────────
// Domain modules (providers, verification, availability, search, bookings,
// pricing, payments, policy, messaging, reviews, video, safety, finance) are
// scaffolded server-side but ship no endpoints yet beyond the liveness probe.
// Real request/response types land alongside each module's WS-A/B/C/D/E step.

export interface MarketplaceHealthOut {
  status: "ok";
}

/** View-ready daily Panchang payload from the /v1/panchang/daily endpoint. */
export interface DailyPanchangView {
  date: string; // "YYYY-MM-DD"
  lat: number;
  lon: number;
  tz: string;
  locationLabel: string;

  summaryTitle: string;
  panchangHindiDate: string;

  elements: PanchangElement[];

  sunrise: string | null;
  sunset: string | null;
  moonrise: string | null;
  moonset: string | null;

  muhurats: MuhuratWindow[];
  festivals: Festival[];
  advisories: Advisory[];
  highlights: DailyHighlight[];
  dharmaCard: DharmaCard | null;

  leapMonthFlag: "adhika" | "kshaya" | null;
  cachedAt: string;
}
