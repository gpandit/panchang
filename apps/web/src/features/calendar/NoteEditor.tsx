"use client";

import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useState, useId } from "react";
import type { LocalNote } from "./types";

interface NoteEditorProps {
  date: string; // "YYYY-MM-DD" — the anchor date
  /** If provided, the form is in edit mode pre-filled with this note. */
  editingNote?: LocalNote;
  onSubmit: (body: string, tags: string[]) => Promise<void>;
  onCancel?: () => void;
  /** When true, tags will include "bookmark"; form label reflects this. */
  isBookmark?: boolean;
}

export function NoteEditor({
  date,
  editingNote,
  onSubmit,
  onCancel,
  isBookmark = false,
}: NoteEditorProps): JSX.Element {
  const labelId = useId();
  const bodyId = useId();

  const [body, setBody] = useState(editingNote?.body ?? "");
  const [tagInput, setTagInput] = useState(
    (editingNote?.tags ?? []).filter((t) => t !== "bookmark").join(", "),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEditing = !!editingNote;
  const entityLabel = isBookmark ? "bookmark" : "note";
  const formLabel = isEditing
    ? `Edit ${entityLabel} for ${date}`
    : `Add ${entityLabel} for ${date}`;

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!body.trim()) {
      setError("Body is required.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const extraTags = tagInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const tags = isBookmark ? ["bookmark", ...extraTags] : extraTags;
      await onSubmit(body.trim(), tags);
      if (!isEditing) {
        setBody("");
        setTagInput("");
      }
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      aria-label={formLabel}
      onSubmit={(e) => void handleSubmit(e)}
      className="flex flex-col gap-sm"
      noValidate
    >
      <div className="flex flex-col gap-xs">
        <label id={labelId} htmlFor={bodyId} className="text-sm font-medium text-foreground">
          {isBookmark ? "Bookmark note" : "Note"}
          <span aria-hidden="true"> *</span>
        </label>
        <textarea
          id={bodyId}
          aria-labelledby={labelId}
          aria-required="true"
          aria-describedby={error ? `${bodyId}-error` : undefined}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
          placeholder={`Add a ${entityLabel}…`}
          className="w-full text-sm px-sm py-xs border border-border rounded-md bg-background text-foreground resize-y"
        />
        {error && (
          <p id={`${bodyId}-error`} role="alert" className="text-xs text-destructive">
            {error}
          </p>
        )}
      </div>

      {!isBookmark && (
        <div className="flex flex-col gap-xs">
          <label htmlFor={`${bodyId}-tags`} className="text-xs text-muted-foreground">
            Tags (comma-separated, optional)
          </label>
          <input
            id={`${bodyId}-tags`}
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="e.g. pooja, travel"
            className="text-sm px-sm py-xs border border-border rounded-md bg-background text-foreground"
          />
        </div>
      )}

      <div className="flex gap-sm justify-end">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="text-sm text-muted-foreground"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={submitting}
          aria-disabled={submitting}
          className="text-sm text-primary font-medium"
        >
          {submitting ? "Saving…" : isEditing ? "Save changes" : `Add ${entityLabel}`}
        </button>
      </div>
    </form>
  );
}
