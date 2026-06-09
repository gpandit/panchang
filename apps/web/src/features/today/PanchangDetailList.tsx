"use client";

import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

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
    <section aria-label="Panchang details" className="px-md py-sm flex flex-col gap-md">
      {groups.map(({ group, label, items }) => (
        <div key={group}>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-xs">
            {label}
          </h3>
          <ul className="rounded-lg border border-border overflow-hidden">
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
  // secondaryValue may be a raw ISO time (prefixed "ends:") or plain text
  const secondary = element.secondaryValue
    ? resolveSecondary(element.secondaryValue, timeFormat)
    : null;

  return (
    <li className="border-b border-border last:border-b-0">
      <button
        type="button"
        className="flex items-center justify-between w-full px-md py-sm text-left gap-md"
        onClick={onTap}
        aria-label={`${element.label}: ${element.value}${secondary ? `, ${secondary}` : ""}. Tap for explanation.`}
      >
        <div className="flex flex-col gap-xs flex-1">
          <span className="text-xs text-muted-foreground">{element.label}</span>
          <span className="text-sm font-medium">{element.value}</span>
          {secondary ? <span className="text-xs text-muted-foreground">{secondary}</span> : null}
        </div>
        {/* Disclosure indicator — visual treatment deferred to design */}
        <span className="text-muted-foreground text-sm" aria-hidden="true">
          ›
        </span>
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
