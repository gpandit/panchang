import type { JSX } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import type { Advisory } from "@pandit/api-client-ts";

interface AdvisorySectionProps {
  advisories: Advisory[];
}

export function AdvisorySection({ advisories }: AdvisorySectionProps): JSX.Element | null {
  const good = advisories.filter((a) => a.category === "good");
  const avoid = advisories.filter((a) => a.category === "avoid");

  if (advisories.length === 0) return null;

  return (
    <section aria-label="Good and avoid advisory" className="px-4 py-3 flex flex-col gap-3">
      {good.length > 0 && <AdvisoryGroup heading="Good for" items={good} type="good" />}
      {avoid.length > 0 && <AdvisoryGroup heading="Avoid" items={avoid} type="avoid" />}
    </section>
  );
}

function AdvisoryGroup({
  heading,
  items,
  type,
}: {
  heading: string;
  items: Advisory[];
  type: "good" | "avoid";
}): JSX.Element {
  const isGood = type === "good";
  const Icon = isGood ? CheckCircle2 : AlertTriangle;
  const color = isGood ? "#5C6B36" : "#B23A1E";
  const bg = isGood ? "rgba(92,107,54,0.08)" : "rgba(178,58,30,0.06)";
  const border = isGood ? "rgba(92,107,54,0.22)" : "rgba(178,58,30,0.20)";

  return (
    <div className="rounded-2xl p-3" style={{ background: bg, border: `1px solid ${border}` }}>
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={14} style={{ color }} aria-hidden="true" />
        <h3 className="text-xs font-bold uppercase" style={{ color, letterSpacing: "0.08em" }}>
          {heading}
        </h3>
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((a, i) => (
          <li key={i}>
            <p className="text-sm font-semibold" style={{ color: "#3A1A11" }}>
              {a.label}
            </p>
            {a.detail ? (
              <p className="text-xs" style={{ color: "#9E7A63" }}>
                {a.detail}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
