import React from "react";
import { cn } from "./cn";

/** Selectable card group with radio semantics. options: [{ value, title, description, badge }] */
export const RadioCardGroup = ({ label, value, onChange, options, className }) => (
  <div role="radiogroup" aria-label={label} className={cn("grid gap-3 md:grid-cols-3", className)}>
    {options.map((opt) => {
      const selected = opt.value === value;
      return (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={selected}
          tabIndex={selected || (!value && opt === options[0]) ? 0 : -1}
          onClick={() => onChange(opt.value)}
          className={cn(
            "flex cursor-pointer flex-col gap-1 rounded-lg border bg-surface p-4 text-left transition-colors",
            selected ? "border-brand-500 bg-selected-bg" : "border-border hover:border-ink-300",
          )}
        >
          <span className="flex items-center justify-between gap-2">
            <span className="text-md font-semibold text-text">{opt.title}</span>
            {opt.badge}
          </span>
          {opt.description && <span className="text-sm text-text-secondary">{opt.description}</span>}
        </button>
      );
    })}
  </div>
);
