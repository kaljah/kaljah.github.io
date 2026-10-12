import React from "react";
import { useFieldContext } from "./Field";
import { cn } from "./cn";

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
    <div className="relative w-full">
      <select
        ref={ref}
        id={props.id ?? field?.id}
        aria-invalid={props["aria-invalid"] ?? (field?.invalid || undefined)}
        aria-describedby={props["aria-describedby"] ?? field?.describedBy}
        required={props.required ?? field?.required}
        {...props}
        style={{ backgroundImage: "none", ...props.style }}
        className={cn(
          "w-full appearance-none bg-[var(--bg-card,#ffffff)] text-[var(--text-primary,#0f172a)] border border-[var(--border-color,#e2e8f0)] rounded-[var(--radius-md,8px)] px-3.5 py-2.5 text-sm font-normal min-h-[42px] transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[var(--accent-color,#0284c7)] focus:border-transparent cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 pr-10",
          props.className
        )}
      />
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-[var(--text-secondary,#64748b)]">
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
});
