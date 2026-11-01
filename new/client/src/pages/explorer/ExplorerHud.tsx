import React from "react";
import { Flame, TrendingUp } from "lucide-react";
import { SegmentedControl } from "../../ui";
import { cn } from "../../ui/cn";
import { t } from "../../i18n";

interface MetricProps {
  label: string;
  children: React.ReactNode;
  tone?: "accent" | "alert";
}

// One telemetry figure in the HUD strip: small caption over a tabular value.
const Metric: React.FC<MetricProps> = ({ label, children, tone }) => (
  <div className="flex flex-col items-center gap-px px-2.5 first:pl-0 last:pr-0 [&:not(:first-child)]:border-l [&:not(:first-child)]:border-border">
    <span className="whitespace-nowrap text-[0.68rem] font-medium text-text-secondary">{label}</span>
    <span className={cn("text-sm font-bold tabular-nums text-text", tone === "accent" && "text-brand-700", tone === "alert" && "text-danger-fg")}>
      {children}
    </span>
  </div>
);

const labelWithIcon = (Icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>, text: string) => (
  <span className="inline-flex items-center gap-1.5">
    <Icon className="size-3.5" aria-hidden="true" />
    {text}
  </span>
);

export interface ExplorerHudProps {
  metrics: {
    activeAssets?: number;
    totalMethane?: number;
    totalGhg?: number;
    avgMethaneIntensity?: string | number;
    superEmitters?: number;
    [key: string]: any;
  };
  viewMode: string;
  onViewMode: (mode: string) => void;
  formatCompact: (v: any) => string;
}

/** Floating telemetry bar on top of the map: title, regional KPIs and view mode. */
const ExplorerHud: React.FC<ExplorerHudProps> = ({
  metrics,
  viewMode,
  onViewMode,
  formatCompact,
}) => {
  const regional = viewMode === "methane" ? metrics.totalMethane : metrics.totalGhg;
  return (
    <header className="absolute inset-x-4 top-3.5 z-1000 flex items-center justify-between gap-3 rounded-lg border border-border bg-surface/95 px-4 py-2.5 shadow-md backdrop-blur-md">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <span className="relative flex size-3 items-center justify-center" aria-hidden="true">
            <span className="size-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20" />
          </span>
          {/* The top bar already names the page on small screens; keep the heading for screen readers. */}
          <div className="sr-only md:not-sr-only">
            <h1 className="m-0 whitespace-nowrap text-md font-bold text-text">{t("Emissions Map")}</h1>
            <p className="m-0 hidden whitespace-nowrap text-xs font-medium text-info-fg xl:block">{t("Reported inventory")}</p>
          </div>
        </div>
      </div>

      {/* Hidden below lg: the strip does not fit beside the title and the metric toggle. */}
      <div className="hidden items-center rounded-md border border-border bg-ink-50 px-3 py-1.5 lg:flex">
        <Metric label={t("Monitored assets")}>{metrics.activeAssets}</Metric>
        <Metric label={viewMode === "methane" ? t("Geolocated methane (On Map)") : t("Geolocated GHG (On Map)")} tone="accent">
          {formatCompact(regional)} t
        </Metric>
        <Metric label={t("Mean loss intensity")}>
          {metrics.avgMethaneIntensity} <span className="text-xs font-medium text-text-secondary">kg/boe</span>
        </Metric>
        <Metric label={t("Super-emitters")} tone={(metrics.superEmitters ?? 0) > 0 ? "alert" : undefined}>
          {metrics.superEmitters} of {metrics.activeAssets}
        </Metric>
      </div>

      <div className="flex items-center gap-2.5">
        <SegmentedControl
          label={t("Map metric")}
          size="sm"
          className="[&_button]:whitespace-nowrap"
          value={viewMode}
          onChange={onViewMode}
          options={[
            { value: "methane", label: labelWithIcon(Flame, t("CH₄ Flux")), title: t("Focus on Methane (CH4) emissions") },
            { value: "total", label: labelWithIcon(TrendingUp, t("Total GHG")), title: t("Focus on Total GHG (CO2e) emissions") },
          ]}
        />
      </div>
    </header>
  );
};

export default ExplorerHud;
