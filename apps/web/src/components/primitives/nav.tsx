import type { JSX } from "react";
import type { ReactNode } from "react";

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
  const listClasses = orientation === "vertical" ? "flex flex-col gap-0.5" : "flex flex-row gap-4";

  return (
    <nav
      aria-label="Main navigation"
      className={`flex items-center justify-between gap-4 ${className}`.trim()}
    >
      {brand ? <div>{brand}</div> : null}
      <ul className={listClasses}>
        {items.map((item) => {
          const isActive = item.href === activeHref;
          return (
            <li key={item.href}>
              <a
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors"
                style={
                  isActive
                    ? {
                        background: "rgba(255,246,234,0.14)",
                        border: "1px solid rgba(224,169,62,0.35)",
                        color: "#FFF6EA",
                        fontWeight: 700,
                      }
                    : {
                        border: "1px solid transparent",
                        color: "rgba(255,241,224,0.82)",
                      }
                }
              >
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
