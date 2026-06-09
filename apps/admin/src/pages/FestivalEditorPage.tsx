/**
 * Festival editor — create or edit a festival record.
 * Shows version history when editing an existing record.
 */

import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { content as api } from "@/api/client";
import type { FestivalIn, FestivalRecord } from "@/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { tokens } from "@/tokens";

const EMPTY: FestivalIn = {
  name: "",
  slug: "",
  date: "",
  description: "",
  body: "",
  puja: "",
  katha: "",
  tags: [],
  region: "all",
  locale: "en",
};

export function FestivalEditorPage() {
  const { id } = useParams<{ id: string }>();
  const isNew = id === "new" || !id;
  const navigate = useNavigate();

  const [record, setRecord] = useState<FestivalRecord | null>(null);
  const [form, setForm] = useState<FestivalIn>(EMPTY);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isNew) return;
    api.get(id!).then((r) => {
      setRecord(r);
      setForm(r.current);
      setLoading(false);
    }).catch((e) => {
      setError(e.message);
      setLoading(false);
    });
  }, [id, isNew]);

  function set<K extends keyof FestivalIn>(key: K, val: FestivalIn[K]) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (isNew) {
        const r = await api.create(form);
        navigate(`/content/${r.id}`);
      } else {
        const r = await api.update(id!, form);
        setRecord(r);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p aria-live="polite">Loading…</p>;

  return (
    <div style={{ maxWidth: 720 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: tokens.space.md,
          marginBottom: tokens.space.lg,
        }}
      >
        <button
          onClick={() => navigate("/content")}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: tokens.color.primary,
            padding: 0,
            fontSize: tokens.font.sizeBase,
          }}
        >
          ← Back
        </button>
        <h1 style={{ margin: 0, fontSize: tokens.font.sizeXl, fontWeight: tokens.font.weightBold }}>
          {isNew ? "New festival" : `Edit: ${record?.current.name}`}
        </h1>
        {record && <StatusBadge status={record.status} />}
      </div>

      {error && (
        <p role="alert" style={{ color: tokens.color.danger, marginBottom: tokens.space.md }}>
          {error}
        </p>
      )}

      <form
        onSubmit={save}
        style={{
          background: tokens.color.surface,
          padding: tokens.space.lg,
          borderRadius: tokens.radius.md,
          boxShadow: tokens.shadow.sm,
          display: "flex",
          flexDirection: "column",
          gap: tokens.space.md,
        }}
      >
        <Field label="Name *">
          <input
            required
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            style={inputStyle()}
          />
        </Field>

        <Field label="Slug *">
          <input
            required
            value={form.slug}
            onChange={(e) => set("slug", e.target.value)}
            style={inputStyle()}
          />
        </Field>

        <div style={{ display: "flex", gap: tokens.space.md }}>
          <Field label="Date (YYYY-MM-DD)" style={{ flex: 1 }}>
            <input
              value={form.date}
              onChange={(e) => set("date", e.target.value)}
              style={inputStyle()}
              placeholder="Leave blank — resolved by rule engine"
            />
          </Field>
          <Field label="Region" style={{ flex: 1 }}>
            <select
              value={form.region ?? "all"}
              onChange={(e) => set("region", e.target.value)}
              style={inputStyle()}
            >
              {["all", "north", "south", "east", "west"].map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </Field>
          <Field label="Locale" style={{ flex: 1 }}>
            <select
              value={form.locale ?? "en"}
              onChange={(e) => set("locale", e.target.value)}
              style={inputStyle()}
            >
              {["en", "hi", "gu", "mr", "ta", "te"].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Description">
          <textarea
            value={form.description ?? ""}
            onChange={(e) => set("description", e.target.value)}
            rows={2}
            style={inputStyle()}
          />
        </Field>

        <Field label="Body (prose)">
          <textarea
            value={form.body ?? ""}
            onChange={(e) => set("body", e.target.value)}
            rows={5}
            style={inputStyle()}
          />
        </Field>

        <Field label="Puja vidhi">
          <textarea
            value={form.puja ?? ""}
            onChange={(e) => set("puja", e.target.value)}
            rows={4}
            style={inputStyle()}
          />
        </Field>

        <Field label="Katha">
          <textarea
            value={form.katha ?? ""}
            onChange={(e) => set("katha", e.target.value)}
            rows={4}
            style={inputStyle()}
          />
        </Field>

        <Field label="Tags (comma-separated)">
          <input
            value={form.tags.join(", ")}
            onChange={(e) =>
              set(
                "tags",
                e.target.value
                  .split(",")
                  .map((t) => t.trim())
                  .filter(Boolean),
              )
            }
            style={inputStyle()}
          />
        </Field>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            type="submit"
            disabled={saving}
            style={{
              padding: `${tokens.space.sm} ${tokens.space.lg}`,
              background: tokens.color.primary,
              color: tokens.color.primaryText,
              border: "none",
              borderRadius: tokens.radius.sm,
              fontWeight: tokens.font.weightMedium,
              cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.7 : 1,
              fontSize: tokens.font.sizeBase,
            }}
          >
            {saving ? "Saving…" : "Save draft"}
          </button>
        </div>
      </form>

      {/* Version history */}
      {record && record.versions.length > 0 && (
        <section style={{ marginTop: tokens.space.xl }}>
          <h2 style={{ fontSize: tokens.font.sizeLg, fontWeight: tokens.font.weightBold, marginBottom: tokens.space.md }}>
            Version history
          </h2>
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
                {["Version", "Status", "Changed by", "Date"].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
                      padding: `${tokens.space.sm} ${tokens.space.md}`,
                      fontSize: tokens.font.sizeSm,
                      color: tokens.color.textMuted,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...record.versions].reverse().map((v) => (
                <tr key={v.version} style={{ borderBottom: `1px solid ${tokens.color.border}` }}>
                  <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>v{v.version}</td>
                  <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}` }}>
                    <StatusBadge status={v.status} />
                  </td>
                  <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, fontFamily: "monospace", fontSize: tokens.font.sizeSm }}>
                    {v.changed_by}
                  </td>
                  <td style={{ padding: `${tokens.space.sm} ${tokens.space.md}`, fontSize: tokens.font.sizeSm, color: tokens.color.textMuted }}>
                    {new Date(v.changed_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function Field({
  label,
  children,
  style,
}: {
  label: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: tokens.space.xs, ...style }}>
      <span style={{ fontSize: tokens.font.sizeSm, fontWeight: tokens.font.weightMedium, color: tokens.color.textMuted }}>
        {label}
      </span>
      {children}
    </label>
  );
}

function inputStyle(): React.CSSProperties {
  return {
    padding: tokens.space.sm,
    border: `1px solid ${tokens.color.border}`,
    borderRadius: tokens.radius.sm,
    fontSize: tokens.font.sizeBase,
    fontFamily: "inherit",
    color: tokens.color.text,
    background: tokens.color.surface,
    width: "100%",
    boxSizing: "border-box",
    resize: "vertical",
  };
}
