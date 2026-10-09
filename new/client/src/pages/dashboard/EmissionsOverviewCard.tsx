import React from "react";
import { Printer } from "lucide-react";
import { Badge, Button, Card, StatCard } from "../../ui";
import { formatCompactNumber } from "../../utils/formatters";

// "+5.2%" / "-3.1%" / "—" (from the parent) to a signed fraction, or null when there is no comparison
const toDelta = (text?: string): number | null => {
  if (!text || text === "—") return null;
  const n = parseFloat(text);
  return Number.isFinite(n) ? n / 100 : null;
};

export interface EmissionsOverviewCardProps {
  currentActivity: string;
  currentDivision: string;
  currentRegion: string;
  currentYear: string | number;
  exportingPDF?: boolean;
  facilities: { id: string | number; name: string; [key: string]: any }[];
  goal?: { target_amount: number; [key: string]: any } | null;
  handleExportPDF: () => void;
  hasProductionData: boolean;
  intensity: number | string;
  stats: {
    totalEmissions: number;
    netEmissions: number;
    methaneEmissions: number;
    mitigation: number;
    scope1: number;
    scope2: number;
    scope3: number;
    [key: string]: any;
  };
  variance: {
    emissions?: string;
    intensity?: string;
    [key: string]: any;
  };
}

// Emissions overview: four KPI tiles (values neutral, only the change is colored) and the scope breakdown.
const EmissionsOverviewCard: React.FC<EmissionsOverviewCardProps> = ({
  currentActivity,
  currentDivision,
  currentRegion,
  currentYear,
  exportingPDF,
  facilities,
  goal,
  handleExportPDF,
  hasProductionData,
  intensity,
  stats,
  variance,
}) => {
  const location =
    currentRegion !== "all"
      ? facilities.find((f) => f.id.toString() === currentRegion)?.name || "Region"
      : currentDivision !== "all"
        ? currentDivision
        : currentActivity !== "all"
          ? currentActivity
          : "All Regions";
  const compare = currentYear !== "all";
  const emissionsDelta = compare ? toDelta(variance.emissions) : null;
  const intensityDelta = compare && hasProductionData ? toDelta(variance.intensity) : null;
  const goalShare = goal && goal.target_amount > 0 ? (stats.totalEmissions / goal.target_amount) * 100 : null;
  const intensityPending = !hasProductionData && stats.totalEmissions > 0;

  return (
    <Card as="section" className="hero-card flex flex-col gap-5" aria-label="Emissions overview">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold uppercase tracking-wide text-text">Emissions Overview</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand">{location}</Badge>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportPDF}
            loading={exportingPDF}
            title="Export multi-page executive summary PDF"
          >
            <Printer className="size-4" aria-hidden="true" />
            {exportingPDF ? "Generating PDF..." : "Export Executive Brief (PDF)"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          className="p-4"
          data-testid="kpi-gross"
          tone="brand"
          label="Gross Operational Emissions"
          sublabel="Scope 1+2"
          value={stats.totalEmissions}
          unit="tCO2e"
          delta={emissionsDelta === null ? undefined : { value: emissionsDelta, goodWhen: "down", label: "vs prior year" }}
          footnote={goalShare === null ? undefined : `${goalShare.toFixed(1)}% of target`}
        />
        <StatCard
          className="p-4"
          data-testid="kpi-net"
          tone="success"
          label="Gross less mitigation"
          sublabel="Indicative, not the inventory total"
          value={stats.netEmissions}
          unit="tCO2e"
          footnote={`Less ${formatCompactNumber(stats.mitigation)} reported mitigation. Inventory totals stay gross (GHG Protocol, ISO 14064-1).`}
        />
        <StatCard
          className="p-4"
          data-testid="kpi-ch4"
          tone="warning"
          label="Total CH4 (Methane)"
          value={stats.methaneEmissions}
          unit="tCH4"
        />
        <StatCard
          className="p-4"
          data-testid="kpi-intensity"
          tone={intensityPending ? "warning" : "purple"}
          label="Performance Intensity"
          sublabel="CO2e intensity (Scope 1+2)"
          value={intensity}
          valueText={intensityPending ? "Pending" : undefined}
          format="compact"
          decimals={2}
          unit={intensityPending ? "Production" : "kg/BOE"}
          delta={intensityDelta === null ? undefined : { value: intensityDelta, goodWhen: "down", label: "vs prior year" }}
          footnote={intensityPending ? "Production figures required" : undefined}
        />
      </div>

      <div className="[display:flex]! [gap:16px]! [background:rgba(255,_255,_255,_0.4)] [padding:16px] [border-radius:var(--radius-lg)] [border:1px_solid_rgba(226,_232,_240,_0.5)] [@media(max-width:768px)]:[flex-direction:column] [@media(max-width:768px)]:[gap:10px]! [@media(max-width:480px)]:[display:grid]! [@media(max-width:480px)]:[grid-template-columns:1fr] [@media(max-width:480px)]:[width:100%]">
        <div className="scope-pill [flex:1] [display:flex] [justify-content:space-between] [align-items:center] [padding:10px_16px] [border-radius:var(--radius-md)] [font-size:var(--text-base)] [font-weight:600] [&.scope-1]:[background:var(--color-brand-50)] [&.scope-1]:[color:var(--color-brand-700)] [&&]:[&.scope-2]:[background:var(--color-legacy-dbeafe)] [&&]:[&.scope-2]:[color:var(--color-legacy-1e40af)] [&&]:[&&]:[&.scope-3]:[background:var(--color-legacy-f3e8ff)] [&&]:[&&]:[&.scope-3]:[color:var(--color-legacy-6b21a8)] scope-1">
          <span className="pill-label">Scope 1 (Direct)</span>
          <span className="pill-value [background:rgba(255,_255,_255,_0.85)] [padding:3px_10px] [border-radius:var(--radius-sm)] [font-weight:700] [box-shadow:var(--shadow-xs)]">{formatCompactNumber(stats.scope1)} tCO₂e</span>
        </div>
        <div className="scope-pill [flex:1] [display:flex] [justify-content:space-between] [align-items:center] [padding:10px_16px] [border-radius:var(--radius-md)] [font-size:var(--text-base)] [font-weight:600] [&.scope-1]:[background:var(--color-brand-50)] [&.scope-1]:[color:var(--color-brand-700)] [&&]:[&.scope-2]:[background:var(--color-legacy-dbeafe)] [&&]:[&.scope-2]:[color:var(--color-legacy-1e40af)] [&&]:[&&]:[&.scope-3]:[background:var(--color-legacy-f3e8ff)] [&&]:[&&]:[&.scope-3]:[color:var(--color-legacy-6b21a8)] scope-2">
          <span className="pill-label">Scope 2 (Indirect)</span>
          <span className="pill-value [background:rgba(255,_255,_255,_0.85)] [padding:3px_10px] [border-radius:var(--radius-sm)] [font-weight:700] [box-shadow:var(--shadow-xs)]">{formatCompactNumber(stats.scope2)} tCO₂e</span>
        </div>
        <div className="scope-pill [flex:1] [display:flex] [justify-content:space-between] [align-items:center] [padding:10px_16px] [border-radius:var(--radius-md)] [font-size:var(--text-base)] [font-weight:600] [&.scope-1]:[background:var(--color-brand-50)] [&.scope-1]:[color:var(--color-brand-700)] [&&]:[&.scope-2]:[background:var(--color-legacy-dbeafe)] [&&]:[&.scope-2]:[color:var(--color-legacy-1e40af)] [&&]:[&&]:[&.scope-3]:[background:var(--color-legacy-f3e8ff)] [&&]:[&&]:[&.scope-3]:[color:var(--color-legacy-6b21a8)] scope-3">
          <span className="pill-label">Scope 3 (Supply Chain)</span>
          <span className="pill-value [background:rgba(255,_255,_255,_0.85)] [padding:3px_10px] [border-radius:var(--radius-sm)] [font-weight:700] [box-shadow:var(--shadow-xs)]">{formatCompactNumber(stats.scope3)} tCO₂e</span>
        </div>
      </div>
    </Card>
  );
};

export default EmissionsOverviewCard;
