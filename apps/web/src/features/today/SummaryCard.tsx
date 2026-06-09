import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { DailyPanchangView, TimeFormat } from "@pandit/api-client-ts";
import { formatTime } from "./time";

interface SummaryCardProps {
  data: DailyPanchangView;
  timeFormat: TimeFormat;
}

export function SummaryCard({ data, timeFormat }: SummaryCardProps): JSX.Element {
  const sunrise = formatTime(data.sunrise, timeFormat);
  const sunset = formatTime(data.sunset, timeFormat);

  return (
    <section aria-label="Day summary" className="px-md py-sm">
      <div className="rounded-lg border border-border bg-background shadow-sm p-md flex flex-col gap-xs">
        {/* Leap month badge */}
        {data.leapMonthFlag ? (
          <span
            className="text-xs text-accent font-semibold uppercase tracking-wide self-start"
            aria-label={
              data.leapMonthFlag === "adhika" ? "Adhika (leap) month" : "Kshaya (lost) month"
            }
          >
            {data.leapMonthFlag === "adhika" ? "Adhika Maas" : "Kshaya Maas"}
          </span>
        ) : null}

        <h2 className="text-xl font-display" id="summary-title">
          {data.summaryTitle}
        </h2>
        <p className="text-sm text-muted-foreground">{data.panchangHindiDate}</p>

        {/* Solar events strip */}
        {sunrise || sunset ? (
          <dl className="flex gap-md mt-xs text-sm" aria-label="Solar events">
            {sunrise ? (
              <div className="flex gap-xs">
                <dt className="text-muted-foreground">Sunrise</dt>
                <dd>
                  <time dateTime={data.sunrise ?? ""}>{sunrise}</time>
                </dd>
              </div>
            ) : null}
            {sunset ? (
              <div className="flex gap-xs">
                <dt className="text-muted-foreground">Sunset</dt>
                <dd>
                  <time dateTime={data.sunset ?? ""}>{sunset}</time>
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </div>
    </section>
  );
}
