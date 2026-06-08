import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

export type CtaVariant = "primary" | "secondary" | "ghost" | "destructive";
export type CtaSize = "sm" | "md" | "lg";

interface CtaOwnProps {
  label: ReactNode;
  icon?: ReactNode;
  variant?: CtaVariant;
  size?: CtaSize;
  loading?: boolean;
  className?: string;
}

type CtaProps =
  | ({ as?: "button" } & CtaOwnProps & ButtonHTMLAttributes<HTMLButtonElement>)
  | ({ as: "a" } & CtaOwnProps & AnchorHTMLAttributes<HTMLAnchorElement>);

const VARIANT_CLASS: Record<CtaVariant, string> = {
  primary: "bg-primary text-primary-foreground",
  secondary: "bg-secondary text-secondary-foreground",
  ghost: "bg-transparent text-foreground",
  destructive: "bg-destructive text-destructive-foreground",
};

const SIZE_CLASS: Record<CtaSize, string> = {
  sm: "text-sm px-sm py-xs",
  md: "text-base px-md py-sm",
  lg: "text-lg px-lg py-md",
};

const BASE_CLASS =
  "inline-flex items-center gap-sm rounded-md transition-colors duration-base disabled:opacity-50 disabled:pointer-events-none";

export function Cta(props: CtaProps): React.JSX.Element {
  const {
    as = "button",
    label,
    icon,
    variant = "primary",
    size = "md",
    loading = false,
    className = "",
    ...rest
  } = props;

  const classes = `${BASE_CLASS} ${VARIANT_CLASS[variant]} ${SIZE_CLASS[size]} ${className}`.trim();
  const content = (
    <>
      {icon}
      <span>{label}</span>
    </>
  );

  if (as === "a") {
    const anchorRest = rest as AnchorHTMLAttributes<HTMLAnchorElement>;
    return (
      <a className={classes} aria-busy={loading || undefined} {...anchorRest}>
        {content}
      </a>
    );
  }

  const buttonRest = rest as ButtonHTMLAttributes<HTMLButtonElement>;
  return (
    <button type="button" className={classes} aria-busy={loading || undefined} {...buttonRest}>
      {content}
    </button>
  );
}
