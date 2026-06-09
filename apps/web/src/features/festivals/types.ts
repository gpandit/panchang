import type { FestivalDetailOut, FestivalOut, PaginatedMeta } from "@pandit/api-client-ts";

export type { FestivalDetailOut, FestivalOut };

export interface FestivalListResult {
  items: FestivalOut[];
  meta: PaginatedMeta;
  fromCache: boolean;
  error?: string;
}

export interface FestivalDetailResult {
  festival: FestivalDetailOut | null;
  error?: string;
}

export interface FestivalFilters {
  region?: string;
  locale?: string;
  year?: number;
}
