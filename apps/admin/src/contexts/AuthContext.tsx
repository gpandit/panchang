/**
 * AuthContext — holds the admin JWT and decoded role.
 * Token is stored in sessionStorage so it survives page refreshes within the tab
 * but is cleared when the tab closes (no persistent credential in localStorage).
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setToken } from "@/api/client";
import type { AdminRole } from "@/api/client";

const SESSION_KEY = "pandit_admin_token";

interface AuthState {
  token: string | null;
  sub: string | null;
  email: string | null;
  adminRole: AdminRole | null;
}

interface AuthContextValue extends AuthState {
  login: (token: string) => void;
  logout: () => void;
}

function decodePayload(token: string): Record<string, unknown> | null {
  try {
    const [, b64] = token.split(".");
    return JSON.parse(atob(b64.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

function stateFromToken(token: string | null): AuthState {
  if (!token) return { token: null, sub: null, email: null, adminRole: null };
  const payload = decodePayload(token);
  if (!payload) return { token: null, sub: null, email: null, adminRole: null };
  return {
    token,
    sub: (payload["sub"] as string) ?? null,
    email: (payload["email"] as string) ?? null,
    adminRole: (payload["admin_role"] as AdminRole) ?? null,
  };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() =>
    stateFromToken(sessionStorage.getItem(SESSION_KEY)),
  );

  useEffect(() => {
    setToken(state.token);
  }, [state.token]);

  const login = useCallback((token: string) => {
    const payload = decodePayload(token);
    if (!payload) {
      throw new Error("Malformed token — cannot decode payload.");
    }
    if (payload["admin_role"] == null) {
      throw new Error("Token does not contain an admin_role claim.");
    }
    // Validate before writing to storage so state and sessionStorage stay in sync.
    const next: AuthState = {
      token,
      sub: (payload["sub"] as string) ?? null,
      email: (payload["email"] as string) ?? null,
      adminRole: payload["admin_role"] as AdminRole,
    };
    sessionStorage.setItem(SESSION_KEY, token);
    setState(next);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setState({ token: null, sub: null, email: null, adminRole: null });
  }, []);

  const value = useMemo(() => ({ ...state, login, logout }), [state, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
