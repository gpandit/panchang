"use client";

import type { JSX, ReactNode } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Sun, Calendar, Star, Sparkles, Printer, MessageCircle, User, Monitor } from "lucide-react";

const NAV_ITEMS = [
  { href: "/today", label: "Today", Icon: Sun },
  { href: "/calendar", label: "Calendar", Icon: Calendar },
  { href: "/festivals", label: "Festivals", Icon: Star },
  { href: "/planner", label: "Planner", Icon: Sparkles },
  { href: "/print-calendar", label: "Print Calendar", Icon: Printer },
  { href: "/ask", label: "Ask the Pandit", Icon: MessageCircle },
  { href: "/display", label: "Temple Display", Icon: Monitor },
  { href: "/profile", label: "Profile", Icon: User },
];

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps): JSX.Element {
  const pathname = usePathname();

  // Display boards are full-screen — no shell
  if (pathname.startsWith("/display")) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen" style={{ background: "#FFF6EA" }}>
      {/* Festival rail — maroon gradient sidebar */}
      <aside
        className="arch-motif hidden lg:flex flex-col w-60 flex-none p-5"
        style={{
          background: "linear-gradient(180deg, #7C1D2B, #5A1320)",
          position: "sticky",
          top: 0,
          height: "100vh",
        }}
        aria-label="Main navigation"
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-2 mb-9">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{
              background: "rgba(255,255,255,0.12)",
              border: "1px solid rgba(224,169,62,0.4)",
            }}
          >
            <OmSymbol />
          </div>
          <div>
            <p
              className="leading-none"
              style={{
                fontFamily: "'Marcellus', Georgia, serif",
                fontSize: "1.3rem",
                color: "#FFF6EA",
              }}
            >
              The Pandit
            </p>
            <p
              className="mt-0.5 text-xs font-semibold uppercase tracking-widest"
              style={{ color: "#E0A93E", letterSpacing: "0.15em" }}
            >
              Panchang &amp; Planner
            </p>
          </div>
        </div>

        {/* Nav items */}
        <nav aria-label="Site navigation">
          <ul className="flex flex-col gap-0.5">
            {NAV_ITEMS.map(({ href, label, Icon }) => {
              const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={isActive ? "page" : undefined}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors"
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
                            fontWeight: 500,
                          }
                    }
                  >
                    <Icon
                      size={19}
                      style={{ color: isActive ? "#E0A93E" : "rgba(255,241,224,0.70)" }}
                      aria-hidden="true"
                    />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Print calendar promo */}
        <div
          className="mt-auto rounded-2xl p-4"
          style={{
            background: "rgba(255,246,234,0.12)",
            border: "1px solid rgba(224,169,62,0.35)",
          }}
        >
          <p
            className="text-xs font-bold uppercase tracking-wider"
            style={{ color: "#E0A93E", letterSpacing: "0.12em" }}
          >
            Print Calendar
          </p>
          <p
            className="mt-1 leading-snug"
            style={{
              fontFamily: "'Marcellus', Georgia, serif",
              fontSize: "0.95rem",
              color: "#FFF6EA",
            }}
          >
            HD 15-month calendar at 300 DPI
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}

function OmSymbol(): JSX.Element {
  return (
    <span
      style={{
        fontFamily: "serif",
        fontSize: "1.4rem",
        color: "#E0A93E",
        lineHeight: 1,
      }}
      aria-hidden="true"
    >
      ॐ
    </span>
  );
}
