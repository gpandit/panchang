/**
 * Flag / review queue — lists open flags and lets admins resolve or dismiss them.
 */

import React, { useCallback, useEffect, useState } from "react";
import { flags as api } from "@/api/client";
import type { FlagRecord } from "@/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { tokens } from "@/tokens";

export function FlagsPage() {
  const [records, setRecords] = useState<FlagRecord[]>([]);
  const [filter, setFilter] = useState<"open" | "resolved" | "dismissed" | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolveState, setResolveState] = useState<{
    flagId: string;
    action: "resolve" | "dismiss";
    note: string;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRecords(await api.list(filter || undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function submitResolve() {
    if (!resolveState) return;
    try {
      await api.resolve(resolveState.flagId, resolveState.action, resolveState.note);
      setResolveState(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: tokens.space.lg,
        }}
      >
        <h1 style={{ margin: 0, fontSize: tokens.font.sizeXl, fontWeight: tokens.font.weightBold }}>
          Flag Review Queue
        </h1>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as typeof filter)}
          aria-label="Filter by status"
          style={{
            padding: `${tokens.space.sm} ${tokens.space.md}`,
            border: `1px solid ${tokens.color.border}`,
            borderRadius: tokens.radius.sm,
            fontSize: tokens.font.sizeBase,
            background: tokens.color.surface,
            color: tokens.color.text,
          }}
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      {error && (
        <p role="alert" style={{ color: tokens.color.danger, marginBottom: tokens.space.md }}>
          {error}
        </p>
      )}

      {loading ? (
        <p aria-live="polite">Loading…</p>
      ) : records.length === 0 ? (
        <p style={{ color: tokens.color.textMuted }}>No flags matching filter.</p>
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
              {["Resource", "Resource ID", "Reason", "Reporter", "Date", "Status", "Actions"].map(
                (h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
                      padding: `${tokens.space.sm} ${tokens.space.md}`,
                      fontSize: tokens.font.sizeSm,
                      color: tokens.color.textMuted,
                      fontWeight: tokens.font.weightMedium,
                    }}
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {records.map((f) => (
              <tr key={f.id} style={{ borderBottom: `1px solid ${tokens.color.border}` }}>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>
                  {f.resource_type}
                </td>
                <td
                  style={{
                    padding: `${tokens.space.sm} ${tokens.space.md}`,
                    fontFamily: "monospace",
                    fontSize: tokens.font.sizeSm,
                  }}
                >
                  {f.resource_id}
                </td>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>{f.reason}</td>
                <td
                  style={{
                    padding: `${tokens.space.sm} ${tokens.space.md}`,
                    fontFamily: "monospace",
                    fontSize: tokens.font.sizeSm,
                  }}
                >
                  {f.reported_by}
                </td>
                <td
                  style={{
                    padding: `${tokens.space.sm} ${tokens.space.md}`,
                    color: tokens.color.textMuted,
                    fontSize: tokens.font.sizeSm,
                  }}
                >
                  {new Date(f.reported_at).toLocaleDateString()}
                </td>
                <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>
                  <StatusBadge status={f.status} />
                </td>
                <td
                  style={{
                    padding: `${tokens.space.sm} ${tokens.space.md}`,
                    display: "flex",
                    gap: tokens.space.xs,
                  }}
                >
                  {f.status === "open" && (
                    <>
                      <button
                        onClick={() =>
                          setResolveState({ flagId: f.id, action: "resolve", note: "" })
                        }
                        style={btnStyle(tokens.color.success)}
                      >
                        Resolve
                      </button>
                      <button
                        onClick={() =>
                          setResolveState({ flagId: f.id, action: "dismiss", note: "" })
                        }
                        style={btnStyle(tokens.color.textMuted)}
                      >
                        Dismiss
                      </button>
                    </>
                  )}
                  {f.resolution_note && (
                    <span style={{ fontSize: tokens.font.sizeSm, color: tokens.color.textMuted }}>
                      {f.resolution_note}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Resolution dialog */}
      {resolveState && (
        <div
          role="dialog"
          aria-label={`${resolveState.action} flag`}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div
            style={{
              background: tokens.color.surface,
              borderRadius: tokens.radius.lg,
              padding: tokens.space.xl,
              width: 400,
              display: "flex",
              flexDirection: "column",
              gap: tokens.space.md,
              boxShadow: tokens.shadow.md,
            }}
          >
            <h2
              style={{
                margin: 0,
                fontSize: tokens.font.sizeLg,
                fontWeight: tokens.font.weightBold,
                textTransform: "capitalize",
              }}
            >
              {resolveState.action} flag
            </h2>
            <label style={{ fontSize: tokens.font.sizeSm, color: tokens.color.textMuted }}>
              Resolution note (optional)
              <textarea
                value={resolveState.note}
                onChange={(e) => setResolveState((s) => s && { ...s, note: e.target.value })}
                rows={3}
                style={{
                  display: "block",
                  marginTop: tokens.space.xs,
                  width: "100%",
                  padding: tokens.space.sm,
                  border: `1px solid ${tokens.color.border}`,
                  borderRadius: tokens.radius.sm,
                  fontSize: tokens.font.sizeBase,
                  boxSizing: "border-box",
                  resize: "vertical",
                }}
              />
            </label>
            <div style={{ display: "flex", gap: tokens.space.sm, justifyContent: "flex-end" }}>
              <button
                onClick={() => setResolveState(null)}
                style={btnStyle(tokens.color.textMuted)}
              >
                Cancel
              </button>
              <button
                onClick={submitResolve}
                style={btnStyle(
                  resolveState.action === "resolve" ? tokens.color.success : tokens.color.danger,
                )}
              >
                Confirm {resolveState.action}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    padding: `${tokens.space.xs} ${tokens.space.sm}`,
    background: bg,
    color: tokens.color.primaryText,
    border: "none",
    borderRadius: tokens.radius.sm,
    cursor: "pointer",
    fontSize: tokens.font.sizeSm,
    whiteSpace: "nowrap",
  };
}
