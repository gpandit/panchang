/**
 * Shared API types for The Pandit platform.
 * Generated from the OpenAPI spec in Step 2+ — these stubs define the shape
 * agreed upon in the Architecture Document §7.
 *
 * TODO(step-2): replace with generated types from services/api OpenAPI spec.
 */

// ─── Location ──────────────────────────────────────────────────────────────

export interface Location {
  latitude: number;
  longitude: number;
  timezone: string; // IANA timezone, e.g. "Asia/Kolkata"
}

// ─── Panchang ─────────────────────────────────────────────────────────────

export type Ayanamsa = "lahiri" | "raman" | "krishnamurti";
export type MonthScheme = "amanta" | "purnimanta";
export type Paksha = "shukla" | "krishna";

export interface TithiInfo {
  index: number; // 1–30
  name: string;
  paksha: Paksha;
  startTime: string; // ISO 8601 datetime
  endTime: string;
}

export interface NakshatraInfo {
  index: number; // 1–27
  name: string;
  pada: number; // 1–4
  startTime: string;
  endTime: string;
}

export interface YogaInfo {
  index: number; // 1–27
  name: string;
  startTime: string;
  endTime: string;
}

export interface KaranaInfo {
  index: number; // 1–11
  name: string;
  startTime: string;
  endTime: string;
}

/**
 * One day of Panchang data.
 * Keyed by date + location-grid + ayanamsa + monthScheme in the backend cache.
 * Clients must never recompute this — always read from the API.
 */
export interface PanchangDay {
  date: string; // "YYYY-MM-DD" (Gregorian date for the Panchang day)
  location: Location;
  ayanamsa: Ayanamsa;
  monthScheme: MonthScheme;
  tithi: TithiInfo | null;
  nakshatra: NakshatraInfo | null;
  yoga: YogaInfo | null;
  karana: KaranaInfo | null;
  sunrise: string | null; // ISO 8601 datetime
  sunset: string | null;
  moonrise: string | null;
  moonset: string | null;
  // Adhika (leap) or Kshaya (lost) month flag
  leapMonthFlag: "adhika" | "kshaya" | null;
}

// ─── API envelope types ──────────────────────────────────────────────────

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ApiResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
}
