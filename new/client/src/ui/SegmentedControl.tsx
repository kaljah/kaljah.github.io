import React, { useRef } from "react";
import { cn } from "./cn";

export interface SegmentedControlOption<T = string> {
  value: T;
  label: React.ReactNode;
  title?: string;
  className?: string;
}

export interface SegmentedControlProps<T = string> {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: SegmentedControlOption<T>[];
  className?: string;
  size?: "sm" | "md";
}

/** Single-choice toggle group (role=radiogroup) with arrow-key navigation and roving tabindex. */
export const SegmentedControl = <T extends string | number>({
  label,
  value,
  onChange,
  options,
  className,
  size = "md",
}: SegmentedControlProps<T>): React.ReactElement => {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const move = (index: number, dir: number) => {
    const next = (index + dir + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      move(index, 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      move(index, -1);
    }
  };

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("inline-flex rounded-md border border-border bg-ink-100 p-0.5", className)}
    >
      {options.map((opt, i) => {
        const selected = opt.value === value;
        return (
          <button
            key={String(opt.value)}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            title={opt.title}
            onClick={() => onChange(opt.value)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={cn(
              "cursor-pointer rounded-sm border-0 bg-transparent font-semibold transition-colors",
              size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm",
              selected ? "bg-surface text-selected-fg shadow-xs" : "text-ink-600 hover:text-text",
              selected && "active",
              opt.className,
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
};
