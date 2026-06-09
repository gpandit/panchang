"use client";

import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { FestivalFilters } from "./types";

const REGIONS = [
  { value: "", label: "All regions" },
  { value: "all", label: "Pan-India" },
  { value: "north", label: "North" },
  { value: "south", label: "South" },
  { value: "east", label: "East" },
  { value: "west", label: "West" },
];

const LOCALES = [
  { value: "", label: "All languages" },
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "gu", label: "Gujarati" },
  { value: "mr", label: "Marathi" },
];

interface FestivalFiltersProps {
  filters: FestivalFilters;
  onChange: (filters: FestivalFilters) => void;
}

export function FestivalFiltersBar({ filters, onChange }: FestivalFiltersProps): JSX.Element {
  return (
    <div
      role="search"
      aria-label="Festival filters"
      className="flex flex-wrap gap-sm px-md py-sm border-b border-border"
    >
      <label className="flex flex-col gap-xs">
        <span className="text-xs text-muted-foreground">Region</span>
        <select
          value={filters.region ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            const next: FestivalFilters = { ...filters };
            if (v) next.region = v;
            else delete next.region;
            onChange(next);
          }}
          className="text-sm border border-border rounded-sm px-xs py-0.5 bg-background"
          aria-label="Filter by region"
        >
          {REGIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-xs">
        <span className="text-xs text-muted-foreground">Language</span>
        <select
          value={filters.locale ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            const next: FestivalFilters = { ...filters };
            if (v) next.locale = v;
            else delete next.locale;
            onChange(next);
          }}
          className="text-sm border border-border rounded-sm px-xs py-0.5 bg-background"
          aria-label="Filter by language"
        >
          {LOCALES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
