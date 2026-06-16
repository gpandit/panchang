/**
 * Temple config for the Temple Display screen.
 * Fetched from the gateway by temple id; the admin console (temple.pandit.xyz)
 * is the source of truth for these values.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export interface TempleLocation {
  label: string;
  lat: number;
  lon: number;
  tz: string;
}

export interface TempleAarti {
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
  aarti: TempleAarti[];
  events: TempleEvent[];
  updated_at: string;
}

/** Default temple id used when the display URL carries no ?temple=<id>. */
export const DEFAULT_TEMPLE_ID = "temple-siddhivinayak";

/** Fetch a temple's public config. Returns null on any failure (display falls back to defaults). */
export async function fetchTempleConfig(templeId: string): Promise<TempleConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/v1/temple/${encodeURIComponent(templeId)}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as TempleConfig;
  } catch {
    return null;
  }
}
