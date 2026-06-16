/**
 * Login page — email + password. Calls POST /temple/v1/auth/login, then stores
 * the returned JWT (which carries the assigned temple_id) via AuthContext.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { tokens as t } from "@/tokens";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { token } = await auth.login(email.trim(), password);
      login(token);
      navigate("/settings");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    display: "block",
    marginTop: t.space.xs,
    width: "100%",
    padding: t.space.sm,
    border: `1px solid ${t.color.border}`,
    borderRadius: t.radius.sm,
    fontSize: t.font.sizeBase,
    boxSizing: "border-box",
    background: t.color.surfaceCard,
    color: t.color.text,
    fontFamily: t.font.family,
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: t.color.surfaceAlt,
        fontFamily: t.font.family,
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: t.color.surface,
          padding: t.space.xl,
          borderRadius: t.radius.lg,
          boxShadow: t.shadow.md,
          width: 360,
          display: "flex",
          flexDirection: "column",
          gap: t.space.md,
          border: `1px solid ${t.color.border}`,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: t.font.sizeXl,
              fontWeight: t.font.weightBold,
              color: t.color.text,
            }}
          >
            Temple Admin
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: t.font.sizeSm, color: t.color.textMuted }}>
            Sign in to manage your temple display.
          </p>
        </div>

        <label style={{ fontSize: t.font.sizeSm, color: t.color.textMuted }}>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
            placeholder="you@temple.org"
            style={inputStyle}
          />
        </label>

        <label style={{ fontSize: t.font.sizeSm, color: t.color.textMuted }}>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            placeholder="••••••••"
            style={inputStyle}
          />
        </label>

        {error && (
          <p role="alert" style={{ margin: 0, color: t.color.danger, fontSize: t.font.sizeSm }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          style={{
            padding: `${t.space.sm} ${t.space.md}`,
            background: t.color.primary,
            color: t.color.primaryText,
            border: "none",
            borderRadius: t.radius.sm,
            fontWeight: t.font.weightMedium,
            cursor: busy ? "default" : "pointer",
            opacity: busy ? 0.6 : 1,
            fontSize: t.font.sizeBase,
            fontFamily: t.font.family,
          }}
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
