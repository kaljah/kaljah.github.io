import React from "react";
import { BookOpen, ChevronDown, ChevronRight, ChevronUp, Plus } from "lucide-react";
import { Button, Card } from "../../ui";
import { cn } from "../../ui/cn";
import { activateOnKey } from "../../utils/a11yKeys";
import { formatCompactNumber as fmt } from "../../utils/formatters";

const INDENT = { 0: "pl-4", 1: "pl-7", 2: "pl-9", 3: "pl-11" } as const;

interface RowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  label: React.ReactNode;
  value: React.ReactNode;
  level?: 0 | 1 | 2 | 3;
  tone?: "summary" | "detail" | "sub" | "total" | "net";
}

// One table row: label cell and right-aligned number cell. Tone picks the row emphasis.
const Row: React.FC<RowProps> = ({ label, value, level = 0, tone = "detail", className, ...props }) => (
  <tr
    className={cn(
      "border-b border-ink-100 text-base",
      tone === "summary" && "font-bold text-text",
      tone === "detail" && "text-text-secondary",
      tone === "sub" && "bg-ink-50/50 text-sm text-text-secondary",
      tone === "total" && "bg-ink-50 font-bold text-text",
      tone === "net" && "bg-ink-50 font-bold text-success-fg",
      className,
    )}
    {...props}
  >
    <td className={cn("py-2.5 pr-4", INDENT[level])}>{label}</td>
    <td className="py-2.5 pr-4 text-right tabular-nums">{value}</td>
  </tr>
);

const Caret: React.FC<{ open?: boolean }> = ({ open }) => (
  <ChevronRight className={cn("mr-1 inline size-3.5 align-text-bottom text-text-secondary transition-transform", open && "rotate-90")} aria-hidden="true" />
);

const LIBRARIES = [
  { name: "API Compendium: 2021", dot: "bg-blue-500" },
  { name: "ISO 14064-1:2018", dot: "bg-green-500" },
  { name: "GRI 305 Standards", dot: "bg-brand-500" },
];

export interface DetailedBreakdownSectionProps {
  detailedBreakdownCollapsed: boolean;
  expandedActivities: Record<string, boolean>;
  expandedDivisions: Record<string, boolean>;
  flaringData?: any;
  formatActivityName: (act: string) => string;
  getHierarchicalData: Record<string, { total: number; divisions: Record<string, { total: number; regions: { region: string; total_emissions: number }[] }> }>;
  navigate: (to: string, options?: any) => void;
  setDetailedBreakdownCollapsed: (val: boolean) => void;
  stats: {
    scope1?: number;
    scope2?: number;
    scope2Market?: number;
    scope3?: number;
    combustion?: number;
    flaring?: number;
    venting?: number;
    fugitive?: number;
    other?: number;
    mitigation?: number;
    [key: string]: any;
  };
  toggleActivity: (act: string) => void;
  toggleDivision: (div: string) => void;
}

/** Detailed breakdown table (scopes, sources, organizational tree) and the reference-library shortcuts. */
const DetailedBreakdownSection: React.FC<DetailedBreakdownSectionProps> = ({
  detailedBreakdownCollapsed,
  expandedActivities,
  expandedDivisions,
  flaringData,
  formatActivityName,
  getHierarchicalData,
  navigate,
  setDetailedBreakdownCollapsed,
  stats,
  toggleActivity,
  toggleDivision,
}) => {
  const total = (stats.scope1 || 0) + (stats.scope2 || 0) + (stats.scope3 || 0);
  const flaring = flaringData;
  const hasFlaringSplit =
    flaring && (flaring.routine_flaring?.volume_knm3 > 0 || flaring.non_routine_flaring?.volume_knm3 > 0 || flaring.safety_flaring?.volume_knm3 > 0);
  const split: [string, any][] = [
    ["Routine", flaring?.routine_flaring],
    ["Non-Routine", flaring?.non_routine_flaring],
    ["Safety & Purge", flaring?.safety_flaring],
  ];

  return (
    <div className="grid gap-6 [grid-template-columns:8fr_4fr] max-[1200px]:grid-cols-1">
      <Card className={cn("detailed-table-card min-w-0 print:break-inside-avoid print:shadow-none", detailedBreakdownCollapsed && "collapsed-card")}>
        <button
          type="button"
          aria-expanded={!detailedBreakdownCollapsed}
          onClick={() => setDetailedBreakdownCollapsed(!detailedBreakdownCollapsed)}
          className="table-header-row clickable-card-header mb-5 flex w-full cursor-pointer items-center justify-between border-0 bg-transparent p-0 text-left hover:opacity-85"
        >
          <span className="text-lg font-semibold text-text">Detailed breakdown</span>
          {detailedBreakdownCollapsed ? <ChevronDown className="size-[18px] text-ink-500" aria-hidden="true" /> : <ChevronUp className="size-[18px] text-ink-500" aria-hidden="true" />}
        </button>

        <div className={cn("overflow-auto", detailedBreakdownCollapsed && "hidden print:block")}>
          <table className="data-table w-full border-collapse">
            <thead>
              <tr className="bg-ink-50 text-left text-sm font-semibold text-text-secondary">
                <th scope="col" className="py-2.5 pl-4 pr-4">Category / Source</th>
                <th scope="col" className="py-2.5 pr-4 text-right">Results (tCO₂e)</th>
              </tr>
            </thead>
            <tbody>
              <Row tone="summary" label="Scope 1 (Direct)" value={fmt(stats.scope1)} />
              <Row level={1} label="Combustion (stationary & mobile)" value={fmt(stats.combustion)} />
              <Row level={1} label="Flaring" value={fmt(stats.flaring)} />
              {hasFlaringSplit &&
                split.map(([name, part]) => (
                  <Row key={name} tone="sub" level={2} label={`↳ ${name} (${part?.percentage ?? 0}%)`} value={fmt(part?.tco2e ?? 0)} />
                ))}
              <Row level={1} label="Venting" value={fmt(stats.venting)} />
              <Row level={1} label="Equipment Leaks / Fugitives" value={fmt(stats.fugitive)} />
              <Row level={1} label="Other Sources" value={fmt(stats.other)} />
              <Row tone="summary" label="Scope 2 (Indirect - Energy), location-based" value={fmt(stats.scope2)} />
              <Row level={1} label="Scope 2 market-based (contractual instruments; not added to the total)" value={fmt(stats.scope2Market ?? stats.scope2)} />
              <Row tone="summary" label="Scope 3 (Supply Chain)" value={fmt(stats.scope3)} />
              <Row tone="total" label="Total Footprint (Scopes 1+2+3)" value={fmt(total)} />
              <Row tone="net" label="Net Footprint" value={fmt(total - (stats.mitigation || 0))} />

              <tr>
                <td colSpan={2} className="px-4 pb-1.5 pt-5 text-xs font-bold uppercase tracking-wide text-text-secondary">
                  Organizational breakdown
                </td>
              </tr>
              {Object.entries(getHierarchicalData).map(([act, actData]) => (
                <React.Fragment key={act}>
                  <Row
                    tone="summary"
                    className="act-row cursor-pointer hover:bg-ink-50"
                    role="row"
                    tabIndex={0}
                    onKeyDown={activateOnKey}
                    onClick={() => toggleActivity(act)}
                    label={
                      <>
                        <Caret open={expandedActivities[act]} />
                        {formatActivityName(act)}
                      </>
                    }
                    value={fmt(actData.total)}
                  />
                  {expandedActivities[act] &&
                    Object.entries(actData.divisions).map(([div, divData]) => (
                      <React.Fragment key={div}>
                        <Row
                          level={1}
                          className="div-row cursor-pointer hover:bg-ink-50"
                          role="row"
                          tabIndex={0}
                          onKeyDown={activateOnKey}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleDivision(div);
                          }}
                          label={
                            <>
                              <Caret open={expandedDivisions[div]} />
                              {div}
                            </>
                          }
                          value={fmt(divData.total)}
                        />
                        {expandedDivisions[div] &&
                          divData.regions.map((reg, i) => (
                            <Row key={i} tone="sub" level={3} className="reg-row" label={reg.region} value={fmt(reg.total_emissions)} />
                          ))}
                      </React.Fragment>
                    ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="flex flex-col gap-4 self-start p-6">
        <div className="flex items-center justify-between">
          <h3 className="m-0 text-lg font-semibold text-text">Reference libraries</h3>
          <BookOpen className="size-5 text-ink-300" aria-hidden="true" />
        </div>
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {LIBRARIES.map((lib) => (
            <li key={lib.name} className="flex items-center gap-2.5 text-base font-medium text-text">
              <span className={cn("size-2 rounded-full", lib.dot)} aria-hidden="true" />
              <span className="flex-1">{lib.name}</span>
              <ChevronRight className="size-3.5 text-ink-400" aria-hidden="true" />
            </li>
          ))}
        </ul>
        <Button variant="secondary" className="manage-factors-btn w-full border-dashed" onClick={() => navigate("/manage-data", { state: { tab: "factors" } })}>
          <Plus className="size-4" aria-hidden="true" /> Manage Custom Factors
        </Button>
      </Card>
    </div>
  );
};

export default DetailedBreakdownSection;
