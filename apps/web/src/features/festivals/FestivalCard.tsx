import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import Link from "next/link";
import type { FestivalOut } from "./types";

interface FestivalCardProps {
  festival: FestivalOut;
}

export function FestivalCard({ festival }: FestivalCardProps): JSX.Element {
  return (
    <Link
      href={`/festivals/${encodeURIComponent(festival.id)}`}
      className="block rounded-lg border border-border p-md hover:bg-muted transition-colors"
      aria-label={`View details for ${festival.name}`}
    >
      <div className="flex items-start justify-between gap-sm">
        <div className="flex flex-col gap-xs min-w-0">
          <span className="text-sm font-semibold truncate">{festival.name}</span>
          {festival.date ? (
            <span className="text-xs text-muted-foreground">{festival.date}</span>
          ) : null}
          {festival.description ? (
            <p className="text-xs text-muted-foreground line-clamp-2">{festival.description}</p>
          ) : null}
        </div>
        <div className="flex flex-col items-end gap-xs shrink-0">
          {festival.region && festival.region !== "all" ? (
            <span className="text-xs text-muted-foreground capitalize">{festival.region}</span>
          ) : null}
          {festival.tags.length > 0 ? (
            <div className="flex gap-xs flex-wrap justify-end">
              {festival.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="text-xs px-xs py-0.5 rounded-sm bg-muted text-muted-foreground capitalize"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </Link>
  );
}
