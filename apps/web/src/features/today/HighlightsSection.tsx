import type { JSX } from "react";
import type { DailyHighlight } from "@pandit/api-client-ts";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface HighlightsSectionProps {
  highlights: DailyHighlight[];
}

export function HighlightsSection({ highlights }: HighlightsSectionProps): JSX.Element | null {
  if (highlights.length === 0) return null;

  return (
    <section aria-label="Today's highlights" className="px-4 py-3">
      <h3
        className="text-xs font-bold uppercase mb-3"
        style={{ color: "var(--color-secondary)", letterSpacing: "0.12em" }}
      >
        Today's Highlights
      </h3>
      <ul
        className="rounded-2xl overflow-hidden bg-white"
        style={{ border: "1px solid var(--color-card-border)" }}
      >
        {highlights.map((h, i) => (
          <li
            key={i}
            className="flex items-start justify-between px-4 py-3"
            style={{ borderBottom: "1px solid var(--color-line-soft)" }}
          >
            <span className="text-sm" style={{ color: "var(--color-mute)" }}>
              {h.label}
            </span>
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-sm font-semibold" style={{ color: "var(--color-ink)" }}>
                {h.value}
              </span>
              {h.detail ? (
                <span className="text-xs" style={{ color: "var(--color-faint)" }}>
                  {h.detail}
                </span>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
