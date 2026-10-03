import React from "react";
import { AlertCircle, RotateCcw, Satellite, Search, Sliders, X } from "lucide-react";
import { Badge, Button, Field, IconButton, Input, NativeSelect, Switch } from "../../ui";
import { cn } from "../../ui/cn";
import { activateOnKey } from "../../utils/a11yKeys";

const selectClass = "h-9 w-full cursor-pointer rounded-md border border-border bg-surface px-2.5 text-sm text-text hover:border-ink-300 focus:border-brand-500";

const SEVERITIES = [
  { id: "all", label: "All" },
  { id: "high", label: "Super-emitters", dot: "bg-red-500" },
  { id: "medium", label: "Moderate", dot: "bg-amber-500" },
  { id: "baseline", label: "Baseline", dot: "bg-green-500" },
];

const DOT = { high: "bg-red-500", medium: "bg-amber-500", low: "bg-green-500", baseline: "bg-green-500" };

const CheckRow = ({ label, title, ...props }) => (
  <label className="inline-flex cursor-pointer items-center gap-1.5 text-sm text-text-secondary">
    <input type="checkbox" className="size-4 accent-brand-500" {...props} />
    <span title={title}>{label}</span>
  </label>
);

const FacilityCard = ({ facility, selected, severity, value, unit, onSelect }) => (
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
          <span className="truncate">{facility.activity || facility.division || "Industrial asset"}</span>
        </div>
      </div>
    </div>
    <div className="flex shrink-0 flex-col items-end">
      <span className="text-base font-extrabold tabular-nums text-text">{value}</span>
      <span className="text-xs font-semibold text-text-secondary">{unit}</span>
    </div>
  </div>
);

/** Left drawer of the emissions map: asset filters, the Sentinel-5P overlay controls and the facility inventory. */
const ExplorerDrawer = ({
  filters,
  onFilters,
  regions,
  years,
  activities,
  count,
  satellite,
  facilities,
  selectedId,
  viewMode,
  getStats,
  getSeverity,
  formatCompact,
  onSelect,
  onReset,
}) => {
  const set = (patch) => onFilters({ ...filters, ...patch });
  return (
    <div className="pointer-events-auto flex size-full flex-col gap-3 overflow-hidden rounded-lg border border-border bg-surface/95 p-3.5 shadow-lg backdrop-blur-lg">
      <div className="flex items-center justify-between">
        <h2 className="m-0 flex items-center gap-2 text-md font-bold text-text">
          <Sliders className="size-4 text-brand-500" aria-hidden="true" /> Assets
        </h2>
        <Badge tone="brand">{count} assets</Badge>
      </div>

      <Field label="Search asset / field">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
          <Input
            className="h-9 pl-9 pr-8 text-sm"
            placeholder="Search name, region, division..."
            value={filters.search}
            onChange={(e) => set({ search: e.target.value })}
          />
          {filters.search && (
            <IconButton label="Clear search" className="absolute right-1 top-1/2 size-7 -translate-y-1/2" onClick={() => set({ search: "" })}>
              <X className="size-3.5" aria-hidden="true" />
            </IconButton>
          )}
        </div>
      </Field>

      <div className="grid grid-cols-2 gap-2">
        <Field label="Region / basin">
          <NativeSelect className={selectClass} value={filters.region} onChange={(e) => set({ region: e.target.value })}>
            <option value="all">All regions</option>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field label="Accounting year">
          <NativeSelect className={selectClass} value={filters.year} onChange={(e) => set({ year: e.target.value })}>
            <option value="all">All years</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </NativeSelect>
        </Field>
      </div>

      <Field label="Activity type">
        <NativeSelect className={selectClass} value={filters.activity} onChange={(e) => set({ activity: e.target.value })}>
          <option value="all">All activities</option>
          {activities.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-1.5 p-0 text-sm font-medium text-text">Anomaly severity</legend>
        <div role="radiogroup" aria-label="Anomaly severity" className="grid grid-cols-2 gap-1.5">
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

      <section className="rounded-md border border-blue-500/30 bg-info-bg p-3" aria-label="Sentinel-5P overlay">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-sm font-bold text-info-fg">
            <Satellite className="size-4" aria-hidden="true" /> Sentinel-5P overlay
          </span>
          <Switch
            id="toggle-sat-layer-checkbox"
            aria-label="Show satellite layer"
            checked={satellite.show}
            onChange={(e) => satellite.onShow(e.target.checked)}
          />
        </div>
        {satellite.show && (
          <div className="mt-2.5 flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-xs font-semibold text-text-secondary">
              Opacity: {Math.round(satellite.opacity * 100)}%
              <input
                id="satellite-opacity-slider"
                type="range"
                min="0.15"
                max="1"
                step="0.05"
                value={satellite.opacity}
                onChange={(e) => satellite.onOpacity(Number(e.target.value))}
                aria-label="Satellite layer opacity"
                className="w-full cursor-pointer accent-blue-700"
              />
            </label>
            <div className="flex justify-between">
              <CheckRow
                label="Severity rings"
                title="Symbol size by emission severity; not a modelled plume"
                checked={satellite.rings}
                onChange={(e) => satellite.onRings(e.target.checked)}
              />
              <CheckRow label="Legend" checked={satellite.legend} onChange={(e) => satellite.onLegend(e.target.checked)} />
            </div>
          </div>
        )}
      </section>

      <div className="flex items-baseline justify-between text-xs font-bold uppercase tracking-wide text-text-secondary">
        <span>Facility inventory</span>
        <span className="font-normal normal-case">Click to inspect</span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
        {facilities.length === 0 ? (
          <div className="flex flex-col items-center gap-2.5 px-2.5 py-8 text-center text-sm text-text-secondary">
            <AlertCircle className="size-5 text-ink-400" aria-hidden="true" />
            <span>No assets match current reconnaissance filters.</span>
            <Button variant="secondary" size="sm" onClick={onReset}>
              <RotateCcw className="size-3" aria-hidden="true" /> Reset all filters
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
