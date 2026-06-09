"use client";

import type { JSX } from "react";
// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import { useState, useId } from "react";
import type { ReminderInput } from "./api";

const ADVANCE_OPTIONS: { label: string; value: number }[] = [
  { label: "At time of event", value: 0 },
  { label: "5 minutes before", value: 5 },
  { label: "15 minutes before", value: 15 },
  { label: "30 minutes before", value: 30 },
  { label: "1 hour before", value: 60 },
  { label: "1 day before", value: 24 * 60 },
];

interface ReminderFormProps {
  /** The Gregorian date this reminder is anchored to ("YYYY-MM-DD"). */
  date: string;
  onSubmit: (reminderIn: ReminderInput) => Promise<void>;
  onCancel?: () => void;
}

export function ReminderForm({ date, onSubmit, onCancel }: ReminderFormProps): JSX.Element {
  const titleId = useId();
  const advanceId = useId();

  const [title, setTitle] = useState("");
  const [advanceMinutes, setAdvanceMinutes] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        trigger_type: "gregorian",
        trigger_value: date,
        advance_minutes: advanceMinutes,
      });
      setTitle("");
      setAdvanceMinutes(0);
    } catch {
      setError("Failed to create reminder. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      aria-label={`Add reminder for ${date}`}
      onSubmit={(e) => void handleSubmit(e)}
      className="flex flex-col gap-sm"
      noValidate
    >
      <div className="flex flex-col gap-xs">
        <label htmlFor={titleId} className="text-sm font-medium text-foreground">
          Reminder title
          <span aria-hidden="true"> *</span>
        </label>
        <input
          id={titleId}
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-required="true"
          aria-describedby={error ? `${titleId}-error` : undefined}
          placeholder="e.g. Morning puja"
          className="text-sm px-sm py-xs border border-border rounded-md bg-background text-foreground"
        />
        {error && (
          <p id={`${titleId}-error`} role="alert" className="text-xs text-destructive">
            {error}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-xs">
        <label htmlFor={advanceId} className="text-sm text-foreground">
          Notify me
        </label>
        <select
          id={advanceId}
          value={advanceMinutes}
          onChange={(e) => setAdvanceMinutes(Number(e.target.value))}
          className="text-sm px-sm py-xs border border-border rounded-md bg-background text-foreground"
        >
          {ADVANCE_OPTIONS.map(({ label, value }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Anchored date (read-only, shown for user confirmation) */}
      <p className="text-xs text-muted-foreground">
        Anchored to: <time dateTime={date}>{date}</time> (Gregorian)
      </p>

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
          {submitting ? "Saving…" : "Add reminder"}
        </button>
      </div>
    </form>
  );
}
