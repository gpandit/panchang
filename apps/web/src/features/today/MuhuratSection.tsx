import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { MuhuratWindow, TimeFormat } from "@pandit/api-client-ts";
import { formatTimeRange } from "./time";

interface MuhuratSectionProps {
  muhurats: MuhuratWindow[];
  timeFormat: TimeFormat;
}

export function MuhuratSection({ muhurats, timeFormat }: MuhuratSectionProps): JSX.Element | null {
  if (muhurats.length === 0) return null;

  return (
    <section aria-label="Muhurat windows" className="px-md py-sm">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-xs">
        Muhurat
      </h3>
      <ul className="rounded-lg border border-border overflow-hidden flex flex-col">
        {muhurats.map((m, i) => {
          const range = formatTimeRange(m.startTime, m.endTime, timeFormat);
          return (
            <li
              key={i}
              className="flex items-start justify-between px-md py-sm gap-md border-b border-border last:border-b-0"
            >
              <div className="flex flex-col gap-xs flex-1">
                <span
                  className={[
                    "text-sm font-medium",
                    m.type === "auspicious" ? "text-auspicious" : "text-inauspicious",
                  ].join(" ")}
                  aria-label={`${m.name} — ${m.type}`}
                >
                  {m.name}
                </span>
                {m.description ? (
                  <span className="text-xs text-muted-foreground">{m.description}</span>
                ) : null}
              </div>
              {range ? (
                <time
                  className="text-sm text-muted-foreground whitespace-nowrap"
                  dateTime={m.startTime}
                  aria-label={`${m.name} time: ${range}`}
                >
                  {range}
                </time>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
