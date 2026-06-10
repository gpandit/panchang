import type { JSX } from "react";
import type { MuhuratWindow, TimeFormat } from "@pandit/api-client-ts";
import { formatTimeRange } from "./time";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface MuhuratSectionProps {
  muhurats: MuhuratWindow[];
  timeFormat: TimeFormat;
}

export function MuhuratSection({ muhurats, timeFormat }: MuhuratSectionProps): JSX.Element | null {
  if (muhurats.length === 0) return null;

  const indexed = muhurats.map((m, i) => ({ muhurat: m, index: i }));
  const auspicious = indexed.filter(({ muhurat: m }) => m.type === "auspicious");
  const inauspicious = indexed.filter(({ muhurat: m }) => m.type !== "auspicious");

  return (
    <section aria-label="Muhurat windows" className="px-4 py-3">
      <h3
        className="text-xs font-bold uppercase mb-3"
        style={{ color: "var(--color-secondary)", letterSpacing: "0.12em" }}
      >
        Muhurat Windows
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {/* Auspicious */}
        <div
          className="rounded-2xl p-3"
          style={{
            background: "var(--color-auspicious-bg-soft)",
            border: "1px solid var(--color-auspicious-border)",
          }}
        >
          <p
            className="text-xs font-bold uppercase mb-2"
            style={{ color: "var(--color-auspicious)", letterSpacing: "0.08em" }}
          >
            Auspicious
          </p>
          <ul className="flex flex-col gap-2">
            {auspicious.map(({ muhurat: m, index: i }) => (
              <MuhuratItem key={i} muhurat={m} timeFormat={timeFormat} type="auspicious" />
            ))}
          </ul>
        </div>

        {/* Inauspicious */}
        <div
          className="rounded-2xl p-3"
          style={{
            background: "var(--color-inauspicious-bg-soft)",
            border: "1px solid var(--color-inauspicious-border)",
          }}
        >
          <p
            className="text-xs font-bold uppercase mb-2"
            style={{ color: "var(--color-inauspicious)", letterSpacing: "0.08em" }}
          >
            Avoid
          </p>
          <ul className="flex flex-col gap-2">
            {inauspicious.map(({ muhurat: m, index: i }) => (
              <MuhuratItem key={i} muhurat={m} timeFormat={timeFormat} type="inauspicious" />
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function MuhuratItem({
  muhurat: m,
  timeFormat,
  type,
}: {
  muhurat: MuhuratWindow;
  timeFormat: TimeFormat;
  type: "auspicious" | "inauspicious";
}): JSX.Element {
  const range = formatTimeRange(m.startTime, m.endTime, timeFormat);
  const nameColor = "var(--color-ink)";
  const timeColor = type === "auspicious" ? "var(--color-auspicious)" : "var(--color-mute)";

  return (
    <li aria-label={`${m.name} — ${m.type}`}>
      <p className="text-sm font-semibold leading-tight" style={{ color: nameColor }}>
        {m.name}
      </p>
      {range ? (
        <time className="text-xs tabular" dateTime={m.startTime} style={{ color: timeColor }}>
          {range}
        </time>
      ) : null}
    </li>
  );
}
