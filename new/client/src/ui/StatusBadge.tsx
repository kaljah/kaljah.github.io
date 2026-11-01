import React from "react";
import { CheckCircle2, Clock, AlertCircle, XCircle, AlertTriangle, HelpCircle } from "lucide-react";
import { Badge, type BadgeTone } from "./Badge";
import { cn } from "./cn";
import { t } from "../i18n";

export type WorkflowStatus =
  | "Draft"
  | "Pending review"
  | "Verified"
  | "Rejected"
  | "Flagged"
  | "Reconciled"
  | "Discrepancy";

export const WORKFLOW_STATUS_LIST: WorkflowStatus[] = [
  "Draft",
  "Pending review",
  "Verified",
  "Rejected",
  "Flagged",
  "Reconciled",
  "Discrepancy",
];

export const STATUS_CONFIG: Record<
  WorkflowStatus,
  {
    tone: BadgeTone;
    label: string;
    Icon: React.ComponentType<{ className?: string }>;
    description: string;
  }
> = {
  Draft: {
    tone: "neutral",
    label: t("Draft"),
    Icon: Clock,
    description: t("Draft record. Saved locally or in progress; not yet submitted for verification."),
  },
  "Pending review": {
    tone: "warning",
    label: t("Pending review"),
    Icon: Clock,
    description: t("Submitted for maker-checker review. Awaiting verification by an authorized checker."),
  },
  Verified: {
    tone: "success",
    label: t("Verified"),
    Icon: CheckCircle2,
    description: t("Formally verified and approved. Included in the official GHG accounting inventory."),
  },
  Rejected: {
    tone: "danger",
    label: t("Rejected"),
    Icon: XCircle,
    description: t("Rejected during review due to anomalies, missing documentation, or calculation errors."),
  },
  Flagged: {
    tone: "danger",
    label: t("Flagged"),
    Icon: AlertTriangle,
    description: t("Flagged by automated QA/QC diagnostic rules for anomalous or suspicious patterns."),
  },
  Reconciled: {
    tone: "success",
    label: t("Reconciled"),
    Icon: CheckCircle2,
    description: t("OGMP 2.0 Level 5 source-level and site-level measurements reconciled within tolerance."),
  },
  Discrepancy: {
    tone: "danger",
    label: t("Discrepancy"),
    Icon: AlertCircle,
    description: t("Discrepancy detected between bottom-up estimates and top-down measurements."),
  },
};

/** Normalizes various legacy database/API status strings to the canonical WorkflowStatus. */
export function normalizeWorkflowStatus(raw: unknown): WorkflowStatus {
  if (!raw) return "Draft";
  const norm = String(raw).trim().toLowerCase();
  if (norm === "verified" || norm === "approved" || norm === "active") return "Verified";
  if (
    norm === "pending review" ||
    norm === "pending" ||
    norm === "under review" ||
    norm === "investigation pending"
  )
    return "Pending review";
  if (norm === "rejected") return "Rejected";
  if (norm === "flagged") return "Flagged";
  if (norm === "reconciled") return "Reconciled";
  if (norm === "discrepancy" || norm === "discrepancy detected") return "Discrepancy";
  if (norm === "draft") return "Draft";
  return "Draft";
}

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: WorkflowStatus | string | null | undefined;
  showIcon?: boolean;
  size?: "sm" | "md";
}

/**
 * Shared StatusBadge component enforcing the single source of truth for workflow statuses.
 * Per rule C3, never relies on color alone: includes explicit text and status icon.
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  showIcon = true,
  size = "md",
  className,
  ...props
}) => {
  const canonical = normalizeWorkflowStatus(status);
  const cfg = STATUS_CONFIG[canonical] ?? STATUS_CONFIG.Draft;
  const Icon = cfg.Icon;

  return (
    <Badge
      tone={cfg.tone}
      title={cfg.description}
      className={cn(
        "gap-1.5 font-medium select-none inline-flex items-center",
        size === "sm" ? "text-[0.7rem] px-2 py-0.5" : "text-xs px-2.5 py-0.5",
        className,
      )}
      {...props}
    >
      {showIcon && <Icon className={cn(size === "sm" ? "size-3" : "size-3.5", "shrink-0")} aria-hidden="true" />}
      <span>{cfg.label}</span>
    </Badge>
  );
};

export interface FlagChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  label: string;
  severity?: "warning" | "danger" | "info";
}

/**
 * QA flag chip shown separately from workflow status.
 * Per A2: A record has one workflow status; QA flags are shown separately as a "Flag" chip.
 */
export const FlagChip: React.FC<FlagChipProps> = ({
  label,
  severity = "danger",
  className,
  ...props
}) => {
  const tone: BadgeTone = severity === "danger" ? "danger" : severity === "warning" ? "warning" : "info";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[0.7rem] font-semibold uppercase tracking-wider",
        tone === "danger"
          ? "bg-red-50 text-red-700 border border-red-500/30"
          : tone === "warning"
            ? "bg-amber-50 text-amber-700 border border-amber-500/30"
            : "bg-blue-50 text-blue-700 border border-blue-500/30",
        className,
      )}
      {...props}
    >
      <AlertTriangle className="size-3 shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
};

/** Page-level Data Health Badge derived from real data. */
export const DataHealthBadge: React.FC<{ cleanRatio: number; totalRecords?: number }> = ({
  cleanRatio,
  totalRecords = 0,
}) => {
  if (totalRecords === 0) {
    return (
      <Badge tone="neutral" className="gap-1.5 text-xs font-medium">
        <HelpCircle className="size-3.5" aria-hidden="true" />
        {t("Data Health: No records")}
      </Badge>
    );
  }
  const pct = Math.round(cleanRatio * 100);
  if (pct >= 98) {
    return (
      <Badge tone="success" className="gap-1.5 text-xs font-semibold">
        <CheckCircle2 className="size-3.5" aria-hidden="true" />
        {t("Data Health: Optimal ({{pct}}%)", { pct })}
      </Badge>
    );
  }
  if (pct >= 90) {
    return (
      <Badge tone="warning" className="gap-1.5 text-xs font-semibold">
        <AlertTriangle className="size-3.5" aria-hidden="true" />
        {t("Data Health: Attention ({{pct}}%)", { pct })}
      </Badge>
    );
  }
  return (
    <Badge tone="danger" className="gap-1.5 text-xs font-semibold">
      <AlertCircle className="size-3.5" aria-hidden="true" />
      {t("Data Health: Critical ({{pct}}%)", { pct })}
    </Badge>
  );
};

/** Page-level OGMP Level 5 status derived from real surveys data. */
export const OgmpL5Badge: React.FC<{ reconciledCount: number; discrepancyCount: number }> = ({
  reconciledCount,
  discrepancyCount,
}) => {
  if (reconciledCount === 0 && discrepancyCount === 0) {
    return (
      <Badge tone="neutral" className="gap-1.5 text-xs font-medium">
        {t("OGMP L5: Pending surveys")}
      </Badge>
    );
  }
  if (discrepancyCount > 0) {
    return (
      <Badge tone="danger" className="gap-1.5 text-xs font-semibold">
        <AlertCircle className="size-3.5" aria-hidden="true" />
        {t("OGMP L5: Discrepancies detected ({{count}})", { count: discrepancyCount })}
      </Badge>
    );
  }
  return (
    <Badge tone="success" className="gap-1.5 text-xs font-semibold">
      <CheckCircle2 className="size-3.5" aria-hidden="true" />
      {t("OGMP L5: Reconciled ({{count}})", { count: reconciledCount })}
    </Badge>
  );
};

/** Target tracking badge derived from actual emissions vs target. */
export const TargetTrackingBadge: React.FC<{ actual: number; target: number }> = ({
  actual,
  target,
}) => {
  if (!target || target <= 0) {
    return (
      <Badge tone="neutral" className="gap-1.5 text-xs font-medium">
        {t("Target not set")}
      </Badge>
    );
  }
  const onTrack = actual <= target;
  return onTrack ? (
    <Badge tone="success" className="gap-1.5 text-xs font-semibold">
      <CheckCircle2 className="size-3.5" aria-hidden="true" />
      {t("On track (≤ target)")}
    </Badge>
  ) : (
    <Badge tone="danger" className="gap-1.5 text-xs font-semibold">
      <AlertCircle className="size-3.5" aria-hidden="true" />
      {t("Over target")}
    </Badge>
  );
};
