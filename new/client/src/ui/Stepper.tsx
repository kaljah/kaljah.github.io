import React from "react";
import { Check } from "lucide-react";
import { cn } from "./cn";
import { t } from "../i18n";

export interface StepperProps {
  steps: string[];
  current: number;
  className?: string;
}

/** Wizard progress header. steps: string[]; current: zero-based index. */
export const Stepper: React.FC<StepperProps> = ({ steps, current, className }) => (
  <ol aria-label={t("Progress")} className={cn("m-0 flex list-none items-center gap-2 p-0", className)}>
    {steps.map((label, i) => {
      const done = i < current;
      const active = i === current;
      return (
        <li key={label} aria-current={active ? "step" : undefined} className="flex items-center gap-2">
          <span
            className={cn(
              "flex size-6 items-center justify-center rounded-full text-xs font-bold",
              done && "bg-primary text-on-primary",
              active && "border-2 border-brand-500 text-brand-700",
              !done && !active && "border border-border text-text-secondary",
            )}
          >
            {done ? <Check className="size-3.5" aria-hidden="true" /> : i + 1}
          </span>
          <span className={cn("text-sm", active ? "font-semibold text-text" : "text-text-secondary")}>{label}</span>
          {i < steps.length - 1 && <span aria-hidden="true" className="mx-1 h-px w-6 bg-border" />}
        </li>
      );
    })}
  </ol>
);
