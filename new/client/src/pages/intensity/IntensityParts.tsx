import React from "react";
import { Card } from "../../ui";
import { cn } from "../../ui/cn";

export type IntensityTone = "co2" | "scope1" | "flare" | "scope3" | "ch4";

const ICON_TONE: Record<IntensityTone, string> = {
  co2: "bg-brand-50 text-brand-700",
  scope1: "bg-info-bg text-info-fg",
  flare: "bg-brand-50 text-brand-600",
  scope3: "bg-ink-100 text-violet-700",
  ch4: "bg-info-bg text-info-fg",
};

const VALUE_TONE: Record<IntensityTone, string> = {
  co2: "text-text",
  scope1: "text-blue-600",
  flare: "text-brand-600",
  scope3: "text-violet-700",
  ch4: "text-blue-600",
};

export interface KpiTileProps {
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  tone?: IntensityTone;
  label: React.ReactNode;
  value: React.ReactNode;
  unit?: string;
  pending?: boolean;
  footer?: React.ReactNode;
  note?: React.ReactNode;
}

/** Headline metric tile: icon, label, big value with unit, footer facts. Used by Carbon and Methane Intensity. */
export const KpiTile: React.FC<KpiTileProps> = ({
  icon: Icon,
  tone = "co2",
  label,
  value,
  unit,
  pending = false,
  footer,
  note,
}) => (
  <div className="kpi-card rounded-lg border border-border bg-surface/70 p-6 shadow-card transition-shadow hover:shadow-md">
    <div className="mb-4 flex items-center gap-3">
      <span className={cn("flex size-[38px] shrink-0 items-center justify-center rounded-md", ICON_TONE[tone])}>
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <span className="kpi-label text-sm font-semibold uppercase tracking-wide text-text-secondary">{label}</span>
    </div>
    <div className="flex items-baseline gap-2">
      <span className={cn("total-value font-bold leading-none tracking-tight tabular-nums", pending ? "text-lg text-warning-fg" : cn("text-3xl", VALUE_TONE[tone]))}>{value}</span>
      {unit && !pending && <span className="kpi-unit text-base font-medium text-text-secondary">{unit}</span>}
    </div>
    <div className="kpi-footer mt-4 flex items-center justify-between gap-2 border-0 border-t border-dashed border-border pt-4 text-sm text-text-secondary [&_strong]:text-text">{footer}</div>
    {note}
  </div>
);

export interface ProdItemProps {
  label: React.ReactNode;
  value: React.ReactNode;
  accent?: string;
  bordered?: boolean;
}

/** One production figure in the context bar under the KPI tiles. */
export const ProdItem: React.FC<ProdItemProps> = ({ label, value, accent, bordered = true }) => (
  <div className={cn("scope-item flex flex-col gap-2", bordered && "md:border-l md:border-border md:pl-5")}>
    <span className="label text-sm font-semibold uppercase tracking-wide text-text-secondary">{label}</span>
    <span className={cn("val text-lg font-bold text-text", accent)}>{value}</span>
  </div>
);

export interface HeroPanelProps {
  title: React.ReactNode;
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode;
}

/** Hero panel with an accent rule on top: title row, KPI grid and production bar. */
export const HeroPanel: React.FC<HeroPanelProps> = ({ title, icon: Icon, badge, actions, children }) => (
  <Card className="hero-card relative overflow-hidden p-8 before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-gradient-to-r before:from-brand-500 before:via-blue-600 before:to-brand-600">
    <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5">
      <div className="flex flex-wrap items-center gap-4">
        <h2 className="grid-title m-0 flex items-center gap-3 text-xl font-bold tracking-tight text-text">
          <Icon className="size-6 text-brand-500" aria-hidden="true" /> {title}
        </h2>
        {badge}
      </div>
      {actions}
    </div>
    {children}
  </Card>
);

export const KpiGrid: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">{children}</div>
);

export const ProdBar: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div className="scope-breakdown mt-8 grid gap-5 rounded-md border border-border bg-ink-100 p-6 md:grid-cols-2 lg:grid-cols-4">{children}</div>
);

export interface ChartCardProps {
  title: React.ReactNode;
  rule?: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

/** Chart panel with a title and a short coloured rule; the colour matches the series. */
export const ChartCard: React.FC<ChartCardProps> = ({ title, rule, subtitle, actions, className, children }) => (
  <Card className={cn("flex flex-col gap-4", className)}>
    <div className="flex items-start justify-between gap-3">
      <div className="flex flex-col gap-2">
        <h3 className="m-0 text-lg font-semibold text-text">{title}</h3>
        {subtitle && <p className="m-0 text-sm text-text-secondary">{subtitle}</p>}
        {rule && <span className="h-1 w-8 rounded-sm" style={{ backgroundColor: rule }} aria-hidden="true" />}
      </div>
      {actions}
    </div>
    <div className="min-w-0 [&>div]:mb-0 [&>div]:border-0 [&>div]:p-0 [&>div]:shadow-none">{children}</div>
  </Card>
);

const HEAT: Record<string, string> = {
  null: "border border-dashed border-border bg-ink-100 text-text-secondary",
  lux: "bg-green-600 text-white",
  low: "bg-green-500 text-white",
  mid: "bg-amber-700 text-white",
  high: "bg-brand-600 text-white",
  crit: "bg-red-600 text-white",
};

// Intensity (kg CO2e/BOE) band used by the heatmap
const heatBand = (val?: number | null): string => {
  if (val === null || val === undefined || Number.isNaN(val) || val === 0) return "null";
  if (val < 18) return "lux";
  if (val < 28) return "low";
  if (val < 38) return "mid";
  if (val < 48) return "high";
  return "crit";
};

export interface HeatmapCell {
  key: string | number;
  value: number;
  title?: string;
}

export interface HeatmapRow {
  id: string | number;
  name: string;
  cells: HeatmapCell[];
}

export interface HeatmapProps {
  years: (string | number)[];
  rows: HeatmapRow[];
  empty?: string;
}

/** Facility x year grid coloured by intensity band. rows: [{ id, name, cells: [{ key, value, title }] }]. */
export const Heatmap: React.FC<HeatmapProps> = ({ years, rows, empty = "No regional data available" }) => {
  const cols = { gridTemplateColumns: `200px repeat(${years.length}, minmax(70px, 1fr))` };
  return (
    <div className="heatmap-container mt-6 overflow-x-auto rounded-md border border-border bg-ink-50 p-4">
      <div className="heatmap-header mb-4 grid gap-3 px-3" style={cols}>
        <div className="text-left text-sm font-bold uppercase tracking-wide text-text-secondary">FACILITY / REGION</div>
        {years.map((y) => (
          <div key={y} className="text-center text-sm font-bold uppercase tracking-wide text-text-secondary">
            {y}
          </div>
        ))}
      </div>
      {rows.length ? (
        rows.map((row) => (
          <div key={row.id} className="heatmap-row grid items-center gap-3 border-b border-border p-3 transition-colors last:border-b-0 hover:rounded-md hover:bg-surface hover:shadow-xs" style={cols}>
            <div className="text-base font-semibold text-text">{row.name}</div>
            {row.cells.map((c) => (
              <div key={c.key} title={c.title} className={cn("flex min-h-10 cursor-default items-center justify-center rounded-sm p-2.5 text-base font-semibold", HEAT[heatBand(c.value)])}>
                {c.value > 0 ? c.value.toFixed(2) : "-"}
              </div>
            ))}
          </div>
        ))
      ) : (
        <p className="p-10 text-center text-text-secondary">{empty}</p>
      )}
    </div>
  );
};
