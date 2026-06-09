/**
 * @pandit/api-client-ts
 *
 * Shared TypeScript API types and fetch client for The Pandit platform.
 * Used by apps/web, apps/admin, and the mobile bridge layer.
 */

export type {
  // Envelopes
  ApiResponse,
  ApiError,
  ApiErrorResponse,
  PaginatedMeta,
  PaginatedResponse,
  // Auth
  SubscriptionTier,
  // Panchang
  Ayanamsa,
  MonthScheme,
  TimeValueOut,
  AngaSpanOut,
  DayEventsOut,
  CalendricalOut,
  PeriodOut,
  ChoghadiyaOut,
  DailyPanchangOut,
  MonthCalendarOut,
  // Festivals
  FestivalOut,
  // Notes
  NoteIn,
  NoteOut,
  // Reminders
  ReminderIn,
  ReminderOut,
  // Profile
  LocationIn,
  LocationOut,
  ProfileOut,
  ProfileUpdateIn,
  // Subscription
  SubscriptionOut,
  // PDF
  PdfJobIn,
  PdfJobOut,
} from "./types.js";

export { PanditApiClient } from "./client.js";
