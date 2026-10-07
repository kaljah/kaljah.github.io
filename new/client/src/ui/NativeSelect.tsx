import React from "react";
import { useFieldContext } from "./Field";

export interface NativeSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

/**
 * Native select with Field wiring. Props pass straight through, so existing call sites keep their
 * className, value, onChange and children. Inside a Field it takes id, aria-invalid and aria-describedby.
 * Use Select for the styled listbox; use this where a native control is preferable (long forms, mobile).
 */
export const NativeSelect = React.forwardRef<HTMLSelectElement, NativeSelectProps>(function NativeSelect(
  props,
  ref,
) {
  const field = useFieldContext();
  return (
    <select
      ref={ref}
      id={props.id ?? field?.id}
      aria-invalid={props["aria-invalid"] ?? (field?.invalid || undefined)}
      aria-describedby={props["aria-describedby"] ?? field?.describedBy}
      required={props.required ?? field?.required}
      {...props}
    />
  );
});
