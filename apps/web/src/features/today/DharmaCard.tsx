import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { DharmaCard as DharmaCardData } from "@pandit/api-client-ts";

interface DharmaCardProps {
  card: DharmaCardData;
}

export function DharmaCard({ card }: DharmaCardProps): JSX.Element {
  return (
    <section aria-label="Daily dharma" className="px-md py-sm">
      <div className="rounded-lg border border-border bg-background shadow-sm p-md flex flex-col gap-sm">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Daily Dharma
        </h3>
        <h4 className="text-base font-display">{card.title}</h4>
        <p className="text-sm text-foreground">{card.body}</p>
        {card.attribution ? (
          <p className="text-xs text-muted-foreground self-end">— {card.attribution}</p>
        ) : null}
      </div>
    </section>
  );
}
