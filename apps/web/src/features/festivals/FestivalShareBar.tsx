"use client";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface FestivalShareBarProps {
  festivalId: string;
  festivalName: string;
}

export function FestivalShareBar({
  festivalId,
  festivalName,
}: FestivalShareBarProps): React.JSX.Element {
  async function handleShare(): Promise<void> {
    const url = `${window.location.origin}/festivals/${encodeURIComponent(festivalId)}`;
    const text = `${festivalName} — The Pandit`;

    if (navigator.share) {
      try {
        await navigator.share({ title: text, text, url });
      } catch {
        // User cancelled or share API failed — fall back to clipboard
      }
      return;
    }

    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // noop
    }
  }

  return (
    <div
      role="toolbar"
      aria-label="Festival page actions"
      className="flex items-center justify-end gap-sm px-md py-sm border-t border-border"
    >
      <button
        type="button"
        className="text-sm text-primary px-sm py-xs rounded-sm border border-border"
        onClick={() => void handleShare()}
        aria-label={`Share ${festivalName}`}
      >
        Share
      </button>
    </div>
  );
}
