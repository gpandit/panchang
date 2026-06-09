/**
 * Audit trail — who did what, when, on which resource.
 */

import React, { useEffect, useState } from "react";
import { content as api } from "@/api/client";
import type { AuditEntry } from "@/api/client";
import { tokens } from "@/tokens";

export function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [resourceType, setResourceType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .audit(resourceType ? { resource_type: resourceType } : {})
      .then(setEntries)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [resourceType]);

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
          Audit Trail
        </h1>
        <select
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value)}
          aria-label="Filter by resource type"
          style={{
            padding: `${tokens.space.sm} ${tokens.space.md}`,
            border: `1px solid ${tokens.color.border}`,
            borderRadius: tokens.radius.sm,
            fontSize: tokens.font.sizeBase,
            background: tokens.color.surface,
            color: tokens.color.text,
          }}
        >
          <option value="">All resources</option>
          <option value="festival">Festival</option>
          <option value="flag">Flag</option>
        </select>
      </div>

      {error && (
        <p role="alert" style={{ color: tokens.color.danger, marginBottom: tokens.space.md }}>
          {error}
        </p>
      )}

      {loading ? (
        <p aria-live="polite">Loading…</p>
      ) : entries.length === 0 ? (
        <p style={{ color: tokens.color.textMuted }}>No audit entries yet.</p>
      ) : (
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
              {["Timestamp", "Actor", "Action", "Resource", "Resource ID"].map((h) => (
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
            {entries.map((e) => (
              <tr key={e.id} style={{ borderBottom: `1px solid ${tokens.color.border}` }}>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, fontFamily: "monospace", fontSize: tokens.font.sizeSm, whiteSpace: "nowrap" }}>
                  {new Date(e.timestamp).toLocaleString()}
                </td>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, fontFamily: "monospace", fontSize: tokens.font.sizeSm }}>
                  {e.actor_email ?? e.actor_id}
                </td>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, fontFamily: "monospace", fontSize: tokens.font.sizeSm }}>
                  {e.action}
                </td>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>{e.resource_type}</td>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, fontFamily: "monospace", fontSize: tokens.font.sizeSm }}>
                  {e.resource_id}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
