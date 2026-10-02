import React, { useRef } from "react";
import { cn } from "./cn";

/** Single-choice toggle group (role=radiogroup) with arrow-key navigation and roving tabindex. */
export const SegmentedControl = ({ label, value, onChange, options, className, size = "md" }) => {
  const refs = useRef([]);

  const move = (index, dir) => {
    const next = (index + dir + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  };

  const onKeyDown = (e, index) => {
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
            key={opt.value}
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
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
};
