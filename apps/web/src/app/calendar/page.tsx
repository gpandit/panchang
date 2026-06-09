import type { JSX } from "react";
import type { Metadata } from "next";
import { CalendarScreen } from "@/features/calendar/CalendarScreen";
import { fetchMonthCalendar } from "@/features/calendar/api";

export const revalidate = 3600;

interface CalendarPageProps {
  searchParams: Promise<{
    year?: string;
    month?: string;
    lat?: string;
    lon?: string;
    tz?: string;
  }>;
}

export async function generateMetadata({ searchParams }: CalendarPageProps): Promise<Metadata> {
  const params = await searchParams;
  const today = new Date();
  const year = params.year ? parseInt(params.year, 10) : today.getFullYear();
  const month = params.month ? parseInt(params.month, 10) : today.getMonth() + 1;
  const monthName = new Date(year, month - 1, 1).toLocaleString("en", { month: "long" });
  return {
    title: `${monthName} ${year} Panchang Calendar | The Pandit`,
    description: `Browse Tithi, Nakshatra, festivals and vrats for ${monthName} ${year}.`,
  };
}

export default async function CalendarPage({
  searchParams,
}: CalendarPageProps): Promise<JSX.Element> {
  const params = await searchParams;

  const today = new Date();
  const year = params.year ? parseInt(params.year, 10) : today.getFullYear();
  const month = params.month ? parseInt(params.month, 10) : today.getMonth() + 1;
  const latitude = parseFloat(params.lat ?? "19.076");
  const longitude = parseFloat(params.lon ?? "72.877");
  const timezone = params.tz ?? "Asia/Kolkata";
  const locationLabel = "Mumbai, Maharashtra"; // TODO: resolve from user profile

  // SSR-prefetch the current month so the page arrives with grid data.
  // On error the client will re-fetch via useMonthCalendar.
  await fetchMonthCalendar({ year, month, lat: latitude, lon: longitude, tz: timezone }).catch(
    () => ({ data: null, fromCache: false }),
  );

  return (
    <CalendarScreen
      latitude={latitude}
      longitude={longitude}
      timezone={timezone}
      locationLabel={locationLabel}
      initialYear={year}
      initialMonth={month}
    />
  );
}
