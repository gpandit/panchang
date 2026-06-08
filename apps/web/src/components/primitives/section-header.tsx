import type { ReactNode } from "react";
import { createElement } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface SectionHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  level?: 1 | 2 | 3 | 4;
  className?: string;
}

export function SectionHeader({
  title,
  subtitle,
  actions,
  level = 2,
  className = "",
}: SectionHeaderProps): React.JSX.Element {
  return (
    <div className={`flex items-baseline justify-between gap-md ${className}`.trim()}>
      <div>
        {createElement(`h${level}`, { className: "text-xl font-display" }, title)}
        {subtitle ? <p className="text-muted-foreground text-sm">{subtitle}</p> : null}
      </div>
      {actions ? <div>{actions}</div> : null}
    </div>
  );
}
