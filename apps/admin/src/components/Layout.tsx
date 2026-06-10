import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { tokens as t } from "@/tokens";

const NAV_ITEMS = [
  { to: "/content", label: "Festival Rules" },
  { to: "/flags", label: "Flag Queue" },
  { to: "/reports", label: "Reports" },
  { to: "/audit", label: "Audit Trail" },
];

export function Layout() {
  const { email, adminRole, logout } = useAuth();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        fontFamily: t.font.family,
        fontSize: t.font.sizeBase,
        color: t.color.textBody,
        background: t.color.surfaceAlt,
      }}
    >
      {/* Top bar — Aqualeo header */}
      <header
        style={{
          height: 56,
          flexShrink: 0,
          borderBottom: `1px solid ${t.color.border}`,
          background: t.color.surface,
          display: "flex",
          alignItems: "center",
          padding: "0 22px",
          gap: 16,
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <div
            style={{
              width: 26,
              height: 26,
              borderRadius: 7,
              background: t.color.primary,
              display: "grid",
              placeItems: "center",
            }}
          >
            <span style={{ fontWeight: 800, fontSize: 14, color: t.color.primaryText }}>a</span>
          </div>
          <span style={{ fontSize: 15, fontWeight: 700, color: t.color.text, letterSpacing: -0.2 }}>
            Aqualeo
          </span>
          <span style={{ fontSize: 13, color: t.color.textFaint }}>/</span>
          <span style={{ fontSize: 14, color: t.color.textBody, fontWeight: 500 }}>
            The Pandit Admin
          </span>
        </div>

        <div style={{ flex: 1 }} />

        {/* Search placeholder */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: t.color.surfaceCard,
            border: `1px solid ${t.color.border}`,
            borderRadius: 9,
            padding: "7px 12px",
            width: 240,
          }}
        >
          <span style={{ fontSize: 13, color: t.color.textFaint }}>
            Search festivals, content…
          </span>
        </div>

        {/* Avatar */}
        <div
          title={email ?? "admin"}
          style={{
            width: 32,
            height: 32,
            borderRadius: 999,
            background: "linear-gradient(135deg,#33D6C2,#2A91B8)",
            display: "grid",
            placeItems: "center",
            fontSize: 13,
            fontWeight: 700,
            color: t.color.primaryText,
            cursor: "default",
          }}
        >
          {(email?.[0] ?? "A").toUpperCase()}
        </div>
      </header>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <nav
          aria-label="Admin navigation"
          style={{
            width: 216,
            flexShrink: 0,
            background: t.color.surface,
            borderRight: `1px solid ${t.color.border}`,
            display: "flex",
            flexDirection: "column",
            padding: "18px 14px",
            gap: 2,
          }}
        >
          <p
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: t.color.textFaint,
              padding: "0 10px",
              marginBottom: 8,
            }}
          >
            Manage
          </p>

          {NAV_ITEMS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 11,
                padding: "9px 11px",
                borderRadius: t.radius.md,
                textDecoration: "none",
                fontSize: 13.5,
                fontWeight: isActive ? 600 : 500,
                color: isActive ? t.color.primary : t.color.textBody,
                background: isActive ? t.color.primaryDim : "transparent",
              })}
            >
              {label}
            </NavLink>
          ))}

          {/* User / sign out */}
          <div style={{ marginTop: "auto", paddingTop: t.space.md }}>
            <div
              style={{
                padding: "10px 11px",
                borderRadius: t.radius.md,
                background: t.color.surfaceCard,
                border: `1px solid ${t.color.border}`,
              }}
            >
              <p style={{ fontSize: t.font.sizeSm, color: t.color.text, fontWeight: 600 }}>
                {email ?? "admin"}
              </p>
              <p
                style={{
                  fontSize: t.font.sizeSm,
                  color: t.color.textFaint,
                  textTransform: "capitalize",
                  marginTop: 2,
                }}
              >
                {adminRole}
              </p>
              <button
                onClick={logout}
                style={{
                  marginTop: 10,
                  width: "100%",
                  padding: `${t.space.xs} ${t.space.sm}`,
                  border: `1px solid ${t.color.border}`,
                  borderRadius: t.radius.sm,
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: t.font.sizeSm,
                  color: t.color.textMuted,
                  fontFamily: t.font.family,
                }}
              >
                Sign out
              </button>
            </div>
          </div>
        </nav>

        {/* Main */}
        <main style={{ flex: 1, overflowY: "auto", padding: t.space.xl }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
