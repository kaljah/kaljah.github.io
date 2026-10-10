import React from "react";
import { BarChart3, Check, Copy, MapPin, Target, X } from "lucide-react";
import { Badge, Banner, Button, IconButton } from "../../ui";
import { cn } from "../../ui/cn";
import { t } from "../../i18n";

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
  loadingSurveys?: boolean;
  surveys?: any[];
  onCenter: () => void;
}

/** Slide-in dossier for the selected facility: recorded OGMP surveys and the bottom-up inventory. */
const ExplorerDossier: React.FC<ExplorerDossierProps> = ({
  facility,
  stats,
  viewMode,
  formatCompact,
  copiedCoords,
  onCopyCoords,
  onClose,
  loadingSurveys,
  surveys = [],
  onCenter,
}) => {
  const methane = viewMode === "methane";
  return (
    <section
      aria-label={t("Facility Reconnaissance Dossier")}
      className="absolute bottom-5 right-4 top-[78px] z-950 flex w-[390px] max-w-[calc(100vw-32px)] animate-[slideInDossier_0.3s_cubic-bezier(0.16,1,0.3,1)] flex-col overflow-y-auto overflow-x-hidden rounded-lg border border-border bg-surface/95 p-5 shadow-lg backdrop-blur-lg"
    >
      <header className="relative mb-4 border-b border-ink-100 pb-3.5">
        <IconButton label={t("Close dossier")} className="absolute right-0 top-0" onClick={onClose}>
          <X className="size-4" aria-hidden="true" />
        </IconButton>
        <p className="m-0 mb-1 inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-brand-700">
          <span className="size-1.5 rounded-full bg-brand-500" aria-hidden="true" />{" "}{t("Facility reconnaissance dossier")}
        </p>
        <h3 className="m-0 mb-1.5 pr-10 text-xl font-extrabold leading-tight text-text">{facility.name}</h3>
        <div className="flex items-center justify-between gap-2.5">
          <span className="flex items-center gap-1.5 text-sm text-text-secondary">
            <MapPin className="size-3.5 text-brand-500" aria-hidden="true" />
            {facility.region ? `${facility.region} Region` : t("Algeria")} • {facility.activity || facility.division || t("Facility")}
          </span>
          <Button variant="secondary" size="sm" className="font-mono text-xs" onClick={onCopyCoords} title={t("Copy coordinates to clipboard")}>
            {copiedCoords ? (
              <>
                <Check className="size-3 text-success-fg" aria-hidden="true" />{" "}{t("Copied!")}
              </>
            ) : (
              <>
                <Copy className="size-3" aria-hidden="true" /> {Number(facility.latitude || 0).toFixed(4)}°N, {Number(facility.longitude || 0).toFixed(4)}°E
              </>
            )}
          </Button>
        </div>
      </header>


      {loadingSurveys && <p className="mb-2.5 text-sm font-extrabold uppercase tracking-wide text-text-secondary">{t("Loading recorded surveys…")}</p>}
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
                    {t("Rate:")}{" "}<strong>{num(s.measured_rate_kg_hr || s.measuredRateKgHr)} kg/hr</strong>
                  </span>
                  <span>
                    {t("Annual:")}{" "}<strong>{num(s.estimated_annual_tch4 || s.estimatedAnnualTch4)}{" "}{t("tCH₄")}</strong>
                  </span>
                  <Badge tone="success" className="ml-auto">
                    {s.reconciliation_status || t("Recorded")}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </Banner>
      )}

      <section className="mb-3.5">
        <SectionTitle icon={BarChart3}>{t("Bottom-up reported inventory")}</SectionTitle>
        <div className="grid grid-cols-2 gap-2">
          <Stat
            className="col-span-2 border-l-4 border-l-brand-500"
            label={methane ? t("Reported methane (CH₄)") : t("Reported total GHG")}
            value={methane ? `${formatCompact(stats.total_ch4)} tCH₄` : `${formatCompact(stats.total_co2e)} tCO₂e`}
          />
          <Stat label={t("Production")} value={formatCompact(stats.total_boe)} unit="BOE / year" />
          <Stat
            label={methane ? t("Methane intensity") : t("Carbon intensity")}
            value={methane ? num(stats.ch4_intensity, 3) : num(stats.co2_intensity, 2)}
            unit={methane ? "kgCH₄/boe" : "kgCO₂e/boe"}
            tone="warning"
          />
          <Stat label={t("Flaring intensity")} value={num(stats.api_flaring_intensity, 2)} unit="kgCO₂e/boe" tone="danger" />
          <Stat label={t("Asset code")} value={<span className="font-mono">{facility.code || "N/A"}</span>} unit="database ref" />
        </div>
      </section>

      <div className="mt-auto pt-2.5">
        <Button variant="secondary" className="w-full" onClick={onCenter}>
          <Target className="size-4" aria-hidden="true" />{" "}{t("Center aerial camera (zoom 11x)")}
        </Button>
      </div>
    </section>
  );
};

export default ExplorerDossier;
