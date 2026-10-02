import React from "react";
import { cva } from "class-variance-authority";
import { cn } from "./cn";

const badge = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-4",
  {
    variants: {
      tone: {
        neutral: "border-border bg-ink-100 text-ink-700",
        brand: "border-brand-100 bg-brand-50 text-brand-700",
        success: "border-green-500/30 bg-success-bg text-success-fg",
        warning: "border-amber-500/30 bg-warning-bg text-warning-fg",
        danger: "border-red-500/30 bg-danger-bg text-danger-fg",
        info: "border-blue-500/30 bg-info-bg text-info-fg",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export const Badge = ({ tone, className, ...props }) => (
  <span className={cn(badge({ tone }), className)} {...props} />
);

const STATUS_TONE = {
  verified: "success",
  approved: "success",
  active: "success",
  pending: "warning",
  draft: "neutral",
  rejected: "danger",
  flagged: "danger",
};

/** Maps the canonical record statuses (Pending / Verified / Draft / Rejected) to a tone. Text is always shown. */
export const StatusPill = ({ status, className, children }) => {
  const key = String(status ?? "").toLowerCase();
  return (
    <Badge tone={STATUS_TONE[key] ?? "neutral"} className={className}>
      {children ?? status}
    </Badge>
  );
};
