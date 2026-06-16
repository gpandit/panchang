/**
 * AuthContext — holds the temple-admin JWT and the decoded temple_id.
 * Token lives in sessionStorage so it survives refresh within the tab but is
 * cleared when the tab closes (no persistent credential in localStorage).
 */

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { setToken } from "@/api/client";

const SESSION_KEY = "pandit_temple_token";

interface AuthState {
  token: string | null;
  sub: string | null;
  email: string | null;
  templeId: string | null;
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
  if (!token) return { token: null, sub: null, email: null, templeId: null };
  const payload = decodePayload(token);
  if (!payload) return { token: null, sub: null, email: null, templeId: null };
  return {
    token,
    sub: (payload["sub"] as string) ?? null,
    email: (payload["email"] as string) ?? null,
    templeId: (payload["temple_id"] as string) ?? null,
  };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>(() =>
    stateFromToken(sessionStorage.getItem(SESSION_KEY)),
  );

  // Sync the API-client token during render (not in an effect): a descendant's
  // mount effect — e.g. TempleSettingsPage calling auth.me() — runs before this
  // provider's effects would, so an effect here would let the first request go
  // out without the Authorization header. Setting it in render keeps the module
  // token current before any child effect fires.
  setToken(state.token);

  const login = useCallback((token: string) => {
    const payload = decodePayload(token);
    if (!payload) {
      throw new Error("Malformed token — cannot decode payload.");
    }
    if (payload["temple_id"] == null) {
      throw new Error("Token does not contain a temple_id claim.");
    }
    // Validate before writing so state and sessionStorage stay in sync.
    const next: AuthState = {
      token,
      sub: (payload["sub"] as string) ?? null,
      email: (payload["email"] as string) ?? null,
      templeId: payload["temple_id"] as string,
    };
    sessionStorage.setItem(SESSION_KEY, token);
    setState(next);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setState({ token: null, sub: null, email: null, templeId: null });
  }, []);

  const value = useMemo(() => ({ ...state, login, logout }), [state, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
