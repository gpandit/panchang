/**
 * Temple Settings — the single working screen of the temple-admin console.
 * Loads the admin's assigned temple, lets them edit the session location
 * (lat/lon/tz, which drives tithi computation), the aarti schedule, and events.
 */

import { useCallback, useEffect, useState } from "react";
import type {
  AartiEntry,
  TempleConfig,
  TempleConfigIn,
  TempleEvent,
  TempleLocation,
} from "@/api/client";
import { auth, temple } from "@/api/client";
import { tokens as t } from "@/tokens";

// ── Shared style helpers ─────────────────────────────────────────────────────

const card: React.CSSProperties = {
  background: t.color.surface,
  border: `1px solid ${t.color.border}`,
  borderRadius: t.radius.lg,
  padding: t.space.lg,
  marginBottom: t.space.lg,
};

const label: React.CSSProperties = {
  display: "block",
  fontSize: t.font.sizeSm,
  color: t.color.textMuted,
  marginBottom: t.space.xs,
};

const input: React.CSSProperties = {
  width: "100%",
  padding: t.space.sm,
  border: `1px solid ${t.color.border}`,
  borderRadius: t.radius.sm,
  fontSize: t.font.sizeBase,
  boxSizing: "border-box",
  background: t.color.surfaceCard,
  color: t.color.text,
  fontFamily: t.font.family,
};

const sectionTitle: React.CSSProperties = {
  margin: `0 0 ${t.space.md}`,
  fontSize: t.font.sizeLg,
  fontWeight: t.font.weightBold,
  color: t.color.text,
};

const smallBtn: React.CSSProperties = {
  padding: `${t.space.xs} ${t.space.sm}`,
  border: `1px solid ${t.color.border}`,
  borderRadius: t.radius.sm,
  background: "transparent",
  color: t.color.textBody,
  cursor: "pointer",
  fontSize: t.font.sizeSm,
  fontFamily: t.font.family,
};

function Field({
  text,
  value,
  onChange,
  type = "text",
}: {
  text: string;
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label style={{ flex: 1, minWidth: 120 }}>
      <span style={label}>{text}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} style={input} />
    </label>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function TempleSettingsPage() {
  const [config, setConfig] = useState<TempleConfig | null>(null);
  const [loc, setLoc] = useState<TempleLocation | null>(null);
  const [aarti, setAarti] = useState<AartiEntry[]>([]);
  const [events, setEvents] = useState<TempleEvent[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const hydrate = useCallback((c: TempleConfig) => {
    setConfig(c);
    setLoc(c.location);
    setAarti(c.aarti);
    setEvents(c.events);
  }, []);

  useEffect(() => {
    auth
      .me()
      .then(hydrate)
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load temple"));
  }, [hydrate]);

  function updateLoc(patch: Partial<TempleLocation>) {
    setLoc((prev) => (prev ? { ...prev, ...patch } : prev));
  }

  // Aarti row helpers
  function addAarti() {
    setAarti((rows) => [...rows, { key: "", name: "", dev: "", time: "", note: "" }]);
  }
  function updateAarti(i: number, patch: Partial<AartiEntry>) {
    setAarti((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function removeAarti(i: number) {
    setAarti((rows) => rows.filter((_, idx) => idx !== i));
  }

  // Event row helpers
  function addEvent() {
    setEvents((rows) => [
      ...rows,
      { id: `evt-${Date.now()}`, title: "", date: "", description: "" },
    ]);
  }
  function updateEvent(i: number, patch: Partial<TempleEvent>) {
    setEvents((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function removeEvent(i: number) {
    setEvents((rows) => rows.filter((_, idx) => idx !== i));
  }

  async function handleSave() {
    if (!loc) return;
    setSaving(true);
    setSaveMsg(null);
    const payload: TempleConfigIn = { location: loc, aarti, events };
    try {
      const updated = await temple.update(payload);
      hydrate(updated);
      setSaveMsg("Saved. The Temple Display will reflect changes on its next refresh.");
    } catch (e) {
      setSaveMsg(e instanceof Error ? `Error: ${e.message}` : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loadError) {
    return (
      <p role="alert" style={{ color: t.color.danger }}>
        {loadError}
      </p>
    );
  }
  if (!config || !loc) {
    return <p style={{ color: t.color.textMuted }}>Loading temple…</p>;
  }

  return (
    <div style={{ maxWidth: 880 }}>
      <div style={{ marginBottom: t.space.lg }}>
        <h1 style={{ margin: 0, fontSize: t.font.size2xl, fontWeight: 700, color: t.color.text }}>
          {config.name}
        </h1>
        <p style={{ margin: "4px 0 0", color: t.color.textMuted }}>
          {config.name_dev} · {config.tagline}
        </p>
      </div>

      {/* Location */}
      <section style={card}>
        <h2 style={sectionTitle}>Session location</h2>
        <p style={{ marginTop: 0, fontSize: t.font.sizeSm, color: t.color.textMuted }}>
          Latitude &amp; longitude are used to compute the tithi and other Panchang elements for the
          display.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: t.space.md }}>
          <Field
            text="Location label"
            value={loc.label}
            onChange={(v) => updateLoc({ label: v })}
          />
          <Field text="Timezone (IANA)" value={loc.tz} onChange={(v) => updateLoc({ tz: v })} />
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: t.space.md, marginTop: t.space.md }}>
          <Field
            text="Latitude"
            type="number"
            value={loc.lat}
            onChange={(v) => updateLoc({ lat: Number(v) })}
          />
          <Field
            text="Longitude"
            type="number"
            value={loc.lon}
            onChange={(v) => updateLoc({ lon: Number(v) })}
          />
        </div>
      </section>

      {/* Aarti schedule */}
      <section style={card}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: t.space.md,
          }}
        >
          <h2 style={{ ...sectionTitle, margin: 0 }}>Aarti schedule</h2>
          <button onClick={addAarti} style={smallBtn}>
            + Add aarti
          </button>
        </div>
        {aarti.length === 0 && (
          <p style={{ fontSize: t.font.sizeSm, color: t.color.textFaint }}>No aarti rows yet.</p>
        )}
        {aarti.map((row, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: t.space.sm,
              alignItems: "flex-end",
              paddingBottom: t.space.md,
              marginBottom: t.space.md,
              borderBottom: `1px solid ${t.color.border}`,
            }}
          >
            <div style={{ width: 90 }}>
              <Field text="Time" value={row.time} onChange={(v) => updateAarti(i, { time: v })} />
            </div>
            <Field text="Name" value={row.name} onChange={(v) => updateAarti(i, { name: v })} />
            <Field text="Devanagari" value={row.dev} onChange={(v) => updateAarti(i, { dev: v })} />
            <Field text="Note" value={row.note} onChange={(v) => updateAarti(i, { note: v })} />
            <button
              onClick={() => removeAarti(i)}
              style={{ ...smallBtn, color: t.color.danger }}
              aria-label="Remove aarti"
            >
              Remove
            </button>
          </div>
        ))}
      </section>

      {/* Events */}
      <section style={card}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: t.space.md,
          }}
        >
          <h2 style={{ ...sectionTitle, margin: 0 }}>Events &amp; announcements</h2>
          <button onClick={addEvent} style={smallBtn}>
            + Add event
          </button>
        </div>
        {events.length === 0 && (
          <p style={{ fontSize: t.font.sizeSm, color: t.color.textFaint }}>No events yet.</p>
        )}
        {events.map((ev, i) => (
          <div
            key={ev.id}
            style={{
              paddingBottom: t.space.md,
              marginBottom: t.space.md,
              borderBottom: `1px solid ${t.color.border}`,
            }}
          >
            <div
              style={{ display: "flex", flexWrap: "wrap", gap: t.space.sm, alignItems: "flex-end" }}
            >
              <Field text="Title" value={ev.title} onChange={(v) => updateEvent(i, { title: v })} />
              <div style={{ width: 150 }}>
                <Field
                  text="Date"
                  type="date"
                  value={ev.date}
                  onChange={(v) => updateEvent(i, { date: v })}
                />
              </div>
              <div style={{ width: 110 }}>
                <Field
                  text="Time"
                  value={ev.time ?? ""}
                  onChange={(v) => updateEvent(i, { time: v })}
                />
              </div>
              <button
                onClick={() => removeEvent(i)}
                style={{ ...smallBtn, color: t.color.danger }}
                aria-label="Remove event"
              >
                Remove
              </button>
            </div>
            <div style={{ marginTop: t.space.sm }}>
              <Field
                text="Description"
                value={ev.description ?? ""}
                onChange={(v) => updateEvent(i, { description: v })}
              />
            </div>
          </div>
        ))}
      </section>

      {/* Save bar */}
      <div style={{ display: "flex", alignItems: "center", gap: t.space.md }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: `${t.space.sm} ${t.space.lg}`,
            background: t.color.primary,
            color: t.color.primaryText,
            border: "none",
            borderRadius: t.radius.sm,
            fontWeight: t.font.weightMedium,
            cursor: saving ? "default" : "pointer",
            opacity: saving ? 0.6 : 1,
            fontSize: t.font.sizeBase,
            fontFamily: t.font.family,
          }}
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
        {saveMsg && (
          <span
            role="status"
            style={{
              fontSize: t.font.sizeSm,
              color: saveMsg.startsWith("Error") ? t.color.danger : t.color.success,
            }}
          >
            {saveMsg}
          </span>
        )}
      </div>
    </div>
  );
}
