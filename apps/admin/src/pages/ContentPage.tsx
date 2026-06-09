/**
 * Content management — lists all festival records across all statuses,
 * with workflow action buttons and a link to the editor.
 */

import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { content as api } from "@/api/client";
import type { FestivalRecord } from "@/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/contexts/AuthContext";
import { tokens } from "@/tokens";

export function ContentPage() {
  const { adminRole } = useAuth();
  const navigate = useNavigate();
  const [records, setRecords] = useState<FestivalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const canEdit = adminRole === "editor" || adminRole === "publisher" || adminRole === "super_admin";
  const canPublish = adminRole === "publisher" || adminRole === "super_admin";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRecords(await api.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function doAction(action: () => Promise<FestivalRecord>) {
    setActionError(null);
    try {
      await action();
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    }
  }

  if (loading) return <p aria-live="polite">Loading…</p>;
  if (error) return <p role="alert" style={{ color: tokens.color.danger }}>{error}</p>;

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
          Festivals &amp; Content
        </h1>
        {canEdit && (
          <button
            onClick={() => navigate("/content/new")}
            style={{
              padding: `${tokens.space.sm} ${tokens.space.md}`,
              background: tokens.color.primary,
              color: tokens.color.primaryText,
              border: "none",
              borderRadius: tokens.radius.sm,
              cursor: "pointer",
              fontWeight: tokens.font.weightMedium,
            }}
          >
            + New festival
          </button>
        )}
      </div>

      {actionError && (
        <p role="alert" style={{ color: tokens.color.danger, marginBottom: tokens.space.md }}>
          {actionError}
        </p>
      )}

      {records.length === 0 && (
        <p style={{ color: tokens.color.textMuted }}>No records yet.</p>
      )}

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
            {["Name", "Slug", "Region", "Status", "Updated", "Actions"].map((h) => (
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
          {records.map((r) => (
            <tr
              key={r.id}
              style={{ borderBottom: `1px solid ${tokens.color.border}` }}
            >
              <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>
                <button
                  onClick={() => navigate(`/content/${r.id}`)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: tokens.color.primary,
                    fontWeight: tokens.font.weightMedium,
                    padding: 0,
                    fontSize: tokens.font.sizeBase,
                  }}
                >
                  {r.current.name}
                </button>
              </td>
              <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, color: tokens.color.textMuted, fontFamily: "monospace" }}>
                {r.current.slug}
              </td>
              <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>
                {r.current.region ?? "—"}
              </td>
              <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>
                <StatusBadge status={r.status} />
              </td>
              <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, color: tokens.color.textMuted, fontSize: tokens.font.sizeSm }}>
                {new Date(r.updated_at).toLocaleDateString()}
              </td>
              <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, display: "flex", gap: tokens.space.xs, flexWrap: "wrap" }}>
                {canEdit && r.status === "draft" && (
                  <ActionBtn
                    label="Submit for review"
                    onClick={() => doAction(() => api.submitReview(r.id))}
                  />
                )}
                {canPublish && r.status === "review" && (
                  <>
                    <ActionBtn
                      label="Publish"
                      onClick={() => doAction(() => api.publish(r.id))}
                      variant="success"
                    />
                    <ActionBtn
                      label="Reject"
                      onClick={() => doAction(() => api.reject(r.id))}
                      variant="danger"
                    />
                  </>
                )}
                {canEdit && r.status === "rejected" && (
                  <ActionBtn
                    label="Re-submit"
                    onClick={() => doAction(() => api.submitReview(r.id))}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActionBtn({
  label,
  onClick,
  variant = "default",
}: {
  label: string;
  onClick: () => void;
  variant?: "default" | "success" | "danger";
}) {
  const bg =
    variant === "success"
      ? tokens.color.success
      : variant === "danger"
      ? tokens.color.danger
      : tokens.color.primary;

  return (
    <button
      onClick={onClick}
      style={{
        padding: `${tokens.space.xs} ${tokens.space.sm}`,
        background: bg,
        color: tokens.color.primaryText,
        border: "none",
        borderRadius: tokens.radius.sm,
        cursor: "pointer",
        fontSize: tokens.font.sizeSm,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}
