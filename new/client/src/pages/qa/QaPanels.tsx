import React from "react";
import { AlertCircle, AlertTriangle, ArrowRight, ChevronDown, ChevronUp, Database, Eye, Flame, Layers, Shield, Sparkles, Zap } from "lucide-react";
import { Badge, Banner, Button, Card, type BadgeTone } from "../../ui";
import { cn } from "../../ui/cn";
import { t } from "../../i18n";

const DIM_BARS = [
  { key: "facility", label: t("Organizational Facility Assignment"), bar: "bg-green-500" },
  { key: "fuel_source", label: t("Source & Fuel Type Specifications"), bar: "bg-blue-500" },
  { key: "activity_amount", label: t("Activity Quantities & Physical Units"), bar: "bg-amber-500" },
  { key: "calculation", label: t("Calculated CO₂e Emissions Integrity"), bar: "bg-violet-500" },
] as const;

const health = (score: number) =>
  score >= 80
    ? { text: "text-success-fg", bg: "bg-success-bg", label: t("Optimal & Verified") }
    : score >= 60
    ? { text: "text-warning-fg", bg: "bg-warning-bg", label: t("Attention Needed") }
    : { text: "text-danger-fg", bg: "bg-danger-bg", label: t("Action Required") };

interface TileProps {
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  label: React.ReactNode;
  title?: string;
  tone?: string;
  value: React.ReactNode;
  valueClass?: string;
  unit?: string;
  children?: React.ReactNode;
}

const Tile: React.FC<TileProps> = ({ icon: Icon, label, title, tone = "bg-ink-100 text-text-secondary", value, valueClass, unit, children }) => (
  <Card className="flex flex-col gap-3 p-5">
    <div className="flex items-center justify-between gap-2">
      <span className="text-sm font-semibold uppercase tracking-wide text-text-secondary" title={title}>
        {label}
      </span>
      <span className={cn("flex size-8 items-center justify-center rounded-md", tone)}>
        <Icon className="size-4" aria-hidden="true" />
      </span>
    </div>
    <div className="flex items-baseline gap-2">
      <span className={cn("text-2xl font-bold leading-none tabular-nums text-text", valueClass)}>{value}</span>
      {unit && <span className="text-base font-semibold text-text-secondary">{unit}</span>}
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-text-secondary [&_strong]:text-text">{children}</div>
  </Card>
);

const pct = (v?: number | null, digits: number = 1): string => (v != null ? `±${(v * 100).toFixed(digits)}%` : "n/a");

export interface QaKpisProps {
  diagnostics: { total_custom_factors?: number; [key: string]: any };
  uncertainty: {
    year?: string | number;
    overall?: number | null;
    scope1?: number | null;
    scope2?: number | null;
    scope3?: number | null;
  };
  anomalies: {
    all: number;
    pending: number;
    verified: number;
    rejected: number;
  };
  totalRecords: number;
  activeFacilities: number;
  totalFacilities: number;
  healthScore: number;
  completeness: number;
}

/** Four headline tiles: data health, IPCC uncertainty, flagged anomalies and inventory coverage. */
export const QaKpis: React.FC<QaKpisProps> = ({ diagnostics, uncertainty, anomalies, totalRecords, activeFacilities, totalFacilities, healthScore, completeness }) => {
  const h = health(healthScore);
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Tile icon={Sparkles} label={t("Data Health Score")} tone={cn(h.bg, h.text)} value={healthScore} valueClass={h.text} unit="/ 100">
        <span>
          {t("Status:")}{" "}<strong className={h.text}>{h.label}</strong>
        </span>
        <span>
          {t("Completeness:")}{" "}<strong>{completeness}%</strong>
        </span>
      </Tile>
      <Tile
        icon={AlertTriangle}
        label={`Inventory Uncertainty (95% CI${uncertainty.year ? `, ${uncertainty.year}` : ""})`}
        title={t("IPCC Approach 1 error propagation (square root of sum of squares)")}
        tone="bg-warning-bg text-warning-fg"
        value={uncertainty.overall != null ? `±${(uncertainty.overall * 100).toFixed(2)}` : "n/a"}
        valueClass="text-warning-fg"
        unit={uncertainty.overall != null ? "%" : ""}
      >
        <span>S1: {pct(uncertainty.scope1, 1)}</span>
        <span>S2: {pct(uncertainty.scope2, 1)}</span>
        <span>S3: {pct(uncertainty.scope3, 1)}</span>
      </Tile>
      <Tile icon={AlertCircle} label={t("Flagged Anomalies")} tone="bg-danger-bg text-danger-fg" value={anomalies.all} valueClass={anomalies.all > 0 ? "text-danger-fg" : "text-success-fg"} unit="active">
        <span>
          {t("Pending:")}{" "}<strong>{anomalies.pending}</strong>
        </span>
        <span>
          {t("Verified:")}{" "}<strong className="text-success-fg">{anomalies.verified}</strong>
        </span>
        <span>
          {t("Rejected:")}{" "}<strong className="text-danger-fg">{anomalies.rejected}</strong>
        </span>
      </Tile>
      <Tile icon={Database} label={t("Inventory Coverage")} tone="bg-info-bg text-info-fg" value={totalRecords.toLocaleString()} unit="entries">
        <span>
          {t("Active Facilities:")}{" "}<strong>{activeFacilities}/{totalFacilities}</strong>
        </span>
        <span>
          {t("Custom Factors:")}{" "}<strong>{diagnostics.total_custom_factors ?? 0}</strong>
        </span>
      </Tile>
    </div>
  );
};

const IMPACT_TONE: Record<string, BadgeTone> = { critical: "danger", high: "danger", medium: "warning", low: "info" };
const FINDING_RULE: Record<string, string> = { critical: "border-l-red-500", warning: "border-l-amber-500", info: "border-l-blue-500" };
const FINDING_ICON: Record<string, React.ReactNode> = {
  critical: <AlertCircle className="size-4 text-danger-fg" aria-hidden="true" />,
  warning: <AlertTriangle className="size-4 text-warning-fg" aria-hidden="true" />,
  info: <Shield className="size-4 text-info-fg" aria-hidden="true" />,
};

const th = "border-b border-border bg-ink-50 px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-text-secondary";
const td = "border-b border-ink-100 px-3 py-2 text-sm text-text";

export interface DiagnosticItem {
  id: string;
  title: string;
  impact?: string;
  affected_count: number;
  description: string;
  action?: string;
  sample_records?: any[];
}

const SampleTable: React.FC<{ item: DiagnosticItem }> = ({ item }) => {
  const facilities = item.id === "unused_facilities";
  const records = item.sample_records || [];
  return (
    <div className="mt-1 flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-1.5 text-sm text-text-secondary">
        <span className="font-semibold text-text">
          {t("Sample Affected Entries (Showing")}{" "}{records.length}{" "}{t("of")}{" "}{item.affected_count})
        </span>
        <span>{t("Direct correction available via the “")}{item.action || t("Resolve")}{t("” button.")}</span>
      </div>
      <div className="max-h-60 overflow-auto rounded-sm border border-ink-100">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {(facilities ? ["Facility ID", "Facility Name", "Location / Field"] : ["Record ID", "Facility", "Year", "Process Type", "Details"]).map((h) => (
                <th key={h} scope="col" className={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.map((s: any, i: number) => (
              <tr key={i}>
                {facilities ? (
                  <>
                    <td className={cn(td, "font-mono font-semibold")}>#{s.id}</td>
                    <td className={td}>
                      <strong>{s.name}</strong>
                    </td>
                    <td className={td}>{s.location || "-"}</td>
                  </>
                ) : (
                  <>
                    <td className={cn(td, "font-mono font-semibold")}>#{s.id}</td>
                    <td className={td}>{s.facility || (s.facility_id ? `Facility #${s.facility_id}` : t("Unassigned Boundary"))}</td>
                    <td className={td}>{s.year || "-"}</td>
                    <td className={td}>
                      <Badge tone="info">{s.process_type || s.process || "—"}</Badge>
                    </td>
                    <td className={td}>
                      {s.fuel && <span className="mr-2">{t("Fuel:")}{" "}<strong>{s.fuel}</strong></span>}
                      {s.quantity !== undefined && <span>{t("Qty:")}{" "}<strong>{s.quantity === null ? t("None") : s.quantity}</strong></span>}
                      {s.co2e !== undefined && <span className="ml-2">{t("CO₂e:")}{" "}<strong>{s.co2e === null ? t("None") : s.co2e}</strong></span>}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface FindingCardProps {
  item: DiagnosticItem;
  type: string;
  expanded: boolean;
  onToggle: () => void;
  onAction: (item: DiagnosticItem) => void;
}

const FindingCard: React.FC<FindingCardProps> = ({ item, type, expanded, onToggle, onAction }) => {
  const hasSamples = Boolean(item.sample_records && item.sample_records.length > 0);
  return (
    <div className={cn("qa-issue-item flex flex-col gap-3 rounded-md border border-border border-l-4 bg-surface px-4 py-3.5", FINDING_RULE[type], type)}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2.5">
            {FINDING_ICON[type]}
            <span className="text-md font-semibold text-text">{item.title}</span>
            <Badge tone={IMPACT_TONE[(item.impact || "low").toLowerCase()] || "neutral"}>{item.impact ? `${item.impact} Impact` : t("Optimization")}</Badge>
            {item.affected_count > 0 && <Badge>{item.affected_count} {item.id === "unused_facilities" ? t("facilities") : t("records")}</Badge>}
          </div>
          <p className="m-0 text-base leading-snug text-text-secondary">{item.description}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {hasSamples && (
            <Button variant="secondary" size="sm" aria-expanded={expanded} onClick={onToggle} title={expanded ? t("Collapse preview") : t("Inspect sample records")}>
              <Eye className="size-3.5" aria-hidden="true" />
              {expanded ? t("Hide") : `Inspect (${item.sample_records?.length ?? 0})`}
              {expanded ? <ChevronUp className="size-3.5" aria-hidden="true" /> : <ChevronDown className="size-3.5" aria-hidden="true" />}
            </Button>
          )}
          <Button size="sm" onClick={() => onAction(item)}>
            {item.action || t("Resolve")} <ArrowRight className="size-3.5" aria-hidden="true" />
          </Button>
        </div>
      </div>
      {expanded && hasSamples && <SampleTable item={item} />}
    </div>
  );
};

export interface DiagnosticsPanelProps {
  healthScore: number;
  completeness: number;
  dim: Record<string, number>;
  issues: DiagnosticItem[];
  warnings: DiagnosticItem[];
  suggestions: DiagnosticItem[];
  expandedId: string | null;
  onExpand: (id: string | null) => void;
  onAction: (item: DiagnosticItem) => void;
}

/** Completeness bars and the categorised list of diagnostic findings. */
export const DiagnosticsPanel: React.FC<DiagnosticsPanelProps> = ({ healthScore, completeness, dim, issues, warnings, suggestions, expandedId, onExpand, onAction }) => {
  const h = health(healthScore);
  const total = issues.length + warnings.length + suggestions.length;
  const groups: [DiagnosticItem[], string][] = [
    [issues, "critical"],
    [warnings, "warning"],
    [suggestions, "info"],
  ];
  return (
    <Card className="flex flex-col gap-6 p-7">
      <div className="rounded-lg border border-border bg-ink-50 p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="m-0 text-lg font-bold text-text">{t("Inventory Completeness by Attribute")}</h3>
            <p className="m-0 mt-1 text-sm text-text-secondary">{t("Evaluates key GHG Protocol and ISO 14064 required fields across all reported records.")}</p>
          </div>
          <div className="text-right">
            <span className={cn("text-2xl font-extrabold", h.text)}>{completeness}%</span>
            <div className="text-xs font-semibold uppercase text-text-secondary">{t("Overall Completeness")}</div>
          </div>
        </div>
        <div className="flex flex-col gap-4">
          {DIM_BARS.map((d) => (
            <div key={d.key} className="flex flex-col gap-1.5">
              <div className="flex justify-between text-base font-medium text-ink-700">
                <span>{d.label}</span>
                <strong>{dim[d.key]}%</strong>
              </div>
              <div role="progressbar" aria-label={d.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={dim[d.key]} className="h-2 overflow-hidden rounded-full bg-ink-200">
                <div className={cn("h-full rounded-full transition-[width] duration-500", d.bar)} style={{ width: `${dim[d.key]}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="m-0 mb-3.5 text-lg font-bold text-text">{t("Diagnostic Findings & Action Items (")}{total})</h3>
        <div className="flex flex-col gap-3">
          {groups.map(([list, type]) => list.map((item) => <FindingCard key={`${type}-${item.id}`} item={item} type={type} expanded={expandedId === item.id} onToggle={() => onExpand(expandedId === item.id ? null : item.id)} onAction={onAction} />))}
          {total === 0 && (
            <Banner tone="success" title={t("All Quality Gates Passed")}>
              {t("Your inventory meets 100% of data completeness and validity requirements.")}
            </Banner>
          )}
        </div>
      </div>
    </Card>
  );
};

const SCOPES: { key: string; total: string; label: string; icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>; tone: BadgeTone; note: string }[] = [
  { key: "scope1", total: "s1_total_tco2e", label: t("Scope 1"), icon: Flame, tone: "success", note: "Combustion, flaring, vented & fugitive sources" },
  { key: "scope2", total: "s2_total_tco2e", label: t("Scope 2"), icon: Zap, tone: "info", note: "Purchased electricity & grid emission factors" },
  { key: "scope3", total: "s3_total_tco2e", label: t("Scope 3"), icon: Layers, tone: "brand", note: "Upstream & downstream category estimations" },
];

export interface UncertaintyPanelProps {
  uncertainty: {
    scope1?: number;
    scope2?: number;
    scope3?: number;
    s1_total_tco2e?: number;
    s2_total_tco2e?: number;
    s3_total_tco2e?: number;
    [key: string]: any;
  };
}

/** IPCC Tier 1 error-propagation explainer plus one uncertainty card per scope. */
export const UncertaintyPanel: React.FC<UncertaintyPanelProps> = ({ uncertainty }) => (
  <Card className="flex flex-col gap-6 p-7">
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-ink-50 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="m-0 text-lg font-bold text-text">{t("IPCC Tier 1 Error Propagation (Square Root of Sum of Squares)")}</h3>
          <p className="m-0 mt-1 text-sm text-text-secondary">{t("Complies with ISO 14064-1:2018 §7.5 and GHG Protocol Corporate Standard Chapter 11.")}</p>
        </div>
        <Badge tone="brand">{t("95% Confidence Interval (k=2)")}</Badge>
      </div>
      <code className="block rounded-md bg-ink-900 px-5 py-4 font-mono text-sky-400">U_total = √[ (U₁ · E₁)² + (U₂ · E₂)² + (U₃ · E₃)² ] / ( E₁ + E₂ + E₃ )</code>
      <p className="m-0 text-sm leading-normal text-text-secondary">
        {t("Each scope uncertainty is propagated from activity data precision and emission factor variance. Higher granularity (e.g. facility-specific continuous monitoring or Tier 3 custom factors) reduces total uncertainty.")}
      </p>
    </div>
    <div className="grid gap-4 md:grid-cols-3">
      {SCOPES.map(({ key, total, label, icon: Icon, tone, note }) => (
        <div key={key} className="flex flex-col gap-3 rounded-md border border-border bg-surface p-5">
          <div className="flex items-center justify-between">
            <Badge tone={tone}>{label}</Badge>
            <Icon className="size-4 text-text-secondary" aria-hidden="true" />
          </div>
          <div className="text-2xl font-extrabold text-text">±{((uncertainty[key] || 0) * 100).toFixed(2)}%</div>
          <div className="text-sm text-text-secondary">
            {t("Total Audited:")}{" "}<strong className="text-text">{(uncertainty[total] || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}{" "}{t("tCO₂e")}</strong>
          </div>
          <div className="border-t border-ink-100 pt-2 text-xs text-text-secondary">{note}</div>
        </div>
      ))}
    </div>
  </Card>
);
