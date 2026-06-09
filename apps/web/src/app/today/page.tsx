import type { Metadata } from "next";
import { TodayScreen } from "@/features/today/TodayScreen";
import { fetchDailyPanchang } from "@/features/today/api";

// ISR: revalidate once per hour on the server; client-side will also cache.
export const revalidate = 3600;

interface TodayPageProps {
  searchParams: Promise<{ date?: string; lat?: string; lon?: string; tz?: string }>;
}

export async function generateMetadata({ searchParams }: TodayPageProps): Promise<Metadata> {
  const params = await searchParams;
  const date = params.date ?? todayISO();
  return {
    title: `Daily Panchang — ${date} | The Pandit`,
    description: "Today's Tithi, Nakshatra, Yoga, Karana, Muhurat, festivals and more.",
  };
}

export default async function TodayPage({ searchParams }: TodayPageProps): Promise<React.JSX.Element> {
  const params = await searchParams;

  const date = params.date ?? todayISO();
  // Default location: Mumbai. In production the gateway resolves via user prefs / IP.
  const latitude = parseFloat(params.lat ?? "19.076");
  const longitude = parseFloat(params.lon ?? "72.877");
  const timezone = params.tz ?? "Asia/Kolkata";

  // Attempt SSR prefetch so the page arrives with data on first render.
  // On error/timeout the client will re-fetch via useTodayPanchang.
  const { data: ssrData } = await fetchDailyPanchang({
    date,
    latitude,
    longitude,
    timezone,
  }).catch(() => ({ data: null, fromCache: false }));

  return (
    <TodayScreen
      initialDate={date}
      latitude={latitude}
      longitude={longitude}
      timezone={timezone}
      ssrData={ssrData}
    />
  );
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}
