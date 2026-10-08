import React from "react";
import { Flame, Radio, Satellite, TrendingUp } from "lucide-react";
import { Badge, Button, SegmentedControl } from "../../ui";
import { cn } from "../../ui/cn";

interface MetricProps {
  label: string;
  children: React.ReactNode;
  tone?: "accent" | "alert";
}

// One telemetry figure in the HUD strip: small caption over a tabular value.
const Metric: React.FC<MetricProps> = ({ label, children, tone }) => (
  <div className="flex flex-col items-center gap-px px-2 first:pl-0 last:pr-0 [&:not(:first-child)]:border-l [&:not(:first-child)]:border-border">
    <span className="whitespace-nowrap text-[0.62rem] font-bold uppercase tracking-wide text-text-secondary">{label}</span>
    <span className={cn("text-md font-extrabold tabular-nums text-text", tone === "accent" && "text-brand-700", tone === "alert" && "text-danger-fg")}>
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
  connected: boolean;
  onConfigure: () => void;
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
  baseMaps: Record<string, { icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>; name: string }>;
  baseLayer: string;
  onBaseLayer: (layer: string) => void;
  formatCompact: (v: any) => string;
}

/** Floating telemetry bar on top of the map: title and stream status, regional KPIs, view mode and basemap. */
const ExplorerHud: React.FC<ExplorerHudProps> = ({
  connected,
  onConfigure,
  metrics,
  viewMode,
  onViewMode,
  baseMaps,
  baseLayer,
  onBaseLayer,
  formatCompact,
}) => {
  const regional = viewMode === "methane" ? metrics.totalMethane : metrics.totalGhg;
  return (
    <header className="absolute inset-x-4 top-3.5 z-1000 flex items-center justify-between gap-3 rounded-lg border border-border bg-surface/95 px-4 py-2.5 shadow-md backdrop-blur-md">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <span className="relative flex size-4 items-center justify-center" aria-hidden="true">
            <span className="size-2 rounded-full bg-brand-500" />
            <span className="absolute inset-0 animate-ping rounded-full border border-brand-500" />
          </span>
          {/* The top bar already names the page on small screens; keep the heading for screen readers. */}
          <div className="sr-only md:not-sr-only">
            <h1 className="m-0 whitespace-nowrap text-md font-bold text-text">Emissions Map</h1>
            <p className="m-0 hidden whitespace-nowrap text-xs font-semibold uppercase tracking-wide text-info-fg xl:block">Sentinel-5P TROPOMI</p>
          </div>
        </div>
        {connected ? (
          <Badge tone="success" title="Connected to Copernicus Data Space">
            <Radio className="size-3" aria-hidden="true" /> S5P stream live
          </Badge>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={onConfigure}
            title="Configure CDSE API credentials in Settings"
            aria-label="Configure S5P"
          >
            <Satellite className="size-3.5" aria-hidden="true" />
            <span className="hidden xl:inline">Configure S5P</span>
          </Button>
        )}
      </div>

      {/* Hidden below lg: the strip does not fit beside the title and the metric toggle. */}
      <div className="hidden items-center rounded-md border border-border bg-ink-50 px-3 py-1.5 lg:flex">
        <Metric label="Monitored assets">{metrics.activeAssets}</Metric>
        <Metric label={viewMode === "methane" ? "Regional methane" : "Regional GHG"} tone="accent">
          {formatCompact(regional)} t
        </Metric>
        <Metric label="Mean loss intensity">
          {metrics.avgMethaneIntensity} <span className="text-xs font-semibold text-text-secondary">kg/boe</span>
        </Metric>
        <Metric label="Super-emitters" tone={(metrics.superEmitters ?? 0) > 0 ? "alert" : undefined}>
          {metrics.superEmitters}
        </Metric>
      </div>

      <div className="flex items-center gap-2.5">
        <SegmentedControl
          label="Map metric"
          size="sm"
          className="[&_button]:whitespace-nowrap"
          value={viewMode}
          onChange={onViewMode}
          options={[
            { value: "methane", label: labelWithIcon(Flame, "CH₄ Flux"), title: "Focus on Methane (CH4) emissions" },
            { value: "total", label: labelWithIcon(TrendingUp, "Total GHG"), title: "Focus on Total GHG (CO2e) emissions" },
          ]}
        />
        {Object.keys(baseMaps).length > 1 && (
        <SegmentedControl
          label="Basemap"
          size="sm"
          className="[&_button]:whitespace-nowrap"
          value={baseLayer}
          onChange={onBaseLayer}
          options={Object.entries(baseMaps).map(([key, info]) => ({
            value: key,
            label: labelWithIcon(info.icon, info.name.split(" ")[0]),
            title: `Switch to ${info.name}`,
          }))}
        />
        )}
      </div>
    </header>
  );
};

export default ExplorerHud;
