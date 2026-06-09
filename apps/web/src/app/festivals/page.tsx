import type { JSX } from "react";
import type { Metadata } from "next";
import { FestivalListScreen } from "@/features/festivals/FestivalListScreen";
import { fetchFestivals } from "@/features/festivals/api";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Festivals & Vrats | The Pandit",
  description: "Browse Hindu festivals, vrats, and observances with puja vidhi and katha.",
};

export default async function FestivalsPage(): Promise<JSX.Element> {
  const ssrData = await fetchFestivals({}, 1, 20).catch(() => null);

  return <FestivalListScreen ssrData={ssrData} />;
}
