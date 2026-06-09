import type { JSX } from "react";
import type { ReactNode } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface CardProps {
  media?: ReactNode;
  header?: ReactNode;
  body: ReactNode;
  footer?: ReactNode;
  interactive?: boolean;
  selected?: boolean;
  onActivate?: () => void;
  className?: string;
  "aria-label"?: string;
}

const BASE_CLASS = "rounded-lg border border-border bg-background shadow-sm p-md";

export function Card({
  media,
  header,
  body,
  footer,
  interactive = false,
  selected = false,
  onActivate,
  className = "",
  ...rest
}: CardProps): JSX.Element {
  const classes = `${BASE_CLASS} ${className}`.trim();
  const inner = (
    <>
      {media ? <div className="mb-sm">{media}</div> : null}
      {header ? <div className="mb-xs">{header}</div> : null}
      <div>{body}</div>
      {footer ? <div className="mt-sm">{footer}</div> : null}
    </>
  );

  if (interactive) {
    return (
      <button
        type="button"
        className={`${classes} text-left`}
        aria-pressed={selected}
        onClick={onActivate}
        aria-label={rest["aria-label"]}
      >
        {inner}
      </button>
    );
  }

  return (
    <div className={classes} aria-label={rest["aria-label"]}>
      {inner}
    </div>
  );
}
