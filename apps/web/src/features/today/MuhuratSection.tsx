import type { JSX } from "react";
import type { MuhuratWindow, TimeFormat } from "@pandit/api-client-ts";
import { formatTimeRange } from "./time";

interface MuhuratSectionProps {
  muhurats: MuhuratWindow[];
  timeFormat: TimeFormat;
}

export function MuhuratSection({ muhurats, timeFormat }: MuhuratSectionProps): JSX.Element | null {
  if (muhurats.length === 0) return null;

  const auspicious = muhurats.filter((m) => m.type === "auspicious");
  const inauspicious = muhurats.filter((m) => m.type !== "auspicious");

  return (
    <section aria-label="Muhurat windows" className="px-4 py-3">
      <h3
        className="text-xs font-bold uppercase mb-3"
        style={{ color: "#C4912F", letterSpacing: "0.12em" }}
      >
        Muhurat Windows
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {/* Auspicious */}
        <div
          className="rounded-2xl p-3"
          style={{
            background: "rgba(92,107,54,0.08)",
            border: "1px solid rgba(92,107,54,0.22)",
          }}
        >
          <p
            className="text-xs font-bold uppercase mb-2"
            style={{ color: "#5C6B36", letterSpacing: "0.08em" }}
          >
            Auspicious
          </p>
          <ul className="flex flex-col gap-2">
            {auspicious.map((m, i) => (
              <MuhuratItem key={i} muhurat={m} timeFormat={timeFormat} type="auspicious" />
            ))}
          </ul>
        </div>

        {/* Inauspicious */}
        <div
          className="rounded-2xl p-3"
          style={{
            background: "rgba(178,58,30,0.06)",
            border: "1px solid rgba(178,58,30,0.20)",
          }}
        >
          <p
            className="text-xs font-bold uppercase mb-2"
            style={{ color: "#B23A1E", letterSpacing: "0.08em" }}
          >
            Avoid
          </p>
          <ul className="flex flex-col gap-2">
            {inauspicious.map((m, i) => (
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
  const nameColor = type === "auspicious" ? "#3A1A11" : "#3A1A11";
  const timeColor = type === "auspicious" ? "#5C6B36" : "#9E7A63";

  return (
    <li aria-label={`${m.name} — ${m.type}`}>
      <p className="text-sm font-semibold leading-tight" style={{ color: nameColor }}>
        {m.name}
      </p>
      {range ? (
        <time
          className="text-xs tabular"
          dateTime={m.startTime}
          style={{ color: timeColor }}
        >
          {range}
        </time>
      ) : null}
    </li>
  );
}
