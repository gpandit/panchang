/**
 * Reports — signups, active users, conversions.
 * Non-sensitive aggregate metrics only; no birth/family data.
 */

import { useEffect, useState } from "react";
import { reporting as api } from "@/api/client";
import type { ReportOut, ReportRow } from "@/api/client";
import { tokens } from "@/tokens";

type Period = "last_7d" | "last_30d" | "last_90d";

export function ReportsPage() {
  const [period, setPeriod] = useState<Period>("last_30d");
  const [report, setReport] = useState<ReportOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .overview(period)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: tokens.space.md,
          marginBottom: tokens.space.lg,
        }}
      >
        <h1 style={{ margin: 0, fontSize: tokens.font.sizeXl, fontWeight: tokens.font.weightBold }}>
          Reports
        </h1>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as Period)}
          aria-label="Reporting period"
          style={{
            padding: `${tokens.space.sm} ${tokens.space.md}`,
            border: `1px solid ${tokens.color.border}`,
            borderRadius: tokens.radius.sm,
            fontSize: tokens.font.sizeBase,
            background: tokens.color.surface,
            color: tokens.color.text,
          }}
        >
          <option value="last_7d">Last 7 days</option>
          <option value="last_30d">Last 30 days</option>
          <option value="last_90d">Last 90 days</option>
        </select>
      </div>

      {error && (
        <p role="alert" style={{ color: tokens.color.danger, marginBottom: tokens.space.md }}>
          {error}
        </p>
      )}

      {loading && <p aria-live="polite">Loading…</p>}

      {!loading && report && (
        <>
          {/* Summary cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: tokens.space.md,
              marginBottom: tokens.space.xl,
            }}
          >
            <MetricCard label="Signups" value={report.totals.signups} />
            <MetricCard label="Peak active users" value={report.totals.active_users} />
            <MetricCard label="Conversions" value={report.totals.conversions} />
          </div>

          {/* Day-by-day table */}
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              background: tokens.color.surface,
              borderRadius: tokens.radius.md,
              boxShadow: tokens.shadow.sm,
            }}
          >
            <thead>
              <tr style={{ borderBottom: `1px solid ${tokens.color.border}` }}>
                {["Date", "Signups", "Active users", "Conversions"].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
                      padding: `${tokens.space.sm} ${tokens.space.md}`,
                      fontSize: tokens.font.sizeSm,
                      fontWeight: tokens.font.weightMedium,
                      color: tokens.color.textMuted,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.rows.map((r) => (
                <ReportRowEl key={r.date} row={r} />
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        background: tokens.color.surface,
        borderRadius: tokens.radius.md,
        boxShadow: tokens.shadow.sm,
        padding: tokens.space.lg,
      }}
    >
      <div
        style={{
          fontSize: tokens.font.sizeSm,
          color: tokens.color.textMuted,
          marginBottom: tokens.space.xs,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: tokens.font.sizeXl, fontWeight: tokens.font.weightBold }}>
        {value.toLocaleString()}
      </div>
    </div>
  );
}

function ReportRowEl({ row }: { row: ReportRow }) {
  return (
    <tr style={{ borderBottom: `1px solid ${tokens.color.border}` }}>
      <td
        style={{
          padding: `${tokens.space.sm} ${tokens.space.md}`,
          fontFamily: "monospace",
          fontSize: tokens.font.sizeSm,
        }}
      >
        {row.date}
      </td>
      <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>{row.signups}</td>
      <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>{row.active_users}</td>
      <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>{row.conversions}</td>
    </tr>
  );
}
