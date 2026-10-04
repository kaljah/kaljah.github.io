import React, { useRef } from "react";
import { cn } from "./cn";

/**
 * Selectable card group with radio semantics (arrow keys, roving tabindex).
 * options: [{ value, title, description, badge, content, id, selectedBadge }]. disabled makes it read-only.
 */
export const RadioCardGroup = ({ label, value, onChange, options, className, disabled = false, columns = "md:grid-cols-3" }) => {
  const refs = useRef([]);
  const move = (i, dir) => {
    const next = (i + dir + options.length) % options.length;
    if (disabled) return;
    onChange(options[next].value);
    refs.current[next]?.focus();
  };

  const onKeyDown = (e, i) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      move(i, 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      move(i, -1);
    }
  };

  const anySelected = options.some((o) => o.value === value);
  return (
    <div role="radiogroup" aria-label={label} className={cn("grid gap-3", columns, className)}>
      {options.map((opt, i) => {
        const selected = opt.value === value;
        return (
          <div
            key={opt.value}
            id={opt.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="radio"
            aria-checked={selected}
            aria-disabled={disabled || undefined}
            tabIndex={selected || (!anySelected && i === 0) ? 0 : -1}
            onClick={() => !disabled && onChange(opt.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                if (!disabled) onChange(opt.value);
              } else onKeyDown(e, i);
            }}
            className={cn(
              "flex flex-col gap-2 rounded-lg border bg-surface p-4 text-left transition-colors",
              disabled ? "cursor-default" : "cursor-pointer",
              selected ? "border-brand-500 bg-selected-bg" : "border-border hover:border-ink-300",
            )}
          >
            <span className="flex items-center justify-between gap-2">
              <span className="text-md font-semibold text-text">{opt.title}</span>
              {selected && opt.selectedBadge ? opt.selectedBadge : opt.badge}
            </span>
            {opt.description && <span className="text-sm text-ink-600">{opt.description}</span>}
            {opt.content}
          </div>
        );
      })}
    </div>
  );
};
