/**
 * Login page — accepts a Bearer JWT (issued by the auth service).
 * In production, the auth service redirects back here with the token.
 * For dev/test we paste the token directly.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { tokens } from "@/tokens";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [tokenInput, setTokenInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      login(tokenInput.trim());
      navigate("/content");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid token");
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: tokens.color.surfaceAlt,
        fontFamily: tokens.font.family,
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: tokens.color.surface,
          padding: tokens.space.xl,
          borderRadius: tokens.radius.lg,
          boxShadow: tokens.shadow.md,
          width: 360,
          display: "flex",
          flexDirection: "column",
          gap: tokens.space.md,
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: tokens.font.sizeXl,
            fontWeight: tokens.font.weightBold,
            color: tokens.color.text,
          }}
        >
          The Pandit — Admin
        </h1>

        <label style={{ fontSize: tokens.font.sizeSm, color: tokens.color.textMuted }}>
          Bearer token
          <textarea
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            required
            rows={4}
            placeholder="Paste your admin JWT here"
            style={{
              display: "block",
              marginTop: tokens.space.xs,
              width: "100%",
              padding: tokens.space.sm,
              border: `1px solid ${tokens.color.border}`,
              borderRadius: tokens.radius.sm,
              fontFamily: "monospace",
              fontSize: tokens.font.sizeSm,
              resize: "vertical",
              boxSizing: "border-box",
              color: tokens.color.text,
            }}
          />
        </label>

        {error && (
          <p
            role="alert"
            style={{
              margin: 0,
              color: tokens.color.danger,
              fontSize: tokens.font.sizeSm,
            }}
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          style={{
            padding: `${tokens.space.sm} ${tokens.space.md}`,
            background: tokens.color.primary,
            color: tokens.color.primaryText,
            border: "none",
            borderRadius: tokens.radius.sm,
            fontWeight: tokens.font.weightMedium,
            cursor: "pointer",
            fontSize: tokens.font.sizeBase,
          }}
        >
          Sign in
        </button>
      </form>
    </div>
  );
}
