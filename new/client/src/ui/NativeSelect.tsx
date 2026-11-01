import React from "react";
import { useFieldContext } from "./Field";
import { cn } from "./cn";

export interface NativeSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  wrapperClassName?: string;
}

/**
 * Native select with Field wiring. Props pass straight through, so existing call sites keep their
 * className, value, onChange and children. Inside a Field it takes id, aria-invalid and aria-describedby.
 * Use Select for the styled listbox; use this where a native control is preferable (long forms, mobile).
 */
export const NativeSelect = React.forwardRef<HTMLSelectElement, NativeSelectProps>(function NativeSelect(
  props,
  ref,
) {
  const { wrapperClassName, className, ...rest } = props;
  const field = useFieldContext();
  const widthClassMatches = className?.match(/\b(?:(?:sm|md|lg|xl):)?w-(?:auto|fit|max|min|\d+|\[[^\]]+\])!?(?=\s|$)/g);
  const detectedWidthClass = widthClassMatches
    ? widthClassMatches.map((cls) => cls.replace(/!$/, "")).join(" ")
    : null;
  const isAuto = className?.includes("w-auto") || className?.includes("w-fit");

  const defaultWrapperClass = detectedWidthClass
    ? cn(detectedWidthClass, "shrink-0 inline-block")
    : isAuto
    ? "w-auto shrink-0 inline-block"
    : "w-full";

  return (
    <div
      className={cn(
        "relative",
        wrapperClassName ? wrapperClassName : defaultWrapperClass
      )}
    >
      <select
        ref={ref}
        id={props.id ?? field?.id}
        aria-invalid={props["aria-invalid"] ?? (field?.invalid || undefined)}
        aria-describedby={props["aria-describedby"] ?? field?.describedBy}
        required={props.required ?? field?.required}
        {...rest}
        style={{ backgroundImage: "none", ...props.style }}
        className={cn(
          "w-full appearance-none bg-[var(--bg-card,#ffffff)] text-[var(--text-primary,#0f172a)] border border-[var(--border-color,#e2e8f0)] rounded-[var(--radius-md,8px)] px-3.5 py-2 text-sm font-normal min-h-[40px] h-10 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[var(--accent-color,#0284c7)] focus:border-transparent cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 pr-9",
          className
        )}
      />
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2.5 text-[var(--text-secondary,#64748b)]">
        <span className="ui-select-chevron" aria-hidden="true" />
      </div>
    </div>
  );
});
