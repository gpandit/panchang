/**
 * Admin console unit tests.
 * API calls are mocked so tests run without a running backend.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ContentPage } from "@/pages/ContentPage";
import { FlagsPage } from "@/pages/FlagsPage";
import { ReportsPage } from "@/pages/ReportsPage";
import * as client from "@/api/client";

// ── Mock token helpers ─────────────────────────────────────────────────────────

const SESSION_KEY = "pandit_admin_token";

function makeToken(role: string) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(JSON.stringify({ sub: "u1", admin_role: role, exp: 9999999999 }));
  return `${header}.${payload}.sig`;
}

function Wrapper({
  role,
  children,
}: {
  role: string;
  children: React.ReactNode;
}) {
  // Pre-populate sessionStorage so AuthProvider picks it up on mount
  sessionStorage.setItem(SESSION_KEY, makeToken(role));
  return (
    <MemoryRouter>
      <AuthProvider>
        {children}
      </AuthProvider>
    </MemoryRouter>
  );
}

// ── Mock API module ────────────────────────────────────────────────────────────

vi.mock("@/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof client>();
  return {
    ...original,
    content: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      submitReview: vi.fn(),
      publish: vi.fn(),
      reject: vi.fn(),
      delete: vi.fn(),
      audit: vi.fn(),
    },
    flags: {
      list: vi.fn(),
      get: vi.fn(),
      report: vi.fn(),
      resolve: vi.fn(),
    },
    reporting: {
      overview: vi.fn(),
    },
  };
});

const mockContent = client.content as Record<string, ReturnType<typeof vi.fn>>;
const mockFlags = client.flags as Record<string, ReturnType<typeof vi.fn>>;
const mockReporting = client.reporting as Record<string, ReturnType<typeof vi.fn>>;

// ── Content management tests ───────────────────────────────────────────────────

describe("ContentPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a list of festival records", async () => {
    mockContent.list.mockResolvedValueOnce([
      {
        id: "fest-1",
        status: "draft",
        versions: [{ version: 1, status: "draft", changed_by: "u1", changed_at: new Date().toISOString(), snapshot: {} }],
        current: { name: "Test Festival", slug: "test-festival", date: "", tags: [], region: "all", locale: "en" },
        created_by: "u1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    render(
      <Wrapper role="editor">
        <ContentPage />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Test Festival")).toBeInTheDocument();
    });
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("shows submit-for-review button for draft records to editors", async () => {
    mockContent.list.mockResolvedValueOnce([
      {
        id: "fest-1",
        status: "draft",
        versions: [],
        current: { name: "A Festival", slug: "a-festival", date: "", tags: [], region: "all", locale: "en" },
        created_by: "u1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    render(
      <Wrapper role="editor">
        <ContentPage />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Submit for review")).toBeInTheDocument();
    });
  });

  it("does not show publish button to editors", async () => {
    mockContent.list.mockResolvedValueOnce([
      {
        id: "fest-1",
        status: "review",
        versions: [],
        current: { name: "In Review", slug: "in-review", date: "", tags: [], region: "all", locale: "en" },
        created_by: "u1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    render(
      <Wrapper role="editor">
        <ContentPage />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("In Review")).toBeInTheDocument();
    });
    expect(screen.queryByText("Publish")).not.toBeInTheDocument();
  });

  it("shows publish and reject buttons to publishers for review-status records", async () => {
    mockContent.list.mockResolvedValueOnce([
      {
        id: "fest-1",
        status: "review",
        versions: [],
        current: { name: "Ready to Publish", slug: "ready", date: "", tags: [], region: "all", locale: "en" },
        created_by: "u1",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    render(
      <Wrapper role="publisher">
        <ContentPage />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Publish")).toBeInTheDocument();
      expect(screen.getByText("Reject")).toBeInTheDocument();
    });
  });
});

// ── Flag queue tests ───────────────────────────────────────────────────────────

describe("FlagsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders open flags from the queue", async () => {
    mockFlags.list.mockResolvedValueOnce([
      {
        id: "flag-1",
        resource_type: "festival",
        resource_id: "fest-diwali",
        reason: "wrong_date",
        details: "Off by one day",
        reported_by: "user-001",
        reported_at: new Date().toISOString(),
        status: "open",
      },
    ]);

    render(
      <Wrapper role="editor">
        <FlagsPage />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("wrong_date")).toBeInTheDocument();
      expect(screen.getByText("fest-diwali")).toBeInTheDocument();
    });
  });

  it("shows resolve and dismiss buttons for open flags", async () => {
    mockFlags.list.mockResolvedValueOnce([
      {
        id: "flag-1",
        resource_type: "panchang_date",
        resource_id: "2026-01-15",
        reason: "incorrect_tithi",
        reported_by: "u2",
        reported_at: new Date().toISOString(),
        status: "open",
      },
    ]);

    render(
      <Wrapper role="editor">
        <FlagsPage />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Resolve")).toBeInTheDocument();
      expect(screen.getByText("Dismiss")).toBeInTheDocument();
    });
  });
});

// ── Reports tests ──────────────────────────────────────────────────────────────

describe("ReportsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders signups, active users and conversions from report data", async () => {
    mockReporting.overview.mockResolvedValueOnce({
      period: "last_7d",
      rows: [
        { date: "2026-06-09", signups: 12, active_users: 95, conversions: 2 },
      ],
      totals: { date: "total", signups: 12, active_users: 95, conversions: 2 },
    });

    render(
      <Wrapper role="viewer">
        <ReportsPage />
      </Wrapper>,
    );

    await waitFor(() => {
      // "Signups" appears in both the metric card and the table header
      const signupEls = screen.getAllByText("Signups");
      expect(signupEls.length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("12").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("95").length).toBeGreaterThanOrEqual(1);
    });
  });
});
