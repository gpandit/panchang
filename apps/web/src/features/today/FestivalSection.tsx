// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { Festival } from "@pandit/api-client-ts";

const TYPE_LABEL: Record<Festival["type"], string> = {
  festival: "Festival",
  vrat: "Vrat",
  ekadashi: "Ekadashi",
  other: "",
};

interface FestivalSectionProps {
  festivals: Festival[];
}

export function FestivalSection({ festivals }: FestivalSectionProps): React.JSX.Element | null {
  if (festivals.length === 0) return null;

  return (
    <section aria-label="Festivals and vrats" className="px-md py-sm">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-xs">
        Festivals &amp; Vrats
      </h3>
      <ul className="rounded-lg border border-border overflow-hidden flex flex-col">
        {festivals.map((f, i) => (
          <li
            key={i}
            className="flex flex-col gap-xs px-md py-sm border-b border-border last:border-b-0"
          >
            <div className="flex items-center justify-between gap-sm">
              <span className="text-sm font-medium">{f.name}</span>
              {TYPE_LABEL[f.type] ? (
                <span className="text-xs text-muted-foreground">{TYPE_LABEL[f.type]}</span>
              ) : null}
            </div>
            {f.significance ? (
              <p className="text-xs text-muted-foreground">{f.significance}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
