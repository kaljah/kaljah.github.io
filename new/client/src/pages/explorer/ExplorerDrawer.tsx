import React from "react";
import { AlertCircle, RotateCcw, Search, Sliders, X } from "lucide-react";
import { Badge, Button, Field, IconButton, Input, NativeSelect } from "../../ui";
import { cn } from "../../ui/cn";
import { activateOnKey } from "../../utils/a11yKeys";
import { t } from "../../i18n";

const selectClass = "h-9 w-full cursor-pointer rounded-md border border-border bg-surface px-2.5 text-sm text-text hover:border-ink-300 focus:border-brand-500";

const SEVERITIES = [
  { id: "all", label: t("All") },
  { id: "high", label: t("Super-emitters"), dot: "bg-red-500" },
  { id: "medium", label: t("Moderate"), dot: "bg-amber-500" },
  { id: "baseline", label: t("Baseline"), dot: "bg-green-500" },
];

const DOT: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-green-500",
  baseline: "bg-green-500",
};

interface CheckRowProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** text colour; the default is too light on the tinted overlay panel */
  tone?: string;
}

const CheckRow: React.FC<CheckRowProps> = ({ label, title, tone = "text-text-secondary", ...props }) => (
  <label className={`inline-flex cursor-pointer items-center gap-1.5 text-sm ${tone}`}>
    <input type="checkbox" className="size-4 accent-brand-500" {...props} />
    <span title={title}>{label}</span>
  </label>
);

interface FacilityCardProps {
  facility: {
    id: number | string;
    name: string;
    region?: string;
    activity?: string;
    division?: string;
    [key: string]: any;
  };
  selected: boolean;
  severity: string;
  value: React.ReactNode;
  unit: string;
  onSelect: () => void;
}

const FacilityCard: React.FC<FacilityCardProps> = ({ facility, selected, severity, value, unit, onSelect }) => (
  <div
    role="button"
    tabIndex={0}
    onKeyDown={activateOnKey}
    onClick={onSelect}
    aria-pressed={selected}
    className={cn(
      "flex cursor-pointer items-center justify-between gap-2.5 rounded-md border px-3 py-2.5 transition-colors",
      selected ? "border-brand-500 bg-selected-bg" : "border-border bg-surface hover:border-ink-300 hover:bg-ink-50",
    )}
  >
    <div className="flex min-w-0 flex-1 items-center gap-2.5">
      <span className={cn("size-2.5 shrink-0 rounded-full", DOT[severity] ?? "bg-ink-400")} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-bold text-text">{facility.name}</div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-text-secondary">
          {facility.region && <Badge className="px-1.5 py-0">{facility.region}</Badge>}
          <span className="truncate">{facility.activity || facility.division || t("Industrial asset")}</span>
        </div>
      </div>
    </div>
    <div className="flex shrink-0 flex-col items-end">
      <span className="text-base font-extrabold tabular-nums text-text">{value}</span>
      <span className="text-xs font-semibold text-text-secondary">{unit}</span>
    </div>
  </div>
);

export interface ExplorerDrawerProps {
  filters: {
    search: string;
    region: string;
    year: string | number;
    activity: string;
    severity: string;
    [key: string]: any;
  };
  onFilters: (filters: any) => void;
  regions: string[];
  years: (string | number)[];
  activities: string[];
  count: number;
  rings: boolean;
  onRings: (val: boolean) => void;
  facilities: any[];
  selectedId: number | string | null;
  viewMode: string;
  getStats: (id: any) => any;
  getSeverity: (val: number) => string;
  formatCompact: (v: any) => string;
  onSelect: (fac: any) => void;
  onReset: () => void;
}

/** Left drawer of the emissions map: asset filters, map display options and the facility inventory. */
const ExplorerDrawer: React.FC<ExplorerDrawerProps> = ({
  filters,
  onFilters,
  regions,
  years,
  activities,
  count,
  rings,
  onRings,
  facilities,
  selectedId,
  viewMode,
  getStats,
  getSeverity,
  formatCompact,
  onSelect,
  onReset,
}) => {
  const set = (patch: Record<string, any>) => onFilters({ ...filters, ...patch });
  return (
    <div className="pointer-events-auto flex size-full flex-col gap-3 overflow-hidden rounded-lg border border-border bg-surface/95 p-3.5 shadow-lg backdrop-blur-lg">
      <div className="flex items-center justify-between">
        <h2 className="m-0 flex items-center gap-2 text-md font-bold text-text">
          <Sliders className="size-4 text-brand-500" aria-hidden="true" />{" "}{t("Assets")}
        </h2>
        <Badge tone="brand">{count}{" "}{t("assets")}</Badge>
      </div>

      <Field label={t("Search asset / field")}>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
          <Input
            className="h-9 pl-9 pr-8 text-sm"
            placeholder={t("Search name, region, division...")}
            value={filters.search}
            onChange={(e) => set({ search: e.target.value })}
          />
          {filters.search && (
            <IconButton label={t("Clear search")} className="absolute right-1 top-1/2 size-7 -translate-y-1/2" onClick={() => set({ search: "" })}>
              <X className="size-3.5" aria-hidden="true" />
            </IconButton>
          )}
        </div>
      </Field>

      <div className="grid grid-cols-2 gap-2">
        <Field label={t("Region / basin")}>
          <NativeSelect className={selectClass} value={filters.region} onChange={(e) => set({ region: e.target.value })}>
            <option value="all">{t("All regions")}</option>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field label={t("Accounting year")}>
          <NativeSelect className={selectClass} value={filters.year} onChange={(e) => set({ year: e.target.value })}>
            <option value="all">{t("All years")}</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </NativeSelect>
        </Field>
      </div>

      <Field label={t("Activity type")}>
        <NativeSelect className={selectClass} value={filters.activity} onChange={(e) => set({ activity: e.target.value })}>
          <option value="all">{t("All activities")}</option>
          {activities.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-1.5 p-0 text-sm font-medium text-text">{t("Anomaly severity")}</legend>
        <div role="radiogroup" aria-label={t("Anomaly severity")} className="grid grid-cols-2 gap-1.5">
          {SEVERITIES.map((s) => {
            const on = filters.severity === s.id;
            return (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => set({ severity: s.id })}
                className={cn(
                  "inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md border px-2 py-1.5 text-xs font-semibold transition-colors",
                  on ? "border-brand-500 bg-selected-bg text-selected-fg" : "border-border bg-surface text-text-secondary hover:border-ink-300",
                )}
              >
                {s.dot && <span className={cn("size-1.5 rounded-full", s.dot)} aria-hidden="true" />}
                {s.label}
              </button>
            );
          })}
        </div>
      </fieldset>

      <section className="rounded-md border border-border bg-ink-50 p-3" aria-label={t("Map display")}>
        <CheckRow
          label={t("Severity rings")}
          tone="text-ink-700"
          title={t("Symbol size by emission severity; not a modelled plume")}
          checked={rings}
          onChange={(e) => onRings(e.target.checked)}
        />
      </section>

      <div className="flex items-baseline justify-between text-xs font-bold uppercase tracking-wide text-text-secondary">
        <span>{t("Facility inventory")}</span>
        <span className="font-normal normal-case">{t("Click to inspect")}</span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
        {facilities.length === 0 ? (
          <div className="flex flex-col items-center gap-2.5 px-2.5 py-8 text-center text-sm text-text-secondary">
            <AlertCircle className="size-5 text-ink-400" aria-hidden="true" />
            <span>{t("No assets match current reconnaissance filters.")}</span>
            <Button variant="secondary" size="sm" onClick={onReset}>
              <RotateCcw className="size-3" aria-hidden="true" />{" "}{t("Reset all filters")}
            </Button>
          </div>
        ) : (
          facilities.map((fac) => {
            const stats = getStats(fac.id);
            const value = viewMode === "methane" ? stats.total_ch4 || 0 : stats.total_co2e || 0;
            return (
              <FacilityCard
                key={fac.id}
                facility={fac}
                selected={selectedId === fac.id}
                severity={getSeverity(value)}
                value={formatCompact(value)}
                unit={viewMode === "methane" ? "tCH₄" : "tCO₂e"}
                onSelect={() => onSelect(fac)}
              />
            );
          })
        )}
      </div>
    </div>
  );
};

export default ExplorerDrawer;
