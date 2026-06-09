import type { JSX } from "react";
import type { ReactNode } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

export interface NavItem {
  href: string;
  label: ReactNode;
}

interface NavProps {
  brand?: ReactNode;
  items: NavItem[];
  actions?: ReactNode;
  activeHref: string;
  orientation?: "horizontal" | "vertical";
  className?: string;
}

export function Nav({
  brand,
  items,
  actions,
  activeHref,
  orientation = "horizontal",
  className = "",
}: NavProps): JSX.Element {
  const listClasses = orientation === "vertical" ? "flex flex-col gap-xs" : "flex flex-row gap-md";

  return (
    <nav
      aria-label="Main navigation"
      className={`flex items-center justify-between gap-md ${className}`.trim()}
    >
      {brand ? <div>{brand}</div> : null}
      <ul className={listClasses}>
        {items.map((item) => {
          const isActive = item.href === activeHref;
          return (
            <li key={item.href}>
              <a href={item.href} aria-current={isActive ? "page" : undefined} className="text-sm">
                {item.label}
              </a>
            </li>
          );
        })}
      </ul>
      {actions ? <div>{actions}</div> : null}
    </nav>
  );
}
