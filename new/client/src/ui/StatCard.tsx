import React from "react";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { Card, type CardProps } from "./Card";
import { Num, Unit } from "./Num";
import { Skeleton } from "./Skeleton";
import { HelpTip } from "./HelpTip";
import { cn } from "./cn";
import { t } from "../i18n";

const VALUE_TONES: Record<StatCardTone, string> = {
  default: "text-text",
  brand: "text-brand-700", // AA text contrast on white
  success: "text-green-700",
  warning: "text-amber-700",
  danger: "text-red-700",
  info: "text-blue-700",
  purple: "text-violet-700",
};

export type StatCardTone = "default" | "brand" | "success" | "warning" | "danger" | "info" | "purple";

export interface StatCardDelta {
  value: number;
  goodWhen?: "up" | "down";
  label?: string;
}

export interface KpiMeta {
  definition: string;
  formula?: string;
  filtersApplied?: string;
  gwpStandard?: string;
  lastUpdated?: string;
}

export interface StatCardProps extends Omit<CardProps, "children"> {
  label: React.ReactNode;
  sublabel?: React.ReactNode;
  value?: number | string | null;
  valueText?: React.ReactNode;
  unit?: string;
  format?: "compact" | "emission" | "number" | "percent";
  decimals?: number;
  delta?: StatCardDelta | null;
  footnote?: React.ReactNode;
  icon?: LucideIcon | React.ComponentType<{ className?: string }>;
  tone?: StatCardTone;
  loading?: boolean;
  info?: KpiMeta | React.ReactNode;
}

/** KPI tile. Defaults to neutral ink for value numbers (rule C3), with structured metadata tooltip (A1). */
export const StatCard: React.FC<StatCardProps> = ({
  label,
  sublabel,
  value,
  valueText,
  unit,
  format = "compact",
  decimals,
  delta,
  footnote,
  icon: Icon,
  tone = "default",
  loading = false,
  info,
  className,
  ...props
}) => {
  const good = delta ? (delta.goodWhen === "up" ? delta.value >= 0 : delta.value <= 0) : false;

  const renderInfoContent = () => {
    if (!info) return null;
    if (typeof info === "object" && "definition" in (info as any)) {
      const meta = info as KpiMeta;
      return (
        <div className="flex flex-col gap-2 p-1 text-xs">
          <div>
            <span className="font-semibold text-text">{t("Definition:")} </span>
            <span className="text-text-secondary">{meta.definition}</span>
          </div>
          {meta.formula && (
            <div>
              <span className="font-semibold text-text">{t("Formula:")} </span>
              <code className="rounded border border-border/60 bg-ink-100 px-1.5 py-0.5 font-mono text-[0.7rem] text-text break-words">
                {meta.formula}
              </code>
            </div>
          )}
          {meta.filtersApplied && (
            <div>
              <span className="font-semibold text-text">{t("Filters:")} </span>
              <span className="text-text-secondary">{meta.filtersApplied}</span>
            </div>
          )}
          {meta.gwpStandard && (
            <div>
              <span className="font-semibold text-text">{t("GWP Standard:")} </span>
              <span className="text-text-secondary">{meta.gwpStandard}</span>
            </div>
          )}
          {meta.lastUpdated && (
            <div className="border-t border-border pt-1 text-[0.7rem] text-text-secondary">
              {t("Last updated: {{time}}", { time: meta.lastUpdated })}
            </div>
          )}
        </div>
      );
    }
    return info as React.ReactNode;
  };

  return (
    <Card className={cn("flex flex-col gap-2", className)} {...props}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="stat-label text-xs font-medium text-text-secondary truncate">{label}</p>
            {info && (
              <HelpTip
                icon="info"
                content={renderInfoContent()}
                term={typeof label === "string" ? label : undefined}
                tooltipClassName="max-w-sm sm:max-w-md"
              />
            )}
          </div>
          {sublabel && <p className="text-xs text-text-secondary mt-0.5">{sublabel}</p>}
        </div>
        {Icon && <Icon className="size-4 shrink-0 text-ink-400" aria-hidden="true" />}
      </div>
      {loading ? (
        <Skeleton className="h-9 w-32" />
      ) : (
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span
            data-testid="kpi-value"
            className={cn("text-2xl font-bold", VALUE_TONES[tone] ?? "text-text")}
          >
            {valueText ?? <Num value={value} format={format} decimals={decimals} />}
          </span>
          {unit && <Unit className="text-sm">{unit}</Unit>}
          {delta && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 text-sm font-semibold",
                good ? "text-success-fg" : "text-danger-fg",
              )}
            >
              {delta.value >= 0 ? (
                <ArrowUpRight className="size-3.5" aria-hidden="true" />
              ) : (
                <ArrowDownRight className="size-3.5" aria-hidden="true" />
              )}
              <Num value={Math.abs(delta.value) * 100} format="percent" decimals={1} />
              {delta.label && <span className="ml-1 font-normal text-text-secondary">{delta.label}</span>}
            </span>
          )}
        </div>
      )}
      {footnote && (
        <p data-testid="kpi-footnote" className="text-sm text-text-secondary">
          {footnote}
        </p>
      )}
    </Card>
  );
};
