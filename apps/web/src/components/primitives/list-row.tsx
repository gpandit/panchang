import type { ReactNode } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface ListRowProps {
  leading?: ReactNode;
  primary: ReactNode;
  secondary?: ReactNode;
  trailing?: ReactNode;
  interactive?: boolean;
  selected?: boolean;
  onActivate?: () => void;
  className?: string;
}

const BASE_CLASS = "flex items-center gap-md px-md py-sm border-b border-border";

export function ListRow({
  leading,
  primary,
  secondary,
  trailing,
  interactive = false,
  selected = false,
  onActivate,
  className = "",
}: ListRowProps): React.JSX.Element {
  const content = (
    <>
      {leading ? <div>{leading}</div> : null}
      <div className="flex-1">
        <div>{primary}</div>
        {secondary ? <div className="text-sm text-muted-foreground">{secondary}</div> : null}
      </div>
      {trailing ? <div>{trailing}</div> : null}
    </>
  );

  if (interactive) {
    return (
      <li>
        <button
          type="button"
          className={`${BASE_CLASS} w-full text-left ${className}`.trim()}
          aria-pressed={selected}
          onClick={onActivate}
        >
          {content}
        </button>
      </li>
    );
  }

  return <li className={`${BASE_CLASS} ${className}`.trim()}>{content}</li>;
}
