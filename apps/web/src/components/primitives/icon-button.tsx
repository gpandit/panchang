import type { ButtonHTMLAttributes, ReactNode } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface IconButtonOwnProps {
  icon: ReactNode;
  label?: ReactNode;
  variant?: "default" | "ghost";
  pressed?: boolean;
  className?: string;
}

type IconButtonProps = IconButtonOwnProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> &
  ({ "aria-label": string } | { label: ReactNode });

const VARIANT_CLASS: Record<"default" | "ghost", string> = {
  default: "bg-muted text-muted-foreground",
  ghost: "bg-transparent text-foreground",
};

export function IconButton(props: IconButtonProps): React.JSX.Element {
  const { icon, label, variant = "default", pressed, className = "", ...rest } = props;
  const classes =
    `inline-flex items-center justify-center gap-xs rounded-md p-sm transition-colors duration-base ${VARIANT_CLASS[variant]} ${className}`.trim();

  return (
    <button type="button" className={classes} aria-pressed={pressed} {...rest}>
      {icon}
      {label ? <span>{label}</span> : null}
    </button>
  );
}
