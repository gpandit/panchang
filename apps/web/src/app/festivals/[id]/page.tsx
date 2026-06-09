import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FestivalDetailScreen } from "@/features/festivals/FestivalDetailScreen";
import { fetchFestivalDetail } from "@/features/festivals/api";

export const revalidate = 3600;

interface FestivalDetailPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: FestivalDetailPageProps): Promise<Metadata> {
  const { id } = await params;
  const { festival } = await fetchFestivalDetail(decodeURIComponent(id)).catch(() => ({
    festival: null,
  }));
  if (!festival) {
    return { title: "Festival not found | The Pandit" };
  }
  return {
    title: `${festival.name} | The Pandit`,
    description: festival.description ?? `Learn about ${festival.name} — puja vidhi, katha and more.`,
  };
}

export default async function FestivalDetailPage({
  params,
}: FestivalDetailPageProps): Promise<React.JSX.Element> {
  const { id } = await params;
  const { festival, error } = await fetchFestivalDetail(decodeURIComponent(id)).catch(() => ({
    festival: null,
    error: "network error",
  }));

  if (!festival || error === "not_found") {
    notFound();
  }

  return <FestivalDetailScreen festival={festival} />;
}
