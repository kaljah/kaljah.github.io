import React from "react";
import { Printer } from "lucide-react";
import { Badge, Button, Card, StatCard } from "../../ui";
import { formatCompactNumber } from "../../utils/formatters";
import { buildKpiMetadata } from "../../utils/kpiMetadata";
import { t } from "../../i18n";

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
  pendingCount?: number;
  includePending?: boolean;
  scope2Method?: string;
  gwpStandard?: string;
  gwpHorizon?: string;
  lastUpdated?: string;
  onNavigateToPending?: () => void;
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

/**
 * Emissions overview: Row 1 = 4 hero KPIs (gross, intensity, methane, pending review) per B5.
 * Row 2 = Scope 1/2/3 breakdown with canonical scope colors (C2).
 */
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
  pendingCount = 0,
  includePending = false,
  scope2Method = "location",
  gwpStandard = "ar5",
  gwpHorizon = "100",
  lastUpdated,
  onNavigateToPending,
  stats,
  variance,
}) => {
  const location =
    currentRegion !== "all"
      ? facilities.find((f) => f.id.toString() === currentRegion)?.name || t("Region")
      : currentDivision !== "all"
        ? currentDivision
        : currentActivity !== "all"
          ? currentActivity
          : t("All Regions");
  const compare = currentYear !== "all";
  const emissionsDelta = compare ? toDelta(variance.emissions) : null;
  const intensityDelta = compare && hasProductionData ? toDelta(variance.intensity) : null;
  const goalShare = goal && goal.target_amount > 0 ? (stats.totalEmissions / goal.target_amount) * 100 : null;
  const intensityPending = !hasProductionData && stats.totalEmissions > 0;

  const totalReported = (stats.scope1 || 0) + (stats.scope2 || 0) + (stats.scope3 || 0);
  const s1Pct = totalReported > 0 ? (((stats.scope1 || 0) / totalReported) * 100).toFixed(0) : null;
  const s2Pct = totalReported > 0 ? (((stats.scope2 || 0) / totalReported) * 100).toFixed(0) : null;
  const s3Pct = totalReported > 0 ? (((stats.scope3 || 0) / totalReported) * 100).toFixed(0) : null;

  const kpiOpts = {
    year: currentYear,
    verifiedOnly: !includePending,
    scope2Method,
    gwpStandard,
    gwpHorizon,
    lastUpdated,
  };

  return (
    <Card as="section" className="hero-card flex flex-col gap-5" aria-label={t("Emissions overview")}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="flex flex-wrap items-baseline gap-2.5">
          <h2 className="text-lg font-semibold text-text">{t("Emissions Overview")}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral" className="font-mono text-xs font-medium">{location}</Badge>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportPDF}
            loading={exportingPDF}
            title={t("Export multi-page executive summary PDF")}
          >
            <Printer className="size-4" aria-hidden="true" />
            {exportingPDF ? t("Generating PDF...") : t("Export Executive Brief (PDF)")}
          </Button>
        </div>
      </div>

      {/* Row 1: max 4 hero KPIs (gross emissions, intensity, methane, pending review) */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          className="p-4"
          data-testid="kpi-gross"
          tone="default"
          label={t("Gross Operational Emissions")}
          sublabel={
            includePending
              ? t("Scope 1+2 · Includes drafts")
              : t("Scope 1+2 · Verified only")
          }
          value={stats.totalEmissions}
          unit="tCO2e"
          delta={emissionsDelta === null ? undefined : { value: emissionsDelta, goodWhen: "down", label: t("vs prior year") }}
          footnote={goalShare === null ? undefined : `${goalShare.toFixed(1)}% of target`}
          info={buildKpiMetadata("grossEmissions", { ...kpiOpts, scope: "Scope 1+2" })}
        />
        <StatCard
          className="p-4"
          data-testid="kpi-intensity"
          tone={intensityPending ? "warning" : "default"}
          label={t("Performance Intensity")}
          sublabel={
            includePending
              ? t("CO2e/BOE · Includes drafts")
              : t("CO2e/BOE · Verified only")
          }
          value={intensity}
          valueText={intensityPending ? t("Pending") : undefined}
          format="compact"
          decimals={2}
          unit={intensityPending ? "Production" : "kg/BOE"}
          delta={intensityDelta === null ? undefined : { value: intensityDelta, goodWhen: "down", label: t("vs prior year") }}
          footnote={intensityPending ? t("Production figures required") : undefined}
          info={buildKpiMetadata("carbonIntensity", { ...kpiOpts, scope: "Scope 1+2" })}
        />
        <StatCard
          className="p-4"
          data-testid="kpi-ch4"
          tone="default"
          label={t("Total CH4 (Methane)")}
          sublabel={
            includePending
              ? t("Venting, flaring, fugitive · Includes drafts")
              : t("Venting, flaring, fugitive · Verified only")
          }
          value={stats.methaneEmissions}
          unit="tCH4"
          info={buildKpiMetadata("methane", { ...kpiOpts, scope: "Direct CH4" })}
        />
        <StatCard
          className="p-4"
          data-testid="kpi-pending"
          tone={pendingCount > 0 ? "warning" : "default"}
          label={t("Pending Review")}
          sublabel={t("Maker-checker queue")}
          value={pendingCount}
          unit={t("records")}
          footnote={
            onNavigateToPending ? (
              <button
                type="button"
                onClick={onNavigateToPending}
                className="mt-1 flex items-center justify-between w-full text-xs text-brand-700 font-semibold cursor-pointer hover:underline border-0 bg-transparent p-0"
              >
                <span>{t("Admin & Lead can approve")}</span>
                <span>{t("Review →")}</span>
              </button>
            ) : (
              t("Admin & Lead can approve")
            )
          }
          info={buildKpiMetadata("pending", { lastUpdated })}
        />
      </div>

      {/* Row 2: Scope breakdown (Scope 1 = deep orange, Scope 2 = blue, Scope 3 = violet per C2) */}
      <div className="flex flex-col sm:flex-row gap-3 rounded-lg border border-border bg-surface/60 p-3">
        <div className="scope-pill scope-1 flex flex-1 min-w-0 flex-col justify-between gap-1.5 rounded-md border-l-3 border-l-brand-700 border border-border/60 bg-surface p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="pill-label font-medium text-text truncate">{t("Scope 1 (Direct)")}</span>
            {s1Pct !== null && (
              <span className="font-mono text-xs text-text-secondary shrink-0">{s1Pct}% of total</span>
            )}
          </div>
          <span className="pill-value font-mono text-base font-semibold tabular-nums text-text">
            {formatCompactNumber(stats.scope1)} <span className="text-xs font-normal text-text-secondary">{t("tCO₂e")}</span>
          </span>
        </div>
        <div className="scope-pill scope-2 flex flex-1 min-w-0 flex-col justify-between gap-1.5 rounded-md border-l-3 border-l-blue-600 border border-border/60 bg-surface p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="pill-label font-medium text-text truncate">{t("Scope 2 (Indirect)")}</span>
            {s2Pct !== null && (
              <span className="font-mono text-xs text-text-secondary shrink-0">{s2Pct}% of total</span>
            )}
          </div>
          <span className="pill-value font-mono text-base font-semibold tabular-nums text-text">
            {formatCompactNumber(stats.scope2)} <span className="text-xs font-normal text-text-secondary">{t("tCO₂e")}</span>
          </span>
        </div>
        <div className="scope-pill scope-3 flex flex-1 min-w-0 flex-col justify-between gap-1.5 rounded-md border-l-3 border-l-violet-600 border border-border/60 bg-surface p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="pill-label font-medium text-text truncate">{t("Scope 3 (Supply Chain)")}</span>
            {s3Pct !== null && (
              <span className="font-mono text-xs text-text-secondary shrink-0">{s3Pct}% of total</span>
            )}
          </div>
          <span className="pill-value font-mono text-base font-semibold tabular-nums text-text">
            {formatCompactNumber(stats.scope3)} <span className="text-xs font-normal text-text-secondary">{t("tCO₂e")}</span>
          </span>
        </div>
      </div>
    </Card>
  );
};

export default EmissionsOverviewCard;
