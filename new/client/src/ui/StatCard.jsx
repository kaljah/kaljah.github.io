import React from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card } from "./Card";
import { Num, Unit } from "./Num";
import { Skeleton } from "./Skeleton";
import { cn } from "./cn";

/** KPI tile. The value is neutral ink; only the delta is colored (green = good, red = bad). */
export const StatCard = ({
  label,
  sublabel,
  value,
  unit,
  format = "compact",
  decimals,
  delta,
  footnote,
  icon: Icon,
  loading = false,
  className,
  ...props
}) => {
  const good = delta ? (delta.goodWhen === "up" ? delta.value >= 0 : delta.value <= 0) : false;
  return (
    <Card className={cn("flex flex-col gap-2", className)} {...props}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-secondary">{label}</p>
          {sublabel && <p className="text-xs text-text-secondary">{sublabel}</p>}
        </div>
        {Icon && <Icon className="size-4 shrink-0 text-ink-400" aria-hidden="true" />}
      </div>
      {loading ? (
        <Skeleton className="h-9 w-32" />
      ) : (
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-2xl font-bold text-text">
            <Num value={value} format={format} decimals={decimals} />
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
      {footnote && <p className="text-sm text-text-secondary">{footnote}</p>}
    </Card>
  );
};
