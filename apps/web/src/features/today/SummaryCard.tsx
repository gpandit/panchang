import type { JSX } from "react";
import { Sunrise, Sunset } from "lucide-react";
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
    <section aria-label="Day summary" className="px-4 -mt-9">
      <div
        className="rounded-2xl p-4 flex flex-col gap-3"
        style={{
          background: "#FFFFFF",
          border: "1px solid rgba(124,29,43,0.14)",
          boxShadow: "0 14px 34px -18px rgba(90,19,32,0.5)",
        }}
      >
        {/* Leap month badge */}
        {data.leapMonthFlag ? (
          <span
            className="self-start rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wider"
            style={{
              background: "rgba(196,145,47,0.15)",
              color: "#C4912F",
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
            fontFamily: "'Marcellus', Georgia, serif",
            fontSize: "1.35rem",
            color: "#3A1A11",
          }}
        >
          {data.summaryTitle}
        </h2>
        <p className="text-sm" style={{ color: "#9E7A63" }}>
          {data.panchangHindiDate}
        </p>

        {/* Solar events strip */}
        {sunrise || sunset ? (
          <dl
            className="flex gap-5 mt-1 pt-3"
            style={{ borderTop: "1px solid rgba(124,29,43,0.08)" }}
            aria-label="Solar events"
          >
            {sunrise ? (
              <div className="flex items-center gap-1.5">
                <Sunrise size={16} style={{ color: "#DC5F1B" }} aria-hidden="true" />
                <dt className="text-xs" style={{ color: "#9E7A63" }}>
                  Sunrise
                </dt>
                <dd>
                  <time
                    dateTime={data.sunrise ?? ""}
                    className="text-sm font-semibold tabular"
                    style={{ color: "#3A1A11" }}
                  >
                    {sunrise}
                  </time>
                </dd>
              </div>
            ) : null}
            {sunset ? (
              <div className="flex items-center gap-1.5">
                <Sunset size={16} style={{ color: "#DC5F1B" }} aria-hidden="true" />
                <dt className="text-xs" style={{ color: "#9E7A63" }}>
                  Sunset
                </dt>
                <dd>
                  <time
                    dateTime={data.sunset ?? ""}
                    className="text-sm font-semibold tabular"
                    style={{ color: "#3A1A11" }}
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
