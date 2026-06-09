import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { DailyHighlight } from "@pandit/api-client-ts";

interface HighlightsSectionProps {
  highlights: DailyHighlight[];
}

export function HighlightsSection({ highlights }: HighlightsSectionProps): JSX.Element | null {
  if (highlights.length === 0) return null;

  return (
    <section aria-label="Today's highlights" className="px-md py-sm">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-xs">
        Today's Highlights
      </h3>
      <ul className="rounded-lg border border-border overflow-hidden">
        {highlights.map((h, i) => (
          <li
            key={i}
            className="flex items-start justify-between px-md py-sm gap-md border-b border-border last:border-b-0"
          >
            <span className="text-sm text-muted-foreground">{h.label}</span>
            <div className="flex flex-col items-end gap-xs">
              <span className="text-sm font-medium">{h.value}</span>
              {h.detail ? <span className="text-xs text-muted-foreground">{h.detail}</span> : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
