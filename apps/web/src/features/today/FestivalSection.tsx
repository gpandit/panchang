import type { JSX } from "react";
import { ChevronRight } from "lucide-react";
import type { Festival } from "@pandit/api-client-ts";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

const TYPE_COLORS: Record<Festival["type"], { bg: string; text: string; border: string }> = {
  festival: {
    bg: "var(--color-festival-bg)",
    text: "var(--color-gold-deep)",
    border: "var(--color-festival-border)",
  },
  vrat: {
    bg: "var(--color-vrat-bg)",
    text: "var(--color-accent)",
    border: "var(--color-vrat-border)",
  },
  ekadashi: {
    bg: "var(--color-ekadashi-bg)",
    text: "var(--color-primary)",
    border: "var(--color-ekadashi-border)",
  },
  other: {
    bg: "var(--color-other-bg)",
    text: "var(--color-mute)",
    border: "var(--color-other-border)",
  },
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
        style={{ color: "var(--color-secondary)", letterSpacing: "0.12em" }}
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
                background: "var(--color-paper)",
                border: "1px solid var(--color-card-border)",
                boxShadow: "var(--shadow-card-soft)",
              }}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold" style={{ color: "var(--color-ink)" }}>
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
                  <p className="text-xs mt-0.5" style={{ color: "var(--color-mute)" }}>
                    {f.significance}
                  </p>
                ) : null}
              </div>
              <ChevronRight size={15} style={{ color: "var(--color-faint)" }} aria-hidden="true" />
            </li>
          );
        })}
      </ul>
    </section>
  );
}
