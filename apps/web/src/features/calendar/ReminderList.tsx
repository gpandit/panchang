"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

import type { LocalReminder } from "./types";

interface ReminderListProps {
  reminders: LocalReminder[];
  date: string;
  onDelete: (id: string) => Promise<void>;
}

export function ReminderList({ reminders, date, onDelete }: ReminderListProps): React.JSX.Element {
  if (reminders.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-xs">
        No reminders for this day yet.
      </p>
    );
  }

  return (
    <ul aria-label={`Reminders for ${date}`} className="flex flex-col gap-sm">
      {reminders.map((reminder) => (
        <li
          key={reminder.id}
          className="flex items-center justify-between gap-sm p-sm border border-border rounded-md bg-background"
        >
          <div className="flex flex-col gap-xs min-w-0">
            <span className="text-sm text-foreground font-medium truncate">{reminder.title}</span>

            <span className="text-xs text-muted-foreground">
              {reminder.advance_minutes === 0
                ? "At time of event"
                : `${reminder.advance_minutes} min before`}
              {" · "}
              <time dateTime={reminder.trigger_value}>{reminder.trigger_value}</time>
            </span>

            {reminder._pending && (
              <span role="status" className="text-xs text-muted-foreground italic">
                Saving…
              </span>
            )}
          </div>

          <button
            type="button"
            aria-label={`Delete reminder: ${reminder.title}`}
            onClick={() => void onDelete(reminder.id)}
            className="text-xs text-destructive flex-shrink-0"
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
