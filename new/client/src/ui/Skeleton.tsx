import React from "react";
import { cn } from "./cn";
import { t } from "../i18n";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export const Skeleton: React.FC<SkeletonProps> = ({ className, ...props }) => (
  <div aria-hidden="true" className={cn("animate-pulse rounded-sm bg-ink-200", className)} {...props} />
);

/** Page-level loading placeholder: header plus a row of cards. */
export const PageSkeleton: React.FC = () => (
  <div role="status" aria-label={t("Loading")} className="flex flex-col gap-6 p-4 sm:p-6">
    <Skeleton className="h-8 w-64" />
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-28 rounded-lg" />
      ))}
    </div>
    <Skeleton className="h-72 rounded-lg" />
  </div>
);

export interface TableSkeletonProps {
  rows?: number;
  cols?: number;
  className?: string;
}

/** Animated skeleton placeholder for tabular grids during fetch. */
export const TableSkeleton: React.FC<TableSkeletonProps> = ({ rows = 6, cols = 5, className }) => (
  <div role="status" aria-label={t("Loading table data")} className={cn("w-full overflow-hidden rounded-md border border-border bg-surface", className)}>
    <div className="flex items-center gap-4 border-b border-border bg-ink-50 px-4 py-3">
      {Array.from({ length: cols }).map((_, c) => (
        <Skeleton key={c} className="h-4 flex-1 rounded-sm" />
      ))}
    </div>
    <div className="divide-y divide-border/60">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 px-4 py-3.5">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cn("h-4 rounded-sm", c === 0 ? "w-1/3" : "flex-1")} />
          ))}
        </div>
      ))}
    </div>
  </div>
);

export interface ChartSkeletonProps {
  height?: number | string;
  className?: string;
}

/** Animated skeleton placeholder for analytics and benchmark charts. */
export const ChartSkeleton: React.FC<ChartSkeletonProps> = ({ height = 300, className }) => (
  <div
    role="status"
    aria-label={t("Loading chart")}
    className={cn("flex flex-col gap-4 rounded-lg border border-border bg-surface p-5", className)}
    style={{ height: typeof height === "number" ? `${height}px` : height }}
  >
    <div className="flex items-center justify-between">
      <Skeleton className="h-5 w-48 rounded-sm" />
      <Skeleton className="h-4 w-24 rounded-sm" />
    </div>
    <div className="flex flex-1 items-end gap-3 pt-6 pb-2">
      {[40, 75, 55, 90, 65, 80, 45, 70].map((h, i) => (
        <div key={i} className="flex flex-1 flex-col items-center gap-2 h-full justify-end">
          <Skeleton className="w-full rounded-t-sm" style={{ height: `${h}%` }} />
          <Skeleton className="h-3 w-8 rounded-xs" />
        </div>
      ))}
    </div>
  </div>
);
