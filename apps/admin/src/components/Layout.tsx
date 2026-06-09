import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { tokens } from "@/tokens";

const NAV_ITEMS = [
  { to: "/content",   label: "Content" },
  { to: "/flags",     label: "Flag Queue" },
  { to: "/reports",   label: "Reports" },
  { to: "/audit",     label: "Audit Trail" },
];

export function Layout() {
  const { email, adminRole, logout } = useAuth();

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        fontFamily: tokens.font.family,
        fontSize: tokens.font.sizeBase,
        color: tokens.color.text,
        background: tokens.color.surfaceAlt,
      }}
    >
      {/* Sidebar */}
      <nav
        style={{
          width: 200,
          background: tokens.color.surface,
          borderRight: `1px solid ${tokens.color.border}`,
          display: "flex",
          flexDirection: "column",
          padding: tokens.space.md,
          gap: tokens.space.sm,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            fontWeight: tokens.font.weightBold,
            fontSize: tokens.font.sizeLg,
            marginBottom: tokens.space.md,
          }}
        >
          The Pandit
          <div
            style={{
              fontSize: tokens.font.sizeSm,
              color: tokens.color.textMuted,
              fontWeight: tokens.font.weightNormal,
            }}
          >
            Admin
          </div>
        </div>

        {NAV_ITEMS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: "block",
              padding: `${tokens.space.sm} ${tokens.space.md}`,
              borderRadius: tokens.radius.sm,
              textDecoration: "none",
              color: isActive ? tokens.color.primaryText : tokens.color.text,
              background: isActive ? tokens.color.primary : "transparent",
              fontWeight: tokens.font.weightMedium,
            })}
          >
            {label}
          </NavLink>
        ))}

        <div style={{ marginTop: "auto", fontSize: tokens.font.sizeSm }}>
          <div style={{ color: tokens.color.textMuted, marginBottom: tokens.space.xs }}>
            {email ?? "admin"}
          </div>
          <div
            style={{
              color: tokens.color.textMuted,
              marginBottom: tokens.space.sm,
              textTransform: "capitalize",
            }}
          >
            Role: {adminRole}
          </div>
          <button
            onClick={logout}
            style={{
              width: "100%",
              padding: `${tokens.space.xs} ${tokens.space.sm}`,
              border: `1px solid ${tokens.color.border}`,
              borderRadius: tokens.radius.sm,
              background: "transparent",
              cursor: "pointer",
              fontSize: tokens.font.sizeSm,
              color: tokens.color.text,
            }}
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* Main */}
      <main style={{ flex: 1, padding: tokens.space.xl, overflowY: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
