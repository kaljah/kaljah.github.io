import React from "react";
import { AlertTriangle, CheckCircle2, Flame } from "lucide-react";
import { Badge, Card, StatCard, type StatCardTone } from "../../ui";
import { formatCompactNumber } from "../../utils/formatters";
import { buildKpiMetadata } from "../../utils/kpiMetadata";
import { t } from "../../i18n";

const UNIT_TITLE = t("thousand standard m³ (15.6 °C / 60 °F, 1 atm)");

export interface FlaringStreamData {
  volume_knm3?: number;
  percentage?: number | null;
  tco2e?: number;
  [key: string]: any;
}

interface StreamTileProps {
  label: string;
  sublabel?: string;
  stream?: FlaringStreamData;
  rule: string;
  tone?: StatCardTone;
  testId?: string;
  shareLabel?: string;
  info?: any;
}

// One flaring stream tile: volume, share of total and tCO2e. The left rule and tone colors the stream category.
const StreamTile: React.FC<StreamTileProps> = ({ label, sublabel, stream, rule, tone = "default", testId, shareLabel = t("of total"), info }) => (
  <StatCard
    data-testid={testId}
    className={`border-l-2 p-4 min-w-0 ${rule}`}
    tone={tone}
    label={label}
    sublabel={sublabel}
    value={stream?.volume_knm3 ?? 0}
    format="number"
    decimals={0}
    unit="kSm3"
    info={info}
    footnote={
      stream?.percentage == null
        ? `${formatCompactNumber(stream?.tco2e ?? 0)} tCO₂e • ${t("100% Stream")}`
        : `${stream.percentage}% ${shareLabel} • ${formatCompactNumber(stream?.tco2e ?? 0)} tCO₂e`
    }
    title={UNIT_TITLE}
  />
);

export interface FlaringData {
  year?: string | number;
  is_compliant?: boolean | null;
  compliance_status?: string;
  yoy_change_pct?: number | null;
  gas_production_m3?: number;
  flaring_intensity_pct?: number | null;
  gwp_horizon?: string | number;
  includes_pending?: boolean;
  measured_dre_pct?: number | null;
  dre_method?: string;
  total_flaring?: FlaringStreamData;
  routine_flaring?: FlaringStreamData;
  non_routine_flaring?: FlaringStreamData;
  safety_flaring?: FlaringStreamData;
  unclassified_flaring?: FlaringStreamData;
  stream_tco2e_allocated?: boolean;
  [key: string]: any;
}

export interface FlaringComplianceCardProps {
  flaringData: FlaringData;
}

// Operational flaring and Executive Decree 21-330 compliance: status badges, stream tiles, intensity vs the 1% limit.
const FlaringComplianceCard: React.FC<FlaringComplianceCardProps> = ({ flaringData }) => {
  const compliant = flaringData.is_compliant;
  const yoy = flaringData.yoy_change_pct;
  const showIntensity = (flaringData.gas_production_m3 ?? 0) > 0 && flaringData.flaring_intensity_pct != null;
  // flaring that is in no stream is shown, by volume or by emissions (BUG-0027: its tCO2e were hidden)
  const showUnclassified =
    (flaringData.unclassified_flaring?.volume_knm3 ?? 0) > 0 || (flaringData.unclassified_flaring?.tco2e ?? 0) > 0;

  return (
    <Card as="section" className="flaring-kpi-banner flex flex-col gap-5" aria-label={t("Operational flaring and regulatory compliance")}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <span className="inline-flex size-9 shrink-0 items-center justify-center rounded border border-border/60 bg-surface text-brand-600">
            <Flame className="size-4.5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h3 className="m-0 text-lg font-semibold text-text truncate">{t("Operational Flaring & Regulatory Compliance")}</h3>
            <p className="m-0 mt-0.5 text-sm text-text-secondary">
              {t("Executive Decree 21-330 Article 9 (1.00% Gas Production Threshold) •")}{" "}
              {flaringData.year === "all" ? t("All years") : `Year ${flaringData.year}`}{" "}{t("• GWP-")}
              {flaringData.gwp_horizon || "100"}
              {flaringData.includes_pending ? t(" • incl. Pending") : t(" • Verified only")}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Badge
            tone={compliant === true ? "success" : compliant === false ? "danger" : "info"}
            className="max-w-full shrink whitespace-normal font-medium"
          >
            {compliant === true ? (
              <CheckCircle2 className="size-3.5" aria-hidden="true" />
            ) : (
              <AlertTriangle className="size-3.5" aria-hidden="true" />
            )}
            {flaringData.compliance_status}
          </Badge>
          <Badge tone="neutral" className="max-w-full shrink whitespace-normal font-medium">
            {flaringData.measured_dre_pct != null
              ? `${flaringData.dre_method}: ${flaringData.measured_dre_pct}% DRE`
              : flaringData.dre_method}
          </Badge>
          {yoy != null && yoy !== 0 && <Badge tone="info" className="font-medium">{yoy > 0 ? `+${yoy}% YoY` : `${yoy}% YoY`}</Badge>}
        </div>
      </div>

      <div className={`grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 ${showUnclassified ? "xl:grid-cols-5" : "xl:grid-cols-4"}`}>
        <StreamTile
          testId="flaring-total"
          label={t("Metered Flared Volume")}
          sublabel={
            flaringData.includes_pending
              ? t("Metered CPF streams · Includes drafts")
              : t("Metered CPF streams · Verified only")
          }
          stream={{ ...flaringData.total_flaring, percentage: null }}
          rule="border-l-brand-700"
          tone="default"
          info={buildKpiMetadata("flaring", {
            year: flaringData.year,
            verifiedOnly: !flaringData.includes_pending,
            gwpHorizon: String(flaringData.gwp_horizon || "100"),
          })}
        />
        <StreamTile
          testId="flaring-routine"
          label={t("Routine Flaring")}
          stream={flaringData.routine_flaring}
          rule="border-l-red-500"
          tone="danger"
        />
        <StreamTile
          testId="flaring-non-routine"
          label={t("Non-Routine Flaring")}
          stream={flaringData.non_routine_flaring}
          rule="border-l-amber-500"
          tone="warning"
        />
        <StreamTile
          testId="flaring-safety"
          label={t("Safety & Purge Flaring")}
          stream={flaringData.safety_flaring}
          rule="border-l-blue-500"
          tone="info"
        />
        {showUnclassified && (
          <StreamTile
            testId="flaring-unclassified"
            label={t("Unclassified Flaring")}
            stream={flaringData.unclassified_flaring}
            rule="border-l-ink-400"
            tone="default"
          />
        )}
      </div>
      {flaringData.stream_tco2e_allocated && (
        <p className="m-0 text-xs text-text-secondary">
          {t("Stream emissions are split by the reported stream volumes: the flaring records are not classified by stream.")}
        </p>
      )}

      {showIntensity && (
        <div className="flex flex-col gap-2.5 rounded-lg border border-border bg-surface/60 p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm text-text">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-text">{t("Decree 21-330 Flaring Intensity:")}</span>
              <span className={`font-mono font-bold ${compliant ? "text-success-fg" : "text-danger-fg"}`}>
                {flaringData.flaring_intensity_pct}%
              </span>
              <span className="text-xs text-text-secondary">
                {t("of Gross Gas Produced (")}{formatCompactNumber((flaringData.gas_production_m3 ?? 0) / 1e6, 2)}{" "}{t("MMSm³)")}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-text-secondary">
              <span>{t("Statutory limit:")} <strong className="text-text font-semibold">1.00%</strong></span>
              <span>•</span>
              <span className={compliant ? "text-success-fg font-medium" : "text-danger-fg font-medium"}>
                {compliant
                  ? `${(1.0 - (flaringData.flaring_intensity_pct ?? 0)).toFixed(2)}% Headroom`
                  : `${((flaringData.flaring_intensity_pct ?? 0) - 1.0).toFixed(2)}% Exceedance`}
              </span>
            </div>
          </div>
          <div className="relative pt-1">
            <div
              role="progressbar"
              aria-label={t("Flaring intensity against the 1.00% statutory limit")}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.min(100, flaringData.flaring_intensity_pct ?? 0)}
              className="relative h-2.5 overflow-hidden rounded-full bg-ink-200"
            >
              <div
                className={`h-full rounded-full transition-all duration-300 ${compliant ? "bg-green-500" : "bg-red-500"}`}
                // eslint-disable-next-line no-restricted-syntax -- width is data-driven
                style={{ width: `${Math.min(100, ((flaringData.flaring_intensity_pct ?? 0) / 1.0) * 100)}%` }}
              />
            </div>
            <div className="mt-1 flex justify-between text-[11px] font-mono text-text-secondary">
              <span>0.00% Baseline</span>
              <span className="font-medium text-text">1.00% Statutory Ceiling (Art. 9)</span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

export default FlaringComplianceCard;
