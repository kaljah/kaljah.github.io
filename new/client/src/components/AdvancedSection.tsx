import React, { useState, useEffect } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../ui/cn";
import { t } from "../i18n";

export interface AdvancedSectionProps {
  id: string;
  title: string;
  fieldCount?: number;
  description?: string;
  defaultOpen?: boolean;
  className?: string;
  children: React.ReactNode;
}

export const AdvancedSection: React.FC<AdvancedSectionProps> = ({
  id,
  title,
  fieldCount,
  description,
  defaultOpen = false,
  className,
  children,
}) => {
  const storageKey = `ct.advanced.${id}`;
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored !== null) return stored === "1";
    } catch {
      // storage unavailable
    }
    return defaultOpen;
  });

  const toggle = () => {
    setIsOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(storageKey, next ? "1" : "0");
      } catch {
        // quiet fallback
      }
      return next;
    });
  };

  return (
    <div className={cn("rounded-lg border border-border bg-ink-50/50 transition-colors", isOpen && "bg-surface border-ink-200", className)}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls={`section-content-${id}`}
        className="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3 text-left border-0 bg-transparent rounded-lg hover:bg-ink-100/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <ChevronDown
            className={cn("size-4 shrink-0 text-text-secondary transition-transform duration-200", isOpen && "rotate-180")}
            aria-hidden="true"
          />
          <div className="min-w-0">
            <span className="text-sm font-semibold text-text">{title}</span>
            {description && (
              <p className="m-0 text-xs text-text-secondary truncate">{description}</p>
            )}
          </div>
        </div>
        {fieldCount != null && (
          <span className="rounded-full bg-ink-200/80 px-2 py-0.5 text-xs font-medium text-text-secondary shrink-0">
            {t("{{count}} fields", { count: fieldCount })}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          id={`section-content-${id}`}
          className="border-t border-border px-4 py-4 animate-in fade-in-50 duration-150"
        >
          {children}
        </div>
      )}
    </div>
  );
};

export default AdvancedSection;
