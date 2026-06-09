import type { JSX } from "react";
import type { ReactElement, ReactNode } from "react";
import { cloneElement } from "react";

// TODO(design): skin via Aqualeo design system. Structure, a11y, and token
// wiring are final — only className/visual treatment changes.

interface FormFieldProps {
  id: string;
  label: ReactNode;
  control: ReactElement<{
    id?: string | undefined;
    "aria-describedby"?: string | undefined;
    "aria-invalid"?: boolean | undefined;
  }>;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  invalid?: boolean;
  className?: string;
}

export function FormField({
  id,
  label,
  control,
  hint,
  error,
  required = false,
  invalid = false,
  className = "",
}: FormFieldProps): JSX.Element {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`flex flex-col gap-xs ${className}`.trim()}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
        {required ? <span aria-hidden="true"> *</span> : null}
      </label>
      {cloneElement(control, {
        id,
        "aria-describedby": describedBy,
        "aria-invalid": invalid || Boolean(error) || undefined,
      })}
      {hint ? (
        <p id={hintId} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
