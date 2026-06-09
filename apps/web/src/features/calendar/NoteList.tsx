"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useState } from "react";
import type { LocalNote } from "./types";
import { NoteEditor } from "./NoteEditor";
import type { NoteInput } from "./api";

interface NoteListProps {
  notes: LocalNote[];
  isBookmarkList?: boolean;
  onUpdate: (id: string, noteIn: NoteInput) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  date: string;
}

export function NoteList({ notes, isBookmarkList = false, onUpdate, onDelete, date }: NoteListProps): React.JSX.Element {
  const [editingId, setEditingId] = useState<string | null>(null);
  const entityLabel = isBookmarkList ? "bookmarks" : "notes";

  if (notes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-xs">
        No {entityLabel} for this day yet.
      </p>
    );
  }

  return (
    <ul
      aria-label={`${entityLabel} for ${date}`}
      className="flex flex-col gap-sm"
    >
      {notes.map((note) => (
        <li
          key={note.id}
          className="flex flex-col gap-xs p-sm border border-border rounded-md bg-background"
        >
          {editingId === note.id ? (
            <NoteEditor
              date={date}
              editingNote={note}
              isBookmark={isBookmarkList}
              onSubmit={async (body, tags) => {
                await onUpdate(note.id, { date, body, tags });
                setEditingId(null);
              }}
              onCancel={() => setEditingId(null)}
            />
          ) : (
            <>
              <p className="text-sm text-foreground whitespace-pre-wrap">{note.body}</p>

              {note.tags.filter((t) => t !== "bookmark").length > 0 && (
                <ul aria-label="Tags" className="flex flex-wrap gap-xs">
                  {note.tags
                    .filter((t) => t !== "bookmark")
                    .map((tag) => (
                      <li key={tag} className="text-xs px-xs py-xs border border-border rounded-full text-muted-foreground">
                        {tag}
                      </li>
                    ))}
                </ul>
              )}

              {note._pending && (
                <span role="status" className="text-xs text-muted-foreground italic">
                  Saving…
                </span>
              )}

              <div className="flex gap-sm">
                <button
                  type="button"
                  aria-label={`Edit ${isBookmarkList ? "bookmark" : "note"}`}
                  onClick={() => setEditingId(note.id)}
                  className="text-xs text-primary"
                >
                  Edit
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${isBookmarkList ? "bookmark" : "note"}`}
                  onClick={() => void onDelete(note.id)}
                  className="text-xs text-destructive"
                >
                  Delete
                </button>
              </div>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}
