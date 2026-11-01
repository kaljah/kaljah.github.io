import React from "react";
import { Send, UserCheck, ShieldCheck, Database, ArrowRight } from "lucide-react";
import { t } from "../i18n";
import { cn } from "../ui";

export interface WorkflowExplainerProps {
  className?: string;
  currentStep?: "submit" | "review" | "verified" | "included";
}

/**
 * Compact workflow explainer:
 * Submit -> Review (maker-checker) -> Verified -> Included in inventory
 * Rendered on Calculations and Pending Review.
 */
export const WorkflowExplainer: React.FC<WorkflowExplainerProps> = ({
  className,
  currentStep,
}) => {
  const steps = [
    {
      id: "submit",
      title: t("1. Submit"),
      subtitle: t("Operator logs raw activity"),
      Icon: Send,
    },
    {
      id: "review",
      title: t("2. Review"),
      subtitle: t("Dual-control maker-checker"),
      Icon: UserCheck,
    },
    {
      id: "verified",
      title: t("3. Verified"),
      subtitle: t("Approved & locked"),
      Icon: ShieldCheck,
    },
    {
      id: "included",
      title: t("4. Included"),
      subtitle: t("Counts in official inventory"),
      Icon: Database,
    },
  ];

  return (
    <div
      aria-label={t("GHG inventory verification workflow")}
      className={cn(
        "rounded-lg border border-border bg-ink-50/70 p-3 text-xs shadow-xs",
        className,
      )}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-semibold text-text uppercase tracking-wider text-[0.7rem] text-text-secondary">
          {t("MRV Assurance Pathway:")}
        </span>
        <div className="flex flex-1 flex-wrap items-center justify-between gap-1 sm:justify-end">
          {steps.map((step, idx) => {
            const isCurrent = currentStep === step.id;
            const Icon = step.Icon;
            return (
              <React.Fragment key={step.id}>
                <div
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors",
                    isCurrent
                      ? "bg-brand-50 border border-brand-500/40 text-brand-700 font-semibold"
                      : "bg-surface/80 text-text-secondary border border-border/40",
                  )}
                >
                  <Icon className={cn("size-3.5 shrink-0", isCurrent ? "text-brand-600" : "text-ink-400")} aria-hidden="true" />
                  <div className="flex flex-col">
                    <span className="font-medium text-text leading-tight">{step.title}</span>
                    <span className="text-[0.65rem] text-text-secondary leading-tight hidden md:inline">
                      {step.subtitle}
                    </span>
                  </div>
                </div>
                {idx < steps.length - 1 && (
                  <ArrowRight className="size-3 text-ink-300 shrink-0 mx-0.5" aria-hidden="true" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
