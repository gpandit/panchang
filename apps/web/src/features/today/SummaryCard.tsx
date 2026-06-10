import type { JSX } from "react";
import { Sunrise, Sunset } from "lucide-react";
import type { DailyPanchangView, TimeFormat } from "@pandit/api-client-ts";
import { formatTime } from "./time";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface SummaryCardProps {
  data: DailyPanchangView;
  timeFormat: TimeFormat;
}

export function SummaryCard({ data, timeFormat }: SummaryCardProps): JSX.Element {
  const sunrise = formatTime(data.sunrise, timeFormat);
  const sunset = formatTime(data.sunset, timeFormat);

  return (
    <section aria-label="Day summary" className="px-4 -mt-9">
      <div
        className="rounded-2xl p-4 flex flex-col gap-3"
        style={{
          background: "var(--color-paper)",
          border: "1px solid var(--color-card-border)",
          boxShadow: "var(--shadow-card)",
        }}
      >
        {/* Leap month badge */}
        {data.leapMonthFlag ? (
          <span
            className="self-start rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wider"
            style={{
              background: "var(--color-secondary-bg)",
              color: "var(--color-secondary)",
              letterSpacing: "0.08em",
            }}
            aria-label={
              data.leapMonthFlag === "adhika" ? "Adhika (leap) month" : "Kshaya (lost) month"
            }
          >
            {data.leapMonthFlag === "adhika" ? "Adhika Maas" : "Kshaya Maas"}
          </span>
        ) : null}

        <h2
          id="summary-title"
          className="leading-tight"
          style={{
            fontFamily: "var(--typography-font-family-display)",
            fontSize: "1.35rem",
            color: "var(--color-ink)",
          }}
        >
          {data.summaryTitle}
        </h2>
        <p className="text-sm" style={{ color: "var(--color-mute)" }}>
          {data.panchangHindiDate}
        </p>

        {/* Solar events strip */}
        {sunrise || sunset ? (
          <dl
            className="flex gap-5 mt-1 pt-3"
            style={{ borderTop: "1px solid var(--color-line-soft)" }}
            aria-label="Solar events"
          >
            {sunrise ? (
              <div className="flex items-center gap-1.5">
                <Sunrise size={16} style={{ color: "var(--color-accent)" }} aria-hidden="true" />
                <dt className="text-xs" style={{ color: "var(--color-mute)" }}>
                  Sunrise
                </dt>
                <dd>
                  <time
                    dateTime={data.sunrise ?? ""}
                    className="text-sm font-semibold tabular"
                    style={{ color: "var(--color-ink)" }}
                  >
                    {sunrise}
                  </time>
                </dd>
              </div>
            ) : null}
            {sunset ? (
              <div className="flex items-center gap-1.5">
                <Sunset size={16} style={{ color: "var(--color-accent)" }} aria-hidden="true" />
                <dt className="text-xs" style={{ color: "var(--color-mute)" }}>
                  Sunset
                </dt>
                <dd>
                  <time
                    dateTime={data.sunset ?? ""}
                    className="text-sm font-semibold tabular"
                    style={{ color: "var(--color-ink)" }}
                  >
                    {sunset}
                  </time>
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </div>
    </section>
  );
}
