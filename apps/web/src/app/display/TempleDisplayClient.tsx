"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { JSX } from "react";

// ── Palette (Festival direction, scaled for large signage) ───────────────────
const D = {
  cream: "#FBF1DF",
  paper: "#FFFFFF",
  maroon: "#7C1D2B",
  maroonDeep: "#4B0F18",
  saffron: "#DC5F1B",
  saffronHi: "#F0872E",
  gold: "#C4912F",
  goldHi: "#E7B84E",
  goldPale: "#EAD7A6",
  ink: "#33150B",
  body: "#5E3826",
  mute: "#9A745C",
  faint: "#C2A488",
  line: "rgba(124,29,43,0.16)",
  lineSoft: "rgba(124,29,43,0.08)",
  good: "#5C6B36",
  goodBg: "rgba(92,107,54,0.10)",
  bad: "#B23A1E",
  badBg: "rgba(178,58,30,0.08)",
  disp: "'Marcellus', Georgia, serif",
  sans: "'Mukta', system-ui, sans-serif",
};

// ── Languages ────────────────────────────────────────────────────────────────
const LANGS = [
  { code: "hi", name: "हिन्दी", script: "Devanagari" },
  { code: "mr", name: "मराठी", script: "Devanagari" },
  { code: "sa", name: "संस्कृतम्", script: "Devanagari" },
  { code: "gu", name: "ગુજરાતી", script: "Gujarati" },
  { code: "ta", name: "தமிழ்", script: "Tamil" },
  { code: "te", name: "తెలుగు", script: "Telugu" },
  { code: "kn", name: "ಕನ್ನಡ", script: "Kannada" },
  { code: "bn", name: "বাংলা", script: "Bengali" },
  { code: "ml", name: "മലയാളം", script: "Malayalam" },
];

// ── Temple identity (placeholder — admin-editable) ───────────────────────────
const TEMPLE = {
  name: "Shree Siddhivinayak Mandir",
  nameDev: "श्री सिद्धिविनायक मंदिर",
  tagline: "Sanātana Dharma",
  location: "Dubai · United Arab Emirates",
};

// ── Panchang data (Mon 8 June 2026, Dubai — Sankashti Chaturthi) ─────────────
const PANDIT = {
  greg: { weekday: "Monday", day: "08", month: "June", year: 2026 },
  vara: "Somvar",
  paksha: "Krishna Paksha",
  month: { amanta: "Jyeshtha", purnimanta: "Ashadha" },
  hinduDate: "Krishna Tritiya",
  samvat: { vikram: "2083 Kalayukta" },
  angas: {
    tithi: { name: "Tritiya", upto: "14:32" },
    nakshatra: { name: "Uttara Ashadha", upto: "19:11" },
    yoga: { name: "Brahma", upto: "09:50" },
    karana: { name: "Vishti", upto: "14:32" },
  },
  sun: { rise: "05:34", set: "19:08" },
  moon: { rise: "22:47", set: "08:12" },
  good: [
    { name: "Abhijit Muhurat", time: ["12:01", "12:54"] },
    { name: "Brahma Muhurat", time: ["04:10", "04:58"] },
    { name: "Amrit Kalam", time: ["24:38", "26:14"] },
  ],
  avoid: [
    { name: "Rahu Kalam", time: ["07:18", "09:01"] },
    { name: "Yamaganda", time: ["10:44", "12:27"] },
    { name: "Gulika Kalam", time: ["14:10", "15:53"] },
  ],
  highlight: { title: "Sankashti Chaturthi", deity: "Ganesha", moonrise: "22:47" },
  mantra: { dev: "ॐ गं गणपतये नमः", tr: "Oṃ Gaṃ Gaṇapataye Namaḥ", count: 108 },
};

// ── Aarti schedule (placeholder — admin-editable) ────────────────────────────
const AARTI = {
  darshan: { morning: ["05:00", "12:30"], evening: ["16:00", "21:00"] },
  schedule: [
    {
      key: "mangala",
      name: "Maṅgala Ārati",
      dev: "मंगला आरती",
      time: "05:00",
      note: "Awakening",
      nat: {
        hi: "मंगला आरती",
        mr: "मंगला आरती",
        sa: "मङ्गला आरती",
        gu: "મંગળા આરતી",
        ta: "மங்கள ஆரத்தி",
        te: "మంగళ హారతి",
        kn: "ಮಂಗಳ ಆರತಿ",
        bn: "মঙ্গল আরতি",
        ml: "മംഗള ആരതി",
      },
    },
    {
      key: "shringar",
      name: "Śṛṅgāra Ārati",
      dev: "शृंगार आरती",
      time: "08:30",
      note: "Adornment",
      nat: {
        hi: "शृंगार आरती",
        mr: "शृंगार आरती",
        sa: "शृङ्गार आरती",
        gu: "શૃંગાર આરતી",
        ta: "சிருங்கார ஆரத்தி",
        te: "శృంగార హారతి",
        kn: "ಶೃಂಗಾರ ಆರತಿ",
        bn: "শৃঙ্গার আরতি",
        ml: "ശൃംഗാര ആരതി",
      },
    },
    {
      key: "rajbhog",
      name: "Rājbhoga Ārati",
      dev: "राजभोग आरती",
      time: "12:00",
      note: "Midday bhoga",
      nat: {
        hi: "राजभोग आरती",
        mr: "राजभोग आरती",
        sa: "राजभोग आरती",
        gu: "રાજભોગ આરતી",
        ta: "ராஜ்போக ஆரத்தி",
        te: "రాజభోగ హారతి",
        kn: "ರಾಜಭೋಗ ಆರತಿ",
        bn: "রাজভোগ আরতি",
        ml: "രാജഭോഗ ആരതി",
      },
    },
    {
      key: "sandhya",
      name: "Sandhyā Ārati",
      dev: "संध्या आरती",
      time: "19:00",
      note: "Dusk",
      nat: {
        hi: "संध्या आरती",
        mr: "संध्या आरती",
        sa: "सन्ध्या आरती",
        gu: "સંધ્યા આરતી",
        ta: "சந்தியா ஆரத்தி",
        te: "సంధ్యా హారతి",
        kn: "ಸಂಧ್ಯಾ ಆರತಿ",
        bn: "সন্ধ্যা আরতি",
        ml: "സന്ധ്യാ ആരതി",
      },
    },
    {
      key: "shayan",
      name: "Śayana Ārati",
      dev: "शयन आरती",
      time: "20:45",
      note: "Rest",
      nat: {
        hi: "शयन आरती",
        mr: "शयन आरती",
        sa: "शयन आरती",
        gu: "શયન આરતી",
        ta: "சயன ஆரத்தி",
        te: "శయన హారతి",
        kn: "ಶಯನ ಆರತಿ",
        bn: "শয়ন আরতি",
        ml: "ശയന ആരതി",
      },
    },
  ],
};

// ── Mantra data ──────────────────────────────────────────────────────────────
const MANTRA = {
  dev: "ॐ गं गणपतये नमः",
  tr: "Oṃ Gaṃ Gaṇapataye Namaḥ",
  count: 108,
  meaning: {
    en: "I bow to Shri Ganesha, the remover of all obstacles.",
    hi: "विघ्नहर्ता श्री गणेश को नमस्कार।",
    mr: "विघ्नहर्ता श्री गणेशाला नमस्कार.",
    sa: "विघ्नहर्त्रे श्रीगणेशाय नमः।",
    gu: "વિઘ્નહર્તા શ્રી ગણેશને નમસ્કાર.",
    ta: "தடைகளை நீக்கும் ஸ்ரீ விநாயகரை வணங்குகிறேன்.",
    te: "విఘ్నాలను తొలగించే శ్రీ గణేశునికి నమస్కారం.",
    kn: "ವಿಘ್ನಗಳನ್ನು ನಿವಾರಿಸುವ ಶ್ರೀ ಗಣೇಶನಿಗೆ ನಮಸ್ಕಾರ.",
    bn: "বিঘ্নহর্তা শ্রী গণেশকে নমস্কার।",
    ml: "വിഘ്നങ്ങള്‍ നീക്കുന്ന ശ്രീ ഗണേശന് നമസ്കാരം.",
  } as Record<string, string>,
  shlokaDev:
    "वक्रतुण्ड महाकाय सूर्यकोटि समप्रभ।\nनिर्विघ्नं कुरु मे देव सर्वकार्येषु सर्वदा॥",
  shlokaTr:
    "Vakratuṇḍa mahākāya sūryakoṭi samaprabha · nirvighnaṃ kuru me deva sarvakāryeṣu sarvadā",
};

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt12(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const h24 = (h ?? 0) % 24;
  const period = h24 < 12 ? "AM" : "PM";
  const h12 = ((h24 + 11) % 12) + 1;
  return `${h12}:${String(m ?? 0).padStart(2, "0")} ${period}`;
}

function toMins(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return (h ?? 0) * 60 + (m ?? 0);
}

function nowMins(): number {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}

function isActive(time: [string, string]): boolean {
  const now = nowMins();
  return now >= toMins(time[0]) && now < toMins(time[1]);
}

function nextAarti(
  schedule: typeof AARTI.schedule,
): (typeof AARTI.schedule)[0] | null {
  const now = nowMins();
  return schedule.find((a) => toMins(a.time) > now) ?? null;
}

function darshantStatus(darshan: typeof AARTI.darshan): {
  open: boolean;
  label: string;
  session: string;
} {
  const now = nowMins();
  const ms = toMins(darshan.morning[0]!);
  const me = toMins(darshan.morning[1]!);
  const es = toMins(darshan.evening[0]!);
  const ee = toMins(darshan.evening[1]!);
  if (now >= ms && now < me) return { open: true, label: "Open", session: "Morning" };
  if (now >= es && now < ee) return { open: true, label: "Open", session: "Evening" };
  return { open: false, label: "Closed", session: "" };
}

// ── Board selector ────────────────────────────────────────────────────────────
type Board = "panchang" | "aarti" | "mantra";

const BOARDS: { id: Board; label: string }[] = [
  { id: "panchang", label: "Today's Panchang" },
  { id: "aarti", label: "Darshan & Ārati" },
  { id: "mantra", label: "Mantra & Shloka" },
];

// ── Main component ────────────────────────────────────────────────────────────
export function TempleDisplayClient(): JSX.Element {
  const [board, setBoard] = useState<Board>("panchang");
  const [langIdx, setLangIdx] = useState(0);
  const [clock, setClock] = useState(new Date());
  const [visible, setVisible] = useState(true);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null);

  // Live clock
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // Language rotation every 7 seconds with crossfade
  useEffect(() => {
    const id = setInterval(() => {
      setVisible(false);
      timerRef.current = setTimeout(() => {
        setLangIdx((i) => (i + 1) % LANGS.length);
        setVisible(true);
      }, 650);
    }, 7000);
    return () => {
      clearInterval(id);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const lang = LANGS[langIdx]!;
  const timeStr = clock.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: D.cream, fontFamily: D.sans }}
    >
      {/* Masthead */}
      <Masthead lang={lang} timeStr={timeStr} visible={visible} />

      {/* Board selector tabs */}
      <div
        className="flex gap-0 border-b"
        style={{ borderColor: D.line, background: D.cream }}
        role="tablist"
        aria-label="Display board selection"
      >
        {BOARDS.map((b) => (
          <button
            key={b.id}
            role="tab"
            aria-selected={board === b.id}
            onClick={() => setBoard(b.id)}
            className="flex-1 py-3 text-sm font-bold transition-colors"
            style={
              board === b.id
                ? {
                    color: D.maroon,
                    borderBottom: `2px solid ${D.saffron}`,
                    background: "transparent",
                  }
                : {
                    color: D.mute,
                    borderBottom: "2px solid transparent",
                    background: "transparent",
                  }
            }
          >
            {b.label}
          </button>
        ))}
      </div>

      {/* Board content */}
      <div className="flex-1 overflow-auto p-6 lg:p-10">
        {board === "panchang" && (
          <PanchangBoard lang={lang} visible={visible} clock={clock} />
        )}
        {board === "aarti" && <AartiBoard lang={lang} visible={visible} clock={clock} />}
        {board === "mantra" && <MantraBoard lang={lang} visible={visible} />}
      </div>

      {/* Footer */}
      <Footer lang={lang} langIdx={langIdx} visible={visible} />
    </div>
  );
}

// ── Masthead ──────────────────────────────────────────────────────────────────
function Masthead({
  lang,
  timeStr,
  visible,
}: {
  lang: (typeof LANGS)[0];
  timeStr: string;
  visible: boolean;
}): JSX.Element {
  return (
    <header
      className="arch-motif flex items-center justify-between px-8 py-4"
      style={{ background: `linear-gradient(160deg, ${D.maroon}, ${D.maroonDeep})` }}
    >
      <div className="flex items-center gap-4">
        <div
          className="flex h-14 w-14 items-center justify-center rounded-2xl"
          style={{ background: "rgba(255,255,255,0.12)", border: `1px solid rgba(231,184,78,0.35)` }}
        >
          <span style={{ fontSize: "2rem", lineHeight: 1 }} aria-hidden="true">
            ॐ
          </span>
        </div>
        <div>
          <p
            className="font-bold leading-tight"
            style={{ fontFamily: D.disp, fontSize: "1.6rem", color: "#FFF6EA" }}
          >
            {TEMPLE.name}
          </p>
          <Fade visible={visible}>
            <p
              className="text-sm mt-0.5"
              style={{ color: D.goldHi, fontFamily: D.sans, fontWeight: 600 }}
            >
              {TEMPLE.nameDev}
            </p>
          </Fade>
          <p className="text-xs mt-0.5" style={{ color: "rgba(255,246,234,0.6)" }}>
            {TEMPLE.location}
          </p>
        </div>
      </div>

      <div className="text-right">
        <p
          className="tabular"
          style={{
            fontFamily: D.disp,
            fontSize: "2.6rem",
            color: "#FFF6EA",
            lineHeight: 1,
            letterSpacing: "0.02em",
          }}
        >
          {timeStr}
        </p>
        <p className="text-sm mt-1" style={{ color: D.goldHi }}>
          {PANDIT.greg.weekday}, {PANDIT.greg.day} {PANDIT.greg.month} {PANDIT.greg.year}
        </p>
        <p className="text-xs" style={{ color: "rgba(255,246,234,0.7)" }}>
          {PANDIT.highlight.title} · {PANDIT.paksha}
        </p>
      </div>
    </header>
  );
}

// ── Panchang Board ────────────────────────────────────────────────────────────
function PanchangBoard({
  lang,
  visible,
  clock,
}: {
  lang: (typeof LANGS)[0];
  visible: boolean;
  clock: Date;
}): JSX.Element {
  const nowM = clock.getHours() * 60 + clock.getMinutes();

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto">
      {/* Festival hero */}
      <div
        className="rounded-3xl p-6 flex items-center gap-6"
        style={{
          background: `linear-gradient(125deg, ${D.saffronHi}, ${D.saffron} 60%, #C24A12)`,
          boxShadow: "0 22px 50px -26px rgba(220,95,27,0.85)",
        }}
      >
        <div
          className="flex h-20 w-20 items-center justify-center rounded-2xl flex-none"
          style={{ background: "rgba(255,255,255,0.18)", border: "1.5px solid rgba(255,246,234,0.5)" }}
        >
          <span style={{ fontSize: "3rem", lineHeight: 1 }} aria-hidden="true">
            ॐ
          </span>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-widest" style={{ color: "rgba(255,246,234,0.85)" }}>
            Today's Vrat
          </p>
          <p style={{ fontFamily: D.disp, fontSize: "2.2rem", color: "#fff", lineHeight: 1.05 }}>
            {PANDIT.highlight.title}
          </p>
          <Fade visible={visible}>
            <p className="text-lg mt-1" style={{ color: "#FFF6EA" }}>
              {lang.code === "hi"
                ? "संकष्टी चतुर्थी · श्री गणेश"
                : lang.code === "gu"
                  ? "સંકષ્ટી ચતુર્થી · શ્રી ગણેશ"
                  : `${PANDIT.highlight.title} · ${PANDIT.highlight.deity}`}
            </p>
          </Fade>
        </div>
        <div className="ml-auto text-right">
          <p className="text-xs font-bold uppercase tracking-widest" style={{ color: "rgba(255,246,234,0.7)" }}>
            Moonrise
          </p>
          <p style={{ fontFamily: D.disp, fontSize: "2rem", color: D.goldHi }} className="tabular">
            {fmt12(PANDIT.highlight.moonrise)}
          </p>
        </div>
      </div>

      {/* Angas grid */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: "Tithi", name: PANDIT.angas.tithi.name, sub: `until ${fmt12(PANDIT.angas.tithi.upto)}` },
          { label: "Nakshatra", name: "U. Ashadha", sub: `until ${fmt12(PANDIT.angas.nakshatra.upto)}` },
          { label: "Yoga", name: PANDIT.angas.yoga.name, sub: `until ${fmt12(PANDIT.angas.yoga.upto)}` },
          { label: "Karana", name: PANDIT.angas.karana.name, sub: `until ${fmt12(PANDIT.angas.karana.upto)}` },
          { label: "Moonsign", name: "Makara", sub: "Rashi" },
        ].map((a) => (
          <div
            key={a.label}
            className="rounded-2xl p-4"
            style={{ background: D.paper, border: `1px solid ${D.line}`, boxShadow: "0 6px 20px -14px rgba(124,29,43,0.4)" }}
          >
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: D.gold }}>
              {a.label}
            </p>
            <p style={{ fontFamily: D.disp, fontSize: "1.4rem", color: D.ink, lineHeight: 1.05, marginTop: 4 }}>
              {a.name}
            </p>
            <p className="text-sm mt-1 tabular" style={{ color: D.mute }}>
              {a.sub}
            </p>
          </div>
        ))}
      </div>

      {/* Sun / Moon strip */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Sunrise", time: PANDIT.sun.rise, icon: "🌅" },
          { label: "Sunset", time: PANDIT.sun.set, icon: "🌇" },
          { label: "Moonrise", time: PANDIT.moon.rise, icon: "🌕" },
          { label: "Moonset", time: PANDIT.moon.set, icon: "🌘" },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-2xl p-4 text-center"
            style={{ background: D.cream, border: `1px solid ${D.line}` }}
          >
            <p className="text-2xl" aria-hidden="true">
              {s.icon}
            </p>
            <p className="text-xs font-bold uppercase tracking-wider mt-2" style={{ color: D.gold }}>
              {s.label}
            </p>
            <p style={{ fontFamily: D.disp, fontSize: "1.4rem", color: D.ink }} className="tabular">
              {fmt12(s.time)}
            </p>
          </div>
        ))}
      </div>

      {/* Auspicious / Inauspicious */}
      <div className="grid grid-cols-2 gap-6">
        <MuhuratCol
          heading="Auspicious Windows"
          items={PANDIT.good}
          tone="good"
          nowMins={nowM}
        />
        <MuhuratCol heading="Avoid" items={PANDIT.avoid} tone="bad" nowMins={nowM} />
      </div>
    </div>
  );
}

function MuhuratCol({
  heading,
  items,
  tone,
  nowMins: nowM,
}: {
  heading: string;
  items: { name: string; time: string[] }[];
  tone: "good" | "bad";
  nowMins: number;
}): JSX.Element {
  const c = tone === "good" ? D.good : D.bad;
  const bg = tone === "good" ? D.goodBg : D.badBg;
  return (
    <div className="rounded-2xl p-5" style={{ background: D.paper, border: `1px solid ${D.line}` }}>
      <p
        className="text-xs font-bold uppercase tracking-wider mb-4"
        style={{ color: c, letterSpacing: "0.1em" }}
      >
        {heading}
      </p>
      <div className="flex flex-col gap-3">
        {items.map((item) => {
          const active =
            item.time[0] && item.time[1] ? isActive([item.time[0], item.time[1]] as [string, string]) : false;
          return (
            <div
              key={item.name}
              className="flex items-center justify-between rounded-xl px-4 py-3"
              style={{
                background: active ? bg : "transparent",
                border: active ? `1.5px solid ${c}` : `1px solid ${D.lineSoft}`,
              }}
            >
              <div>
                <p style={{ fontFamily: D.disp, fontSize: "1.1rem", color: D.ink }}>
                  {item.name}
                </p>
                {active && (
                  <p className="text-xs font-bold uppercase" style={{ color: c }}>
                    ● Now active
                  </p>
                )}
              </div>
              <p style={{ fontFamily: D.disp, fontSize: "1rem", color: c }} className="tabular">
                {item.time[0] && item.time[1]
                  ? `${fmt12(item.time[0])} – ${fmt12(item.time[1])}`
                  : ""}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Aarti Board ───────────────────────────────────────────────────────────────
function AartiBoard({
  lang,
  visible,
  clock,
}: {
  lang: (typeof LANGS)[0];
  visible: boolean;
  clock: Date;
}): JSX.Element {
  const status = darshantStatus(AARTI.darshan);
  const next = nextAarti(AARTI.schedule);
  const nowM = clock.getHours() * 60 + clock.getMinutes();

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      {/* Status banner */}
      <div
        className="rounded-3xl px-8 py-5 flex items-center justify-between"
        style={{
          background: status.open
            ? "rgba(92,107,54,0.12)"
            : "rgba(178,58,30,0.08)",
          border: `1.5px solid ${status.open ? D.good : D.bad}`,
        }}
      >
        <div>
          <div className="flex items-center gap-3">
            <span
              className="h-3 w-3 rounded-full"
              style={{ background: status.open ? D.good : D.bad }}
              aria-hidden="true"
            />
            <p
              style={{
                fontFamily: D.disp,
                fontSize: "2rem",
                color: status.open ? D.good : D.bad,
              }}
            >
              {status.label}
            </p>
          </div>
          {status.session ? (
            <p className="text-sm mt-1" style={{ color: D.mute }}>
              {status.session} Session
            </p>
          ) : null}
        </div>
        <div className="text-right">
          <p className="text-xs font-bold uppercase tracking-wider" style={{ color: D.gold }}>
            Darshan Hours
          </p>
          <p className="text-sm mt-1" style={{ color: D.ink }}>
            Morning: {fmt12(AARTI.darshan.morning[0]!)} – {fmt12(AARTI.darshan.morning[1]!)}
          </p>
          <p className="text-sm" style={{ color: D.ink }}>
            Evening: {fmt12(AARTI.darshan.evening[0]!)} – {fmt12(AARTI.darshan.evening[1]!)}
          </p>
        </div>
      </div>

      {/* Aarti schedule */}
      <div className="rounded-2xl overflow-hidden" style={{ border: `1px solid ${D.line}` }}>
        <div className="px-6 py-4" style={{ background: D.maroon }}>
          <p style={{ fontFamily: D.disp, fontSize: "1.3rem", color: "#FFF6EA" }}>
            Ārati Schedule
          </p>
        </div>
        <div style={{ background: D.paper }}>
          {AARTI.schedule.map((a) => {
            const isNext = next?.key === a.key;
            const isPast = toMins(a.time) < nowM;
            return (
              <div
                key={a.key}
                className="flex items-center justify-between px-6 py-4"
                style={{
                  borderBottom: `1px solid ${D.lineSoft}`,
                  background: isNext ? "rgba(196,145,47,0.08)" : "transparent",
                }}
              >
                <div>
                  <div className="flex items-center gap-3">
                    {isNext && (
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-bold"
                        style={{ background: D.gold, color: D.maroonDeep }}
                      >
                        Next
                      </span>
                    )}
                    <p
                      style={{
                        fontFamily: D.disp,
                        fontSize: "1.2rem",
                        color: isPast && !isNext ? D.faint : D.ink,
                      }}
                    >
                      {a.name}
                    </p>
                  </div>
                  <Fade visible={visible}>
                    <p className="text-sm mt-0.5" style={{ color: D.mute }}>
                      {a.nat[lang.code as keyof typeof a.nat] ?? a.dev}
                    </p>
                  </Fade>
                </div>
                <div className="text-right">
                  <p
                    style={{
                      fontFamily: D.disp,
                      fontSize: "1.3rem",
                      color: isPast && !isNext ? D.faint : D.saffron,
                    }}
                    className="tabular"
                  >
                    {fmt12(a.time)}
                  </p>
                  <p className="text-xs" style={{ color: D.mute }}>
                    {a.note}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Mantra Board ──────────────────────────────────────────────────────────────
function MantraBoard({
  lang,
  visible,
}: {
  lang: (typeof LANGS)[0];
  visible: boolean;
}): JSX.Element {
  const meaning = MANTRA.meaning[lang.code] ?? MANTRA.meaning["en"]!;

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto text-center">
      {/* Main mantra */}
      <div
        className="rounded-3xl px-10 py-10"
        style={{
          background: `linear-gradient(135deg, ${D.maroon}, ${D.maroonDeep})`,
          boxShadow: "0 20px 60px -30px rgba(90,19,32,0.6)",
        }}
      >
        <p
          className="text-xs font-bold uppercase tracking-widest mb-4"
          style={{ color: D.goldHi, letterSpacing: "0.2em" }}
        >
          Mantra of the Day · {PANDIT.highlight.deity}
        </p>
        <p
          style={{
            fontFamily: "'Tiro Devanagari Hindi', serif, " + D.disp,
            fontSize: "2.8rem",
            color: D.goldHi,
            lineHeight: 1.3,
          }}
        >
          {MANTRA.dev}
        </p>
        <p className="mt-4 text-lg italic" style={{ color: "rgba(255,246,234,0.8)" }}>
          {MANTRA.tr}
        </p>
        <div
          className="mt-6 rounded-2xl px-6 py-4"
          style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(231,184,78,0.25)" }}
        >
          <Fade visible={visible}>
            <p className="text-base leading-relaxed" style={{ color: "#FFF6EA" }}>
              {meaning}
            </p>
          </Fade>
          <p className="text-sm mt-2" style={{ color: D.goldHi }}>
            {MANTRA.meaning["en"]}
          </p>
        </div>
        <p className="mt-6 text-sm font-bold uppercase tracking-widest" style={{ color: "rgba(255,246,234,0.5)" }}>
          Japa count: {MANTRA.count}
        </p>
      </div>

      {/* Shloka */}
      <div
        className="rounded-3xl px-8 py-8"
        style={{ background: D.paper, border: `1px solid ${D.line}` }}
      >
        <p className="text-xs font-bold uppercase tracking-widest mb-5" style={{ color: D.gold }}>
          Shloka of the Day
        </p>
        <p
          style={{
            fontFamily: "'Tiro Devanagari Hindi', serif, " + D.disp,
            fontSize: "1.7rem",
            color: D.ink,
            lineHeight: 1.7,
            whiteSpace: "pre-line",
          }}
        >
          {MANTRA.shlokaDev}
        </p>
        <p className="mt-4 text-sm italic" style={{ color: D.mute }}>
          {MANTRA.shlokaTr}
        </p>
      </div>
    </div>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer({
  lang,
  langIdx,
  visible,
}: {
  lang: (typeof LANGS)[0];
  langIdx: number;
  visible: boolean;
}): JSX.Element {
  return (
    <footer
      className="flex items-center justify-between px-8 py-3"
      style={{ borderTop: `1px solid ${D.line}`, background: D.cream }}
    >
      <div className="flex items-center gap-3">
        <p className="text-xs font-bold" style={{ color: D.faint }}>
          Language:
        </p>
        <div className="flex gap-1">
          {LANGS.map((l, i) => (
            <div
              key={l.code}
              className="h-1.5 rounded-full transition-all"
              style={{
                width: i === langIdx ? "1.5rem" : "0.375rem",
                background: i === langIdx ? D.saffron : D.faint,
              }}
              aria-hidden="true"
            />
          ))}
        </div>
        <Fade visible={visible}>
          <p className="text-xs font-bold" style={{ color: D.body }}>
            {lang.name}
          </p>
        </Fade>
      </div>
      <p className="text-xs" style={{ color: D.faint }}>
        Powered by{" "}
        <span className="font-semibold" style={{ color: D.mute }}>
          The Pandit
        </span>
      </p>
    </footer>
  );
}

// ── Fade wrapper ──────────────────────────────────────────────────────────────
function Fade({ visible, children }: { visible: boolean; children: React.ReactNode }): JSX.Element {
  return (
    <span
      style={{
        opacity: visible ? 1 : 0,
        transition: "opacity 0.5s ease",
        display: "inline",
      }}
    >
      {children}
    </span>
  );
}
