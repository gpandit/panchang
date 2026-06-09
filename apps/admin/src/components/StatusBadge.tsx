import React from "react";
import { tokens } from "@/tokens";
import type { ContentStatus, FlagStatus } from "@/api/client";

const STATUS_COLOR: Record<ContentStatus | FlagStatus, string> = {
  draft:      tokens.color.statusDraft,
  review:     tokens.color.statusReview,
  published:  tokens.color.statusPublished,
  rejected:   tokens.color.statusRejected,
  open:       tokens.color.flagOpen,
  in_review:  tokens.color.statusReview,
  resolved:   tokens.color.flagResolved,
  dismissed:  tokens.color.flagDismissed,
};

interface Props {
  status: ContentStatus | FlagStatus;
}

export function StatusBadge({ status }: Props) {
  const color = STATUS_COLOR[status] ?? tokens.color.textMuted;
  return (
    <span
      style={{
        display: "inline-block",
        padding: `${tokens.space.xs} ${tokens.space.sm}`,
        borderRadius: tokens.radius.sm,
        fontSize: tokens.font.sizeSm,
        fontWeight: tokens.font.weightMedium,
        background: color,
        color: tokens.color.primaryText,
        textTransform: "capitalize",
      }}
    >
      {status.replace("_", " ")}
    </span>
  );
}
