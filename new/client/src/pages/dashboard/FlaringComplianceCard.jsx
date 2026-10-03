import React from "react";
import { AlertTriangle, CheckCircle2, Flame } from "lucide-react";
import { Badge, Card, StatCard } from "../../ui";
import { formatCompactNumber } from "../../utils/formatters";

const UNIT_TITLE = "thousand standard m³ (15.6 °C / 60 °F, 1 atm)";

// One flaring stream tile: volume, share of total and tCO2e. The left rule colors the stream category.
const StreamTile = ({ label, stream, rule, testId, shareLabel = "of total" }) => (
  <StatCard
    data-testid={testId}
    className={`border-l-4 p-4 ${rule}`}
    label={label}
    value={stream?.volume_knm3 ?? 0}
    format="number"
    decimals={0}
    unit="kSm3"
    footnote={
      stream?.percentage == null
        ? `${formatCompactNumber(stream?.tco2e ?? 0)} tCO₂e • 100% Stream`
        : `${stream.percentage}% ${shareLabel} • ${formatCompactNumber(stream?.tco2e ?? 0)} tCO₂e`
    }
    title={UNIT_TITLE}
  />
);

// Operational flaring and Executive Decree 21-330 compliance: status badges, stream tiles, intensity vs the 1% limit.
const FlaringComplianceCard = ({ flaringData }) => {
  const compliant = flaringData.is_compliant;
  const yoy = flaringData.yoy_change_pct;
  const showIntensity = flaringData.gas_production_m3 > 0 && flaringData.flaring_intensity_pct != null;

  return (
    <Card as="section" className="[margin-top:20px]! [padding:22px_24px]! [border-radius:var(--radius-lg)]! [background:linear-gradient(135deg,_rgba(255,_255,_255,_0.95)_0%,_rgba(255,_247,_237,_0.6)_100%)]! [border:1px_solid_rgba(251,_146,_60,_0.3)]! [box-shadow:0_4px_20px_-2px_rgba(234,_88,_12,_0.08),_0_2px_6px_-1px_rgba(0,_0,_0,_0.04)]! flex flex-col gap-5" aria-label="Operational flaring and regulatory compliance">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700">
            <Flame className="size-5" aria-hidden="true" />
          </span>
          <div>
            <h3 className="m-0 text-lg font-semibold text-text">Operational Flaring &amp; Regulatory Compliance</h3>
            <p className="m-0 mt-0.5 text-sm text-text-secondary">
              Executive Decree 21-330 Article 9 (1.00% Gas Production Threshold) •{" "}
              {flaringData.year === "all" ? "All years" : `Year ${flaringData.year}`} • GWP-
              {flaringData.gwp_horizon || "100"}
              {flaringData.includes_pending ? " • incl. Pending" : " • Verified only"}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={compliant === true ? "success" : compliant === false ? "danger" : "info"}>
            {compliant === true ? (
              <CheckCircle2 className="size-3.5" aria-hidden="true" />
            ) : (
              <AlertTriangle className="size-3.5" aria-hidden="true" />
            )}
            {flaringData.compliance_status}
          </Badge>
          <Badge tone="neutral">
            {flaringData.measured_dre_pct != null
              ? `${flaringData.dre_method}: ${flaringData.measured_dre_pct}% DRE`
              : flaringData.dre_method}
          </Badge>
          {yoy != null && yoy !== 0 && <Badge tone="info">{yoy > 0 ? `+${yoy}% YoY` : `${yoy}% YoY`}</Badge>}
        </div>
      </div>

      <div className={`grid gap-4 sm:grid-cols-2 ${flaringData.unclassified_flaring?.volume_knm3 > 0 ? "lg:grid-cols-5" : "lg:grid-cols-4"}`}>
        <StreamTile
          testId="flaring-total"
          label="Total Flared Volume"
          stream={{ ...flaringData.total_flaring, percentage: null }}
          rule="border-l-brand-500"
        />
        <StreamTile testId="flaring-routine" label="Routine Flaring" stream={flaringData.routine_flaring} rule="border-l-red-500" />
        <StreamTile
          testId="flaring-non-routine"
          label="Non-Routine Flaring"
          stream={flaringData.non_routine_flaring}
          rule="border-l-amber-500"
        />
        <StreamTile
          testId="flaring-safety"
          label="Safety & Purge Flaring"
          stream={flaringData.safety_flaring}
          rule="border-l-blue-500"
        />
        {flaringData.unclassified_flaring?.volume_knm3 > 0 && (
          <StreamTile
            testId="flaring-unclassified"
            label="Unclassified Flaring"
            stream={flaringData.unclassified_flaring}
            rule="border-l-ink-400"
          />
        )}
      </div>

      {showIntensity && (
        <div className="flex flex-col gap-2 rounded-md border border-border bg-ink-50 p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-base text-text">
            <span>
              <strong>Decree 21-330 Flaring Intensity:</strong>{" "}
              <strong className={compliant ? "text-success-fg" : "text-danger-fg"}>{flaringData.flaring_intensity_pct}%</strong>{" "}
              of Gross Gas Produced ({formatCompactNumber(flaringData.gas_production_m3 / 1e6, 2)} MMSm³)
            </span>
            <span className="text-sm text-text-secondary">
              Statutory limit: <strong>1.00%</strong> (Executive Decree 21-330 Art. 9)
            </span>
          </div>
          <div
            role="progressbar"
            aria-label="Flaring intensity against the 1.00% statutory limit"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.min(100, flaringData.flaring_intensity_pct)}
            className="relative h-2 overflow-hidden rounded-full bg-ink-200"
          >
            <div
              className={`h-full rounded-full ${compliant ? "bg-green-500" : "bg-red-500"}`}
              // eslint-disable-next-line no-restricted-syntax -- width is data-driven
              style={{ width: `${Math.min(100, (flaringData.flaring_intensity_pct / 1.0) * 100)}%` }}
            />
          </div>
        </div>
      )}
    </Card>
  );
};

export default FlaringComplianceCard;
