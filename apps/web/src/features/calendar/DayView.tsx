"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useState } from "react";
import type { CalendarDayCell, LocalNote, LocalReminder } from "./types";
import type { NoteInput } from "./api";
import { NoteEditor } from "./NoteEditor";
import { ReminderForm } from "./ReminderForm";
import { NoteList } from "./NoteList";
import { ReminderList } from "./ReminderList";
import type { ReminderInput } from "./api";

interface DayViewProps {
  cell: CalendarDayCell;
  notes: LocalNote[];
  reminders: LocalReminder[];
  onClose: () => void;
  onCreateNote: (noteIn: NoteInput) => Promise<void>;
  onUpdateNote: (id: string, noteIn: NoteInput) => Promise<void>;
  onDeleteNote: (id: string) => Promise<void>;
  onCreateReminder: (r: ReminderInput) => Promise<void>;
  onDeleteReminder: (id: string) => Promise<void>;
}

type DayTab = "notes" | "bookmarks" | "reminders";

export function DayView({
  cell,
  notes,
  reminders,
  onClose,
  onCreateNote,
  onUpdateNote,
  onDeleteNote,
  onCreateReminder,
  onDeleteReminder,
}: DayViewProps): React.JSX.Element {
  const { date, panchang, markers } = cell;
  const [activeTab, setActiveTab] = useState<DayTab>("notes");
  const [addingNote, setAddingNote] = useState(false);
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [addingReminder, setAddingReminder] = useState(false);

  const dayNotes = notes.filter((n) => n.date === date && !n.tags.includes("bookmark"));
  const dayBookmarks = notes.filter((n) => n.date === date && n.tags.includes("bookmark"));
  const dayReminders = reminders.filter(
    (r) => r.trigger_type === "gregorian" && r.trigger_value === date,
  );

  return (
    <section
      aria-label={`Day detail for ${date}`}
      className="flex flex-col border-t border-border bg-background"
    >
      {/* Day view header */}
      <header className="flex items-center justify-between px-md py-sm border-b border-border">
        <div>
          <h2 className="text-base font-semibold text-foreground">
            <time dateTime={date}>{date}</time>
          </h2>
          {markers.tithi && (
            <p className="text-sm text-muted-foreground">{markers.tithi}</p>
          )}
        </div>
        <button
          type="button"
          aria-label="Close day view"
          onClick={onClose}
          className="text-sm text-muted-foreground p-xs"
        >
          {/* TODO(design): close icon token */}
          ✕
        </button>
      </header>

      {/* Panchang summary (if data available) */}
      {panchang && (
        <dl
          aria-label="Panchang summary"
          className="flex flex-wrap gap-md px-md py-sm border-b border-border text-sm"
        >
          <div>
            <dt className="text-xs text-muted-foreground">Tithi</dt>
            <dd className="text-foreground">{panchang.tithi[0]?.name ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Nakshatra</dt>
            <dd className="text-foreground">{panchang.nakshatra[0]?.name ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Paksha</dt>
            <dd className="text-foreground">{panchang.calendrical.paksha}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Sunrise</dt>
            <dd className="text-foreground">
              {panchang.day_events.sunrise.hour_12}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Sunset</dt>
            <dd className="text-foreground">
              {panchang.day_events.sunset.hour_12}
            </dd>
          </div>
        </dl>
      )}

      {/* Festivals / vrats strip */}
      {(markers.festivals.length > 0 || markers.vrats.length > 0) && (
        <ul
          aria-label="Festivals and vrats"
          className="flex flex-wrap gap-xs px-md py-sm border-b border-border"
        >
          {markers.festivals.map((name) => (
            <li key={name} className="text-xs px-sm py-xs border border-border rounded-full text-foreground">
              {name}
            </li>
          ))}
          {markers.vrats.map((name) => (
            <li key={name} className="text-xs px-sm py-xs border border-border rounded-full text-muted-foreground">
              {name} (vrat)
            </li>
          ))}
        </ul>
      )}

      {/* Tab navigation */}
      <div
        role="tablist"
        aria-label="Day sections"
        className="flex border-b border-border px-md"
      >
        {(["notes", "bookmarks", "reminders"] as DayTab[]).map((tab) => {
          const counts = { notes: dayNotes.length, bookmarks: dayBookmarks.length, reminders: dayReminders.length };
          return (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              aria-controls={`panel-${tab}`}
              id={`tab-${tab}-${date}`}
              onClick={() => setActiveTab(tab)}
              className="px-md py-sm text-sm capitalize border-b-2 border-transparent aria-selected:border-primary aria-selected:text-primary text-muted-foreground"
            >
              {tab}
              {counts[tab] > 0 && (
                <span aria-label={`${counts[tab]} items`} className="ml-xs text-xs">
                  ({counts[tab]})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab panels */}
      <div className="flex flex-col gap-sm px-md py-sm">
        {activeTab === "notes" && (
          <div
            role="tabpanel"
            id={`panel-notes`}
            aria-labelledby={`tab-notes-${date}`}
            className="flex flex-col gap-sm"
          >
            <NoteList
              notes={dayNotes}
              date={date}
              onUpdate={onUpdateNote}
              onDelete={onDeleteNote}
            />

            {addingNote ? (
              <NoteEditor
                date={date}
                onSubmit={async (body, tags) => {
                  await onCreateNote({ date, body, tags });
                  setAddingNote(false);
                }}
                onCancel={() => setAddingNote(false)}
              />
            ) : (
              <button
                type="button"
                onClick={() => setAddingNote(true)}
                className="text-sm text-primary text-left"
              >
                + Add note
              </button>
            )}
          </div>
        )}

        {activeTab === "bookmarks" && (
          <div
            role="tabpanel"
            id={`panel-bookmarks`}
            aria-labelledby={`tab-bookmarks-${date}`}
            className="flex flex-col gap-sm"
          >
            <NoteList
              notes={dayBookmarks}
              isBookmarkList
              date={date}
              onUpdate={onUpdateNote}
              onDelete={onDeleteNote}
            />

            {addingBookmark ? (
              <NoteEditor
                date={date}
                isBookmark
                onSubmit={async (body, tags) => {
                  await onCreateNote({ date, body, tags });
                  setAddingBookmark(false);
                }}
                onCancel={() => setAddingBookmark(false)}
              />
            ) : (
              <button
                type="button"
                onClick={() => setAddingBookmark(true)}
                className="text-sm text-primary text-left"
              >
                + Add bookmark
              </button>
            )}
          </div>
        )}

        {activeTab === "reminders" && (
          <div
            role="tabpanel"
            id={`panel-reminders`}
            aria-labelledby={`tab-reminders-${date}`}
            className="flex flex-col gap-sm"
          >
            <ReminderList
              reminders={dayReminders}
              date={date}
              onDelete={onDeleteReminder}
            />

            {addingReminder ? (
              <ReminderForm
                date={date}
                onSubmit={async (r) => {
                  await onCreateReminder(r);
                  setAddingReminder(false);
                }}
                onCancel={() => setAddingReminder(false)}
              />
            ) : (
              <button
                type="button"
                onClick={() => setAddingReminder(true)}
                className="text-sm text-primary text-left"
              >
                + Add reminder
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
