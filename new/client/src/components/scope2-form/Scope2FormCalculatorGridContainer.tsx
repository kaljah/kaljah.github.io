import React from "react";
import { Button } from "../../ui";
import { Copy, Eye, Trash2 } from "lucide-react";
import LoadingSpinner from "../LoadingSpinner";
import { UNCERTAINTY_COVERAGE_K } from "../../constants";
import { formatEmission, formatNumber } from "../../utils/formatters";

export interface Scope2Entry {
  id: number | string;
  year: number;
  month?: number;
  facility_id?: number | string;
  source_type: string;
  grid_region?: string;
  division?: string;
  field?: string;
  electricity_kwh?: number;
  heat_mmbtu?: number;
  co2e: number;
  emission_factor?: number | string;
  uncertainty?: number;
  status?: string;
  [key: string]: any;
}

export type Scope2GridEntry = Scope2Entry;

export interface Scope2FormCalculatorGridContainerProps {
  currentPage: number;
  entries: Scope2Entry[];
  facilities: Array<{ id: number | string; name: string }>;
  handleDelete: (id: number | string) => void;
  handleDuplicate: (entry: Scope2Entry) => void;
  handleInspect: (entry: Scope2Entry) => void;
  loadEntries: () => void;
  loadError?: boolean;
  loading?: boolean;
  setCurrentPage: React.Dispatch<React.SetStateAction<number>>;
  setShowWizard: (show: boolean) => void;
  totalPages: number;
}

const Scope2FormCalculatorGridContainer: React.FC<Scope2FormCalculatorGridContainerProps> = ({
  currentPage,
  entries,
  facilities,
  handleDelete,
  handleDuplicate,
  handleInspect,
  loadEntries,
  loadError,
  loading,
  setCurrentPage,
  setShowWizard,
  totalPages,
}) => (
  <div className="calculator-grid-container [background:white] [border-radius:var(--radius-md)] [overflow:hidden] [box-shadow:var(--shadow-xs)] mt-[30px]!">
    <div className="table-controls flex! justify-between! items-center! p-[15px]!">
      <strong className="text-[length:1rem]! text-[color:#374151]!">
        Recent Scope 2 (Electricity) Entries
      </strong>
      <button
        type="button"
        className="action-btn secondary flex! items-center! gap-[8px]! whitespace-nowrap!"
        onClick={() => setShowWizard(true)}
      >
        ↑ Bulk Import (Wizard)
      </button>
    </div>
    <div
      className={`table-scroll-container [max-height:600px]! [overflow-y:auto]!`}
      tabIndex={0}
      role="region"
      aria-label="Entries table"
    >
      <table className="excel-table">
        <thead>
          <tr>
            <th>Period</th>
            <th>Facility</th>
            <th>Source Type</th>
            <th>Grid / Region</th>
            <th>Division / Field</th>
            <th>Consumption / Input</th>
            <th>EF</th>
            <th>Total (tCO₂e)</th>
            <th
              title="Standard Combined Uncertainty (1σ)"
              className="[cursor:help]!"
            >
              CO₂e 1σ (±%)
            </th>
            <th
              title="Expanded Uncertainty (95% Confidence Interval)"
              className="[cursor:help]!"
            >
              CO₂e 95% CI (±%)
            </th>
            <th className="text-center!">Actions</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={11} className="text-center!">
                <LoadingSpinner />
              </td>
            </tr>
          ) : loadError ? (
            <tr>
              <td colSpan={11} className="text-center! p-[40px]! text-[color:var(--danger,_#dc2626)]!">
                Could not load the records.{" "}
                <Button type="button" variant="ghost" onClick={loadEntries}>
                  Retry
                </Button>
              </td>
            </tr>
          ) : entries.length === 0 ? (
            <tr>
              <td
                colSpan={11}
                className="text-center! p-[40px]! text-[color:#9ca3af]!"
              >
                No entries found
              </td>
            </tr>
          ) : (
            entries.map((entry) => {
              const srcLabel =
                ({
                  electricity: "Grid Electricity",
                  indirect_steam: "Indirect Steam / Heat",
                  cogen_allocation: "CHP / Cogen Allocation",
                } as Record<string, string>)[entry.source_type] || entry.source_type;

              let consumptionDisplay = "-";
              if (entry.source_type === "electricity") {
                consumptionDisplay = `${formatNumber(entry.electricity_kwh, 0)} kWh`;
              } else if (entry.source_type === "indirect_steam") {
                consumptionDisplay = entry.heat_mmbtu
                  ? `${formatNumber(entry.heat_mmbtu, 2)} MMBtu`
                  : "-";
              } else if (entry.source_type === "cogen_allocation") {
                consumptionDisplay = `${formatNumber(entry.co2e, 3)} tCO₂e allocated`;
              }

              // a 0 factor (renewable contract) is a value, not a missing factor
              // (a CHP allocation has no factor)
              const efDisplay =
                entry.source_type !== "cogen_allocation" &&
                entry.emission_factor != null &&
                entry.emission_factor !== ""
                  ? formatNumber(entry.emission_factor, 4)
                  : "—";

              return (
                <tr key={entry.id}>
                  <td>
                    {entry.month
                      ? `${entry.year}-${String(entry.month).padStart(2, "0")}`
                      : entry.year}
                  </td>
                  <td className="font-medium!">
                    {facilities.find((f) => f.id === entry.facility_id)?.name ||
                      "Unknown"}
                  </td>
                  <td
                    style={{
                      fontSize: "0.8rem",
                      color:
                        entry.source_type === "electricity"
                          ? "#2e7d32"
                          : entry.source_type === "indirect_steam"
                          ? "#f59e0b"
                          : "#8b5cf6",
                      fontWeight: 600,
                    }}
                  >
                    {srcLabel}
                  </td>
                  <td>{entry.grid_region || "—"}</td>
                  <td className="text-[length:0.8rem]! text-[color:#6b7280]!">
                    {entry.division} / {entry.field}
                  </td>
                  <td>{consumptionDisplay}</td>
                  <td>{efDisplay}</td>
                  <td className="text-[color:#1d4ed8]! font-semibold!">
                    {formatEmission(entry.co2e, 3)}
                  </td>
                  <td className="text-[color:#6b7280]! text-[length:0.85rem]!">
                    {entry.uncertainty != null
                      ? `${formatNumber(entry.uncertainty * 100, 1)}%`
                      : "—"}
                  </td>
                  <td className="text-[color:#6b7280]! text-[length:0.85rem]!">
                    {entry.uncertainty != null
                      ? `${formatNumber(
                          entry.uncertainty * UNCERTAINTY_COVERAGE_K * 100,
                          1,
                        )}%`
                      : "—"}
                    {entry.status === "Draft" ? (
                      <span className="ml-[8px]! text-[length:0.65rem]! bg-[color:#fee2e2]! text-[color:#b91c1c]! p-[2px_6px]! rounded-[4px]! font-semibold!">
                        Draft
                      </span>
                    ) : entry.status === "Pending Approval" ||
                      entry.status === "Pending" ? (
                      <span className="ml-[8px]! text-[length:0.65rem]! bg-[color:#fef3c7]! text-[color:#d97706]! p-[2px_6px]! rounded-[4px]! font-semibold!">
                        Pending
                      </span>
                    ) : (
                      <span className="ml-[8px]! text-[length:0.65rem]! bg-[color:#dcfce7]! text-[color:#15803d]! p-[2px_6px]! rounded-[4px]! font-semibold!">
                        Verified
                      </span>
                    )}
                  </td>
                  <td className="text-center!">
                    <div className="flex! justify-center! gap-[8px]!">
                      <button
                        type="button"
                        className="icon-button text-[color:#1d4ed8]!"
                        onClick={() => handleInspect(entry)}
                        title="Inspect Calculation Details"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        type="button"
                        className="icon-button"
                        onClick={() => handleDuplicate(entry)}
                        title="Duplicate"
                      >
                        <Copy size={16} />
                      </button>
                      <button
                        type="button"
                        className="icon-button delete"
                        onClick={() => handleDelete(entry.id)}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
        <tfoot>
          <tr className={`[background-color:#f9fafb]! [font-weight:bold]!`}>
            <td colSpan={7} className="text-right! pr-[15px]!">
              Total (Page):
            </td>
            <td className="text-[color:#1d4ed8]!">
              {formatNumber(
                entries.reduce((sum, e) => sum + (e.co2e || 0), 0),
                3,
              )}
            </td>
            <td colSpan={3}></td>
          </tr>
        </tfoot>
      </table>
    </div>
    <div className="pagination-controls p-[15px]! [border-top:1px_solid_#e5e7eb]! flex! justify-center! gap-[20px]! items-center!">
      <button
        type="button"
        className="action-btn secondary"
        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
        disabled={currentPage === 1}
      >
        Previous
      </button>
      <span className="text-[length:0.9rem]! text-[color:#4b5563]!">
        Page {currentPage} of {totalPages}
      </span>
      <button
        type="button"
        className="action-btn secondary"
        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
        disabled={currentPage === totalPages}
      >
        Next
      </button>
    </div>
  </div>
);

export default Scope2FormCalculatorGridContainer;
