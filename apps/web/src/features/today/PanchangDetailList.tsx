"use client";

import type { JSX } from "react";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import type { PanchangElement, TimeFormat } from "@pandit/api-client-ts";
import { formatTime } from "./time";
import { ExplainModal } from "./ExplainModal";

const GROUP_LABELS: Record<PanchangElement["group"], string> = {
  core: "Core Angas",
  solar: "Solar & Lunar",
  lunar: "Lunar Events",
  other: "Other",
};

const GROUP_ORDER: PanchangElement["group"][] = ["core", "solar", "lunar", "other"];

interface PanchangDetailListProps {
  elements: PanchangElement[];
  timeFormat: TimeFormat;
}

export function PanchangDetailList({ elements, timeFormat }: PanchangDetailListProps): JSX.Element {
  const [activeElement, setActiveElement] = useState<PanchangElement | null>(null);

  const groups = GROUP_ORDER.map((group) => ({
    group,
    label: GROUP_LABELS[group],
    items: elements.filter((el) => el.group === group),
  })).filter((g) => g.items.length > 0);

  return (
    <section aria-label="Panchang details" className="px-4 py-3 flex flex-col gap-4">
      {groups.map(({ group, label, items }) => (
        <div key={group}>
          <h3
            className="text-xs font-bold uppercase mb-2"
            style={{ color: "#C4912F", letterSpacing: "0.12em" }}
          >
            {label}
          </h3>
          <ul
            className="rounded-2xl overflow-hidden"
            style={{ border: "1px solid rgba(124,29,43,0.14)" }}
          >
            {items.map((el) => (
              <PanchangRow
                key={el.key}
                element={el}
                timeFormat={timeFormat}
                onTap={() => setActiveElement(el)}
              />
            ))}
          </ul>
        </div>
      ))}

      <ExplainModal element={activeElement} onClose={() => setActiveElement(null)} />
    </section>
  );
}

interface PanchangRowProps {
  element: PanchangElement;
  timeFormat: TimeFormat;
  onTap: () => void;
}

function PanchangRow({ element, timeFormat, onTap }: PanchangRowProps): JSX.Element {
  const secondary = element.secondaryValue
    ? resolveSecondary(element.secondaryValue, timeFormat)
    : null;

  return (
    <li style={{ borderBottom: "1px solid rgba(124,29,43,0.08)" }} className="last:border-b-0">
      <button
        type="button"
        className="flex items-center justify-between w-full px-4 py-3 text-left gap-4 bg-white transition-colors hover:bg-[#FFEFD9]"
        onClick={onTap}
        aria-label={`${element.label}: ${element.value}${secondary ? `, ${secondary}` : ""}. Tap for explanation.`}
      >
        <div className="flex flex-col gap-0.5 flex-1">
          <span
            className="text-xs font-bold uppercase tracking-wider"
            style={{ color: "#C4912F" }}
          >
            {element.label}
          </span>
          <span
            className="leading-tight"
            style={{
              fontFamily: "'Marcellus', Georgia, serif",
              fontSize: "1.1rem",
              color: "#3A1A11",
            }}
          >
            {element.value}
          </span>
          {secondary ? (
            <span className="text-xs" style={{ color: "#9E7A63" }}>
              {secondary}
            </span>
          ) : null}
        </div>
        <ChevronRight size={16} style={{ color: "#C2A488" }} aria-hidden="true" />
      </button>
    </li>
  );
}

/**
 * If secondaryValue starts with "ends:" treat the remainder as an ISO time
 * and format it with the current timeFormat. Otherwise return as-is.
 */
function resolveSecondary(value: string, timeFormat: TimeFormat): string {
  if (value.startsWith("ends:")) {
    const iso = value.slice(5);
    const formatted = formatTime(iso, timeFormat);
    return formatted ? `ends ${formatted}` : value;
  }
  return value;
}
