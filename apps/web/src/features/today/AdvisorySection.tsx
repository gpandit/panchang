// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { Advisory } from "@pandit/api-client-ts";

interface AdvisorySectionProps {
  advisories: Advisory[];
}

export function AdvisorySection({ advisories }: AdvisorySectionProps): React.JSX.Element | null {
  const good = advisories.filter((a) => a.category === "good");
  const avoid = advisories.filter((a) => a.category === "avoid");

  if (advisories.length === 0) return null;

  return (
    <section aria-label="Good and avoid advisory" className="px-md py-sm flex flex-col gap-sm">
      {good.length > 0 && (
        <AdvisoryGroup
          heading="Good for"
          items={good}
          itemClassName="text-auspicious"
        />
      )}
      {avoid.length > 0 && (
        <AdvisoryGroup
          heading="Avoid"
          items={avoid}
          itemClassName="text-inauspicious"
        />
      )}
    </section>
  );
}

interface AdvisoryGroupProps {
  heading: string;
  items: Advisory[];
  itemClassName?: string;
}

function AdvisoryGroup({ heading, items, itemClassName = "" }: AdvisoryGroupProps): React.JSX.Element {
  return (
    <div>
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-xs">
        {heading}
      </h3>
      <ul className="rounded-lg border border-border overflow-hidden">
        {items.map((a, i) => (
          <li
            key={i}
            className="flex flex-col gap-xs px-md py-sm border-b border-border last:border-b-0"
          >
            <span className={`text-sm font-medium ${itemClassName}`}>{a.label}</span>
            {a.detail ? (
              <span className="text-xs text-muted-foreground">{a.detail}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
