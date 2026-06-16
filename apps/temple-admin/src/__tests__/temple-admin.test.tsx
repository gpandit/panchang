/**
 * Temple-admin console unit tests. API calls are mocked so tests run without a backend.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { TempleSettingsPage } from "@/pages/TempleSettingsPage";
import * as client from "@/api/client";

const SESSION_KEY = "pandit_temple_token";

function makeToken(templeId: string) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({ sub: "u1", temple_id: templeId, email: "a@t.org", exp: 9999999999 }),
  );
  return `${header}.${payload}.sig`;
}

function Wrapper({ children }: { children: React.ReactNode }) {
  sessionStorage.setItem(SESSION_KEY, makeToken("temple-x"));
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

vi.mock("@/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof client>();
  return {
    ...original,
    auth: { login: vi.fn(), me: vi.fn() },
    temple: { get: vi.fn(), update: vi.fn() },
  };
});

const mockConfig: client.TempleConfig = {
  id: "temple-x",
  name: "Test Mandir",
  name_dev: "टेस्ट मंदिर",
  tagline: "Dharma",
  location: { label: "Dubai", lat: 25.2, lon: 55.27, tz: "Asia/Dubai" },
  aarti: [{ key: "mangala", name: "Maṅgala", dev: "मंगला", time: "05:00", note: "Dawn" }],
  events: [],
  updated_at: "2026-06-15T00:00:00Z",
};

describe("TempleSettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("loads and renders the assigned temple with its location and aarti", async () => {
    vi.mocked(client.auth.me).mockResolvedValue(mockConfig);

    render(
      <Wrapper>
        <TempleSettingsPage />
      </Wrapper>,
    );

    await waitFor(() => expect(screen.getByText("Test Mandir")).toBeInTheDocument());
    expect(screen.getByDisplayValue("Dubai")).toBeInTheDocument();
    expect(screen.getByDisplayValue("25.2")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Maṅgala")).toBeInTheDocument();
    expect(screen.getByText("Save changes")).toBeInTheDocument();
  });
});
