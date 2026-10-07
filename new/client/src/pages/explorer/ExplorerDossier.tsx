import React from "react";
import { Activity, AlertCircle, BarChart3, Check, Copy, MapPin, RefreshCw, Satellite, ShieldCheck, Target, X } from "lucide-react";
import { Badge, Banner, Button, IconButton, Skeleton } from "../../ui";
import { cn } from "../../ui/cn";

const Caption: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="text-xs font-bold uppercase tracking-wide text-text-secondary">{children}</span>
);

interface StatProps {
  label: React.ReactNode;
  value: React.ReactNode;
  unit?: string;
  tone?: "danger" | "warning";
  className?: string;
}

const Stat: React.FC<StatProps> = ({ label, value, unit, tone, className }) => (
  <div className={cn("flex flex-col gap-0.5 rounded-md border border-border bg-surface px-2.5 py-2", className)}>
    <Caption>{label}</Caption>
    <span className={cn("text-md font-extrabold tabular-nums text-text", tone === "danger" && "text-danger-fg", tone === "warning" && "text-warning-fg")}>
      {value} {unit && <span className="text-xs font-semibold text-text-secondary">{unit}</span>}
    </span>
  </div>
);

const num = (v: any, digits: number = 1): string => Number(v || 0).toFixed(digits);

interface SectionTitleProps {
  icon: React.ComponentType<{ className?: string; [key: string]: any }>;
  children: React.ReactNode;
}

const SectionTitle: React.FC<SectionTitleProps> = ({ icon: Icon, children }) => (
  <h4 className="m-0 mb-2.5 flex items-center gap-1.5 text-sm font-extrabold uppercase tracking-wide text-text-secondary">
    <Icon className="size-4 text-brand-500" aria-hidden="true" /> {children}
  </h4>
);

interface SatelliteSectionProps {
  loading?: boolean;
  observation?: any;
  reconciliation?: {
    color: string;
    label: string;
    deltaText: string;
    [key: string]: any;
  } | null;
  exporting?: boolean;
  onExport: () => void;
  onConfigure: () => void;
}

const SatelliteSection: React.FC<SatelliteSectionProps> = ({ loading, observation, reconciliation, exporting, onExport, onConfigure }) => {
  const summary = observation?.summary;
  return (
    <section className="mb-3.5 rounded-lg border border-blue-500/30 bg-info-bg p-3.5">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="m-0 flex items-center gap-1.5 text-sm font-bold text-info-fg">
          <Satellite className="size-4" aria-hidden="true" /> Copernicus Sentinel-5P overpass
        </h4>
        {loading ? (
          <span className="flex items-center gap-1.5 text-xs text-info-fg">
            <RefreshCw className="size-3 animate-spin" aria-hidden="true" /> STAC query…
          </span>
        ) : (
          summary?.stream_type && <Badge tone="success">● {summary.stream_type}</Badge>
        )}
      </div>

      {loading ? (
        <div className="flex flex-col gap-2 py-3" role="status" aria-label="Loading satellite data">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      ) : observation?.authenticated && summary ? (
        <div>
          <div className="mb-2.5 grid grid-cols-2 gap-2">
            <Stat label="Mean CH₄ column" value={num(summary.mean_ch4_column_ppb)} unit="ppb" />
            <Stat label="Max anomaly (ΔCH₄)" value={`+${num(summary.max_anomaly_ppb)}`} unit="ppb" tone={Number(summary.max_anomaly_ppb || 0) >= 25 ? "danger" : "warning"} />
            <Stat
              label="Inferred emission rate"
              value={Number(summary.estimated_emission_rate_kg_hr || 0) > 0 ? `${num(summary.estimated_emission_rate_kg_hr)} kg/hr` : "Background"}
              tone="warning"
            />
            <Stat label="Annualized satellite flux" value={`${Number(summary.annualized_ch4_tonnes || 0) > 0 ? num(summary.annualized_ch4_tonnes) : "0.0"} t/yr`} />
          </div>

          <dl className="m-0 mb-2.5 flex justify-between border-b border-border px-0.5 pb-1.5 text-xs text-text-secondary">
            <div>
              <dt className="mr-1 inline">Overpass:</dt>
              <dd className="m-0 inline font-semibold text-text">
                {summary.latest_observation_date} {summary.latest_observation_time ? `(${summary.latest_observation_time})` : ""}
              </dd>
            </div>
            <div>
              <dt className="mr-1 inline">QA confidence:</dt>
              <dd className="m-0 inline font-semibold text-text">{(Number(summary.mean_qa_score || 0) * 100).toFixed(0)}%</dd>
            </div>
          </dl>

          {reconciliation && (
            <div className="mb-3 rounded-md border bg-surface p-2.5" style={{ borderColor: `${reconciliation.color}50` }}>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs font-bold text-text">
                  <Activity className="size-3.5" style={{ color: reconciliation.color }} aria-hidden="true" /> OGMP 2.0 reconciliation gap
                </span>
                <span
                  className="rounded-sm border px-1.5 py-0.5 text-xs font-bold"
                  style={{ backgroundColor: `${reconciliation.color}15`, color: reconciliation.color, borderColor: `${reconciliation.color}40` }}
                >
                  {reconciliation.label}
                </span>
              </div>
              <p className="m-0 text-xs leading-snug text-text-secondary">{reconciliation.deltaText}</p>
            </div>
          )}

          <Button id="reconcile-ogmp-btn" className="w-full" onClick={onExport} loading={exporting} disabled={exporting}>
            <ShieldCheck className="size-4" aria-hidden="true" />
            {exporting ? "Recording Level 5 verification…" : "Reconcile into OGMP 2.0 ledger"}
          </Button>
        </div>
      ) : (
        <div className="flex gap-3 p-2">
          <AlertCircle className="size-[18px] shrink-0 text-warning-fg" aria-hidden="true" />
          <div>
            <p className="m-0 mb-1 text-sm font-bold text-warning-fg">Copernicus live feed unconfigured</p>
            <p className="m-0 mb-2 text-xs leading-snug text-text-secondary">
              Connect your free Copernicus Data Space Ecosystem (CDSE) credentials in Settings to stream verified Sentinel-5P overpasses.
            </p>
            <Button variant="secondary" size="sm" onClick={onConfigure}>
              Configure in Settings →
            </Button>
          </div>
        </div>
      )}
    </section>
  );
};

export interface ExplorerDossierProps {
  facility: {
    id: number | string;
    name: string;
    code?: string;
    region?: string;
    activity?: string;
    division?: string;
    latitude?: number | string;
    longitude?: number | string;
    [key: string]: any;
  };
  stats: {
    total_ch4?: number;
    total_co2e?: number;
    total_boe?: number;
    ch4_intensity?: number;
    co2_intensity?: number;
    api_flaring_intensity?: number;
    [key: string]: any;
  };
  viewMode: "methane" | "total" | string;
  formatCompact: (v: any) => string;
  copiedCoords: boolean;
  onCopyCoords: () => void;
  onClose: () => void;
  satelliteLoading?: boolean;
  satelliteObservation?: any;
  reconciliation?: {
    color: string;
    label: string;
    deltaText: string;
    [key: string]: any;
  } | null;
  exporting?: boolean;
  onExport: () => void;
  onConfigure: () => void;
  loadingSurveys?: boolean;
  surveys?: any[];
  onCenter: () => void;
}

/** Slide-in dossier for the selected facility: satellite evidence, OGMP surveys and the bottom-up inventory. */
const ExplorerDossier: React.FC<ExplorerDossierProps> = ({
  facility,
  stats,
  viewMode,
  formatCompact,
  copiedCoords,
  onCopyCoords,
  onClose,
  satelliteLoading,
  satelliteObservation,
  reconciliation,
  exporting,
  onExport,
  onConfigure,
  loadingSurveys,
  surveys = [],
  onCenter,
}) => {
  const methane = viewMode === "methane";
  return (
    <section
      aria-label="Facility Reconnaissance Dossier"
      className="absolute bottom-5 right-4 top-[78px] z-950 flex w-[390px] max-w-[calc(100vw-32px)] animate-[slideInDossier_0.3s_cubic-bezier(0.16,1,0.3,1)] flex-col overflow-y-auto overflow-x-hidden rounded-lg border border-border bg-surface/95 p-5 shadow-lg backdrop-blur-lg"
    >
      <header className="relative mb-4 border-b border-ink-100 pb-3.5">
        <IconButton label="Close dossier" className="absolute right-0 top-0" onClick={onClose}>
          <X className="size-4" aria-hidden="true" />
        </IconButton>
        <p className="m-0 mb-1 inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-brand-700">
          <span className="size-1.5 rounded-full bg-brand-500" aria-hidden="true" /> Facility reconnaissance dossier
        </p>
        <h3 className="m-0 mb-1.5 pr-10 text-xl font-extrabold leading-tight text-text">{facility.name}</h3>
        <div className="flex items-center justify-between gap-2.5">
          <span className="flex items-center gap-1.5 text-sm text-text-secondary">
            <MapPin className="size-3.5 text-brand-500" aria-hidden="true" />
            {facility.region ? `${facility.region} Region` : "Algeria"} • {facility.activity || facility.division || "Facility"}
          </span>
          <Button variant="secondary" size="sm" className="font-mono text-xs" onClick={onCopyCoords} title="Copy coordinates to clipboard">
            {copiedCoords ? (
              <>
                <Check className="size-3 text-success-fg" aria-hidden="true" /> Copied!
              </>
            ) : (
              <>
                <Copy className="size-3" aria-hidden="true" /> {Number(facility.latitude || 0).toFixed(4)}°N, {Number(facility.longitude || 0).toFixed(4)}°E
              </>
            )}
          </Button>
        </div>
      </header>

      <SatelliteSection
        loading={satelliteLoading}
        observation={satelliteObservation}
        reconciliation={reconciliation}
        exporting={exporting}
        onExport={onExport}
        onConfigure={onConfigure}
      />

      {loadingSurveys && <p className="mb-2.5 text-sm font-extrabold uppercase tracking-wide text-text-secondary">Loading recorded surveys…</p>}
      {surveys.length > 0 && (
        <Banner tone="success" title={`Verified OGMP surveys in database (${surveys.length})`} className="mb-3.5">
          <ul className="m-0 mt-2 flex list-none flex-col gap-1.5 p-0">
            {surveys.slice(0, 3).map((s) => (
              <li key={s.id} className="flex flex-col gap-1 rounded-md border border-border bg-surface px-2.5 py-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-bold text-text">{s.survey_type || s.surveyType}</span>
                  <span className="text-xs text-text-secondary">{s.survey_date || s.surveyDate}</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-secondary">
                  <span>
                    Rate: <strong>{num(s.measured_rate_kg_hr || s.measuredRateKgHr)} kg/hr</strong>
                  </span>
                  <span>
                    Annual: <strong>{num(s.estimated_annual_tch4 || s.estimatedAnnualTch4)} tCH₄</strong>
                  </span>
                  <Badge tone="success" className="ml-auto">
                    {s.reconciliation_status || "Recorded"}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </Banner>
      )}

      <section className="mb-3.5">
        <SectionTitle icon={BarChart3}>Bottom-up reported inventory</SectionTitle>
        <div className="grid grid-cols-2 gap-2">
          <Stat
            className="col-span-2 border-l-4 border-l-brand-500"
            label={methane ? "Reported methane (CH₄)" : "Reported total GHG"}
            value={methane ? `${formatCompact(stats.total_ch4)} tCH₄` : `${formatCompact(stats.total_co2e)} tCO₂e`}
          />
          <Stat label="Production" value={formatCompact(stats.total_boe)} unit="BOE / year" />
          <Stat
            label={methane ? "Methane intensity" : "Carbon intensity"}
            value={methane ? num(stats.ch4_intensity, 3) : num(stats.co2_intensity, 2)}
            unit={methane ? "kgCH₄/boe" : "kgCO₂e/boe"}
            tone="warning"
          />
          <Stat label="Flaring intensity" value={num(stats.api_flaring_intensity, 2)} unit="kgCO₂e/boe" tone="danger" />
          <Stat label="Asset code" value={<span className="font-mono">{facility.code || "N/A"}</span>} unit="database ref" />
        </div>
      </section>

      <div className="mt-auto pt-2.5">
        <Button variant="secondary" className="w-full" onClick={onCenter}>
          <Target className="size-4" aria-hidden="true" /> Center aerial camera (zoom 11x)
        </Button>
      </div>
    </section>
  );
};

export default ExplorerDossier;
