"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface ShareBookmarkBarProps {
  date: string; // "YYYY-MM-DD" — used to construct share URL
  locationLabel: string;
  bookmarked: boolean;
  onBookmark: () => void;
}

export function ShareBookmarkBar({
  date,
  locationLabel,
  bookmarked,
  onBookmark,
}: ShareBookmarkBarProps): React.JSX.Element {
  async function handleShare(): Promise<void> {
    const url = `${window.location.origin}/today?date=${date}`;
    const text = `Panchang for ${locationLabel} — ${date}`;

    if (navigator.share) {
      try {
        await navigator.share({ title: "The Pandit — Daily Panchang", text, url });
      } catch {
        // User cancelled or share failed — fall through to clipboard
      }
      return;
    }

    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // noop — clipboard not available
    }
  }

  return (
    <div
      role="toolbar"
      aria-label="Page actions"
      className="flex items-center justify-end gap-sm px-md py-sm border-t border-border"
    >
      <button
        type="button"
        className="text-sm text-primary px-sm py-xs rounded-sm border border-border"
        onClick={() => void handleShare()}
        aria-label="Share today's Panchang"
      >
        Share
      </button>
      <button
        type="button"
        className="text-sm px-sm py-xs rounded-sm border border-border"
        onClick={onBookmark}
        aria-label={bookmarked ? "Remove bookmark" : "Bookmark this day"}
        aria-pressed={bookmarked}
      >
        {bookmarked ? "Bookmarked" : "Bookmark"}
      </button>
    </div>
  );
}
