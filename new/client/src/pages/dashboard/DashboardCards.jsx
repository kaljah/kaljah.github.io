import React from "react";
import { ArrowRight, BarChart3, ChevronDown, ChevronUp, Clock, Eye, EyeOff, Hexagon } from "lucide-react";
import { Badge, Banner, Button, Card, CardHeader, Switch } from "../../ui";
import { cn } from "../../ui/cn";
import { PieChart as PieChartWrapper, LineChart as LineChartWrapper } from "../../components/charts";
import { formatCompactNumber } from "../../utils/formatters";

/** Pending records notice with the "preview pending data" switch and a review shortcut for approvers. */
export const PendingBanner = ({ count, co2e, includePending, onIncludePending, canReview, onReview }) => (
  <Banner
    tone="warning"
    className="items-center bg-surface"
    title={includePending ? "Previewing pending & verified emissions" : "Pending records awaiting review"}
    actions={
      <>
        <Switch
          label={
            <span className="flex items-center gap-1.5 text-sm font-semibold text-text-secondary">
              {includePending ? <Eye className="size-4" aria-hidden="true" /> : <EyeOff className="size-4" aria-hidden="true" />}
              Preview pending data
            </span>
          }
          checked={includePending}
          onChange={(e) => onIncludePending(e.target.checked)}
        />
        {canReview && (
          <Button size="sm" onClick={onReview} title="Go to Manage Data to review pending records">
            Review now <ArrowRight className="size-3.5" aria-hidden="true" />
          </Button>
        )}
      </>
    }
  >
    <div className="flex flex-wrap items-center gap-2">
      <Badge tone="warning">
        <Clock className="size-3" aria-hidden="true" /> {includePending ? "Live preview active" : "Pending approval"}
      </Badge>
      <span className="text-sm text-text-secondary">
        There are <strong>{count.toLocaleString()}</strong> emission records
        {co2e > 0 && <strong className="mx-1 tabular-nums text-warning-fg">{co2e.toLocaleString()} tCO₂e</strong>}
        pending approval.{" "}
        {includePending
          ? "Dashboard metrics now combine pending drafts and verified records."
          : "Official metrics currently display verified records only."}
      </span>
    </div>
  </Banner>
);

/** Emissions trend with the five-year forecast; the compare toggle switches to one line per facility. */
export const TrendCard = ({ data, lines, compare, onCompare }) => (
  <Card className="min-w-0">
    <CardHeader
      title="Emissions trend & projection"
      description="Historical inventory trajectory with 5-year predictive forecast"
      actions={
        <Button variant="secondary" size="sm" aria-pressed={compare} onClick={onCompare} className="print:hidden">
          <BarChart3 className="size-4" aria-hidden="true" />
          {compare ? "Standard view" : "Compare regions"}
        </Button>
      }
    />
    <div className="relative h-[360px] w-full min-w-0">
      <LineChartWrapper data={data} xKey="year" lines={lines} height={360} />
    </div>
  </Card>
);

export const DonutCard = ({ title, data }) => (
  <Card className="min-w-0">
    <h3 className="m-0 mb-3 text-md font-bold text-ink-800">{title}</h3>
    <div className="relative h-[170px] w-full min-w-0">
      <PieChartWrapper data={data} height={170} innerRadius={50} outerRadius={75} />
    </div>
  </Card>
);

const SBTI_SERIES = (label) => [
  { dataKey: "actual", name: "Actual Verified Emissions", color: "#3b82f6", strokeWidth: 3 },
  { dataKey: "sbti_target", name: label || "Linear Target", color: "#10b981", strokeDasharray: "5 5", strokeWidth: 2 },
  { dataKey: "bau_projection", name: "Business as Usual (+1.5%/yr)", color: "#ef4444", strokeDasharray: "3 3", strokeWidth: 2 },
];

export const SbtiCard = ({ sbti, onOpen }) => (
  <Card className="p-6">
    <CardHeader
      title={sbti.pathway_label || "Decarbonization trajectory"}
      description={`Progress monitoring against corporate Net-Zero targets from Base Year ${sbti.base_year} to Target Year ${sbti.target_year}`}
      actions={
        <Button variant="secondary" onClick={onOpen}>
          View full SBTi dashboard <ArrowRight className="size-4" aria-hidden="true" />
        </Button>
      }
    />
    <div className="h-[320px] w-full">
      {/* BUG-059: the target line is labelled with the stored pathway */}
      <LineChartWrapper data={sbti.trajectory} xAxisKey="year" series={SBTI_SERIES(sbti.pathway_label)} height={320} />
    </div>
  </Card>
);

/** Activity → division → region cards. Collapsed state hides the body except when printing. */
export const CategoricalCard = ({ collapsed, onToggle, activities, hierarchy }) => (
  <Card>
    <button
      type="button"
      aria-expanded={!collapsed}
      onClick={onToggle}
      className={cn(
        "flex w-full cursor-pointer items-center justify-between gap-3 border-0 bg-transparent p-0 text-left",
        !collapsed && "mb-6",
      )}
    >
      <span className="flex flex-wrap items-center gap-3">
        <span className="text-lg font-semibold text-text">Categorical emissions overview</span>
        <Badge className="gap-1.5 px-2.5 py-1 text-sm">
          <Hexagon className="size-3.5" aria-hidden="true" /> Activity → Division → Region
        </Badge>
      </span>
      {collapsed ? <ChevronDown className="size-[18px] text-ink-500" aria-hidden="true" /> : <ChevronUp className="size-[18px] text-ink-500" aria-hidden="true" />}
    </button>
    <div className={cn(collapsed && "hidden print:block")}>
      <div className="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        {activities.map((opt) => (
          <div key={opt.value} className="flex flex-col gap-4">
            <h4 className="m-0 w-fit border-b-2 border-brand-500 pb-1.5 text-base font-bold text-text">{opt.label}</h4>
            {hierarchy[opt.value] ? (
              Object.entries(hierarchy[opt.value].divisions).map(([division, data]) => (
                <div key={division} className="rounded-lg border border-border bg-surface/60 p-3.5">
                  <h5 className="m-0 mb-3 text-sm font-bold uppercase tracking-wide text-text-secondary">{division}</h5>
                  <ul className="m-0 flex list-none flex-col gap-2 p-0">
                    {data.regions.map((reg, i) => (
                      <li key={i} className="rounded-md border border-border bg-surface px-3 py-2.5 transition-shadow hover:shadow-sm">
                        <div className="mb-1 text-sm font-semibold text-text">
                          {reg.region} {reg.field && <span className="font-medium text-text-secondary">- {reg.field}</span>}
                        </div>
                        <div className="text-base font-bold tabular-nums text-text">
                          {formatCompactNumber(reg.total_emissions)} <span className="text-xs font-normal text-text-secondary">tCO₂e</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            ) : (
              <p className="m-0 py-2 text-sm italic text-text-secondary">No emissions data for this activity</p>
            )}
          </div>
        ))}
      </div>
    </div>
  </Card>
);
