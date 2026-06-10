import type { JSX } from "react";
import { ChevronRight } from "lucide-react";
import type { Festival } from "@pandit/api-client-ts";

const TYPE_COLORS: Record<Festival["type"], { bg: string; text: string; border: string }> = {
  festival: { bg: "rgba(196,145,47,0.14)", text: "#9A6E1E", border: "rgba(196,145,47,0.30)" },
  vrat: { bg: "rgba(220,95,27,0.10)", text: "#DC5F1B", border: "rgba(220,95,27,0.25)" },
  ekadashi: { bg: "rgba(124,29,43,0.10)", text: "#7C1D2B", border: "rgba(124,29,43,0.20)" },
  other: { bg: "rgba(158,122,99,0.10)", text: "#9E7A63", border: "rgba(158,122,99,0.20)" },
};

const TYPE_LABEL: Record<Festival["type"], string> = {
  festival: "Festival",
  vrat: "Vrat",
  ekadashi: "Ekadashi",
  other: "",
};

interface FestivalSectionProps {
  festivals: Festival[];
}

export function FestivalSection({ festivals }: FestivalSectionProps): JSX.Element | null {
  if (festivals.length === 0) return null;

  return (
    <section aria-label="Festivals and vrats" className="px-4 py-3">
      <h3
        className="text-xs font-bold uppercase mb-3"
        style={{ color: "#C4912F", letterSpacing: "0.12em" }}
      >
        Festivals &amp; Vrats
      </h3>
      <ul className="flex flex-col gap-2">
        {festivals.map((f, i) => {
          const colors = TYPE_COLORS[f.type];
          return (
            <li
              key={i}
              className="flex items-center gap-3 rounded-2xl px-4 py-3"
              style={{
                background: "#FFFFFF",
                border: "1px solid rgba(124,29,43,0.14)",
                boxShadow: "0 2px 6px rgba(90,19,32,0.06)",
              }}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold" style={{ color: "#3A1A11" }}>
                    {f.name}
                  </span>
                  {TYPE_LABEL[f.type] ? (
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-semibold"
                      style={{
                        background: colors.bg,
                        color: colors.text,
                        border: `1px solid ${colors.border}`,
                      }}
                    >
                      {TYPE_LABEL[f.type]}
                    </span>
                  ) : null}
                </div>
                {f.significance ? (
                  <p className="text-xs mt-0.5" style={{ color: "#9E7A63" }}>
                    {f.significance}
                  </p>
                ) : null}
              </div>
              <ChevronRight size={15} style={{ color: "#C2A488" }} aria-hidden="true" />
            </li>
          );
        })}
      </ul>
    </section>
  );
}
