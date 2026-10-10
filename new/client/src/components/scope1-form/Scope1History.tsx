import React from "react";
import { Button, Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { Eye, Trash2 } from "lucide-react";
import api from "../../api";
import { formatEmission, formatNumber } from "../../utils/formatters";
import { PROCESS_TYPES, factorTypeLabel, processLabel } from "./shared";
import { t } from "../../i18n";

export interface Scope1HistoryEntry {
  id: string | number;
  year?: number | string;
  month?: number | string;
  activity?: string;
  facility_name?: string;
  region?: string;
  division?: string;
  field?: string;
  group_name?: string;
  group?: string;
  equipment_id?: string;
  process?: string;
  process_type?: string;
  fuel?: string;
  fuel_type?: string;
  activity_data_label?: string;
  factor_source?: string;
  custom_factor_id?: any;
  amount?: number | string;
  quantity?: number | string;
  unit?: string;
  co2_emissions?: number;
  ch4_emissions?: number;
  n2o_emissions?: number;
  co2e_total?: number;
  status?: string;
  uncertainty_co2?: number | null;
  uncertainty_ch4?: number | null;
  uncertainty_n2o?: number | null;
  [key: string]: any;
}

export interface Scope1HistoryProps {
  currentPage: number;
  entries: Scope1HistoryEntry[];
  exportToCSV: (rows: any[], filename: string) => void;
  facetYears: Array<string | number>;
  filterProcess: string;
  filterSearch: string;
  filterYear: string;
  handleDelete: (id: string | number) => void;
  handleInspect: (entry: Scope1HistoryEntry) => void;
  loading: boolean;
  setCurrentPage: React.Dispatch<React.SetStateAction<number>>;
  setFilterProcess: (val: string) => void;
  setFilterSearch: (val: string) => void;
  setFilterYear: (val: string) => void;
  setImportModal: React.Dispatch<React.SetStateAction<{ isOpen: boolean; type?: string }>>;
  setShowUncertainty: React.Dispatch<React.SetStateAction<boolean>>;
  showUncertainty: boolean;
  toast: { error: (msg: string) => void; [key: string]: any };
  totalPages: number;
}

// Extracted from Scope1Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
export const Scope1History: React.FC<Scope1HistoryProps> = ({
  currentPage,
  entries,
  exportToCSV,
  facetYears,
  filterProcess,
  filterSearch,
  filterYear,
  handleDelete,
  handleInspect,
  loading,
  setCurrentPage,
  setFilterProcess,
  setFilterSearch,
  setFilterYear,
  setImportModal,
  setShowUncertainty,
  showUncertainty,
  toast,
  totalPages,
}) => (
  <div className="calculator-grid-container [background:white] [border-radius:var(--radius-md)] [overflow:hidden] [box-shadow:var(--shadow-xs)] mt-[30px]!">
    {/* Filter bar */}
    <div className="flex! gap-[10px]! flex-wrap! items-center! mb-[14px]!">
      <strong className="text-[length:0.95rem]! mr-[4px]!">{t("Recent Activity (Scope 1)")}</strong>
      <div className="flex-1!" />
      <Input
        type="text"
        placeholder={t("Search...")}
        value={filterSearch}
        onChange={(e) => {
          setFilterSearch(e.target.value);
          setCurrentPage(1);
        }}
        className="w-[160px]! p-[6px_10px]! text-[length:0.82rem]!"
      />
      <NativeSelect
        aria-label={t("Filter by year")}
        value={filterYear}
        onChange={(e) => {
          setFilterYear(e.target.value);
          setCurrentPage(1);
        }}
        className="component-select w-[100px]! text-[length:0.82rem]!"
      >
        <option value="">{t("All Years")}</option>
        {/* BUG-095: options come from the server facets, not from the 10 rows of the current page */}
        {facetYears.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </NativeSelect>
      <NativeSelect
        aria-label={t("Filter by process")}
        value={filterProcess}
        onChange={(e) => {
          setFilterProcess(e.target.value);
          setCurrentPage(1);
        }}
        className="component-select w-[140px]! text-[length:0.82rem]!"
      >
        <option value="">{t("All Processes")}</option>
        {Object.keys(PROCESS_TYPES).map((p) => {
          const pDef = (PROCESS_TYPES as Record<string, any>)[p];
          const pLabel = typeof pDef === "string" ? pDef : pDef?.label || p;
          return (
            <option key={p} value={p}>
              {pLabel}
            </option>
          );
        })}
      </NativeSelect>
      {(filterYear || filterProcess || filterSearch) && (
        <Button
          variant="ghost"
          type="button"
          onClick={() => {
            setFilterYear("");
            setFilterProcess("");
            setFilterSearch("");
            setCurrentPage(1);
          }}
          className="text-[length:0.8rem]! p-[5px_10px]! text-[color:var(--text-secondary)]!"
        >
          {t("Clear")}
        </Button>
      )}
      <button
        className="action-btn bg-[color:var(--color-green-500)]! p-[6px_14px]! text-[length:0.82rem]! whitespace-nowrap!"
        onClick={async () => {
          // BUG-095: export every matching record (server-side filters), not just the visible page.
          // S1K-F13: the server caps one request at 5,000 records ("limit=all" silently returned
          // 5,000 of 83,147), so the export pages through the whole result.
          try {
            const rows: any[] = [];
            const PAGE = 5000;
            let total = Infinity;
            while (rows.length < total) {
              const res = await api.get("/emissions", {
                params: {
                  scope: "1",
                  limit: PAGE,
                  offset: rows.length,
                  ...(filterYear && { year: filterYear }),
                  ...(filterProcess && { process: filterProcess }),
                  ...(filterSearch && { search: filterSearch }),
                },
              });
              const page = res.data?.emissions || res.data?.data || (Array.isArray(res.data) ? res.data : []);
              total = Number(res.data?.total ?? res.headers?.["x-total-count"] ?? rows.length + page.length);
              if (!page.length) break;
              rows.push(...page);
            }
            exportToCSV(rows, "scope1_export.csv");
          } catch (err: any) {
            toast.error(err.response?.data?.error || t("Export failed"));
          }
        }}
      >
        {t("↓ Export CSV")}
      </button>
      <button
        className="action-btn bg-[color:var(--color-green-500)]! p-[6px_14px]! text-[length:0.82rem]! whitespace-nowrap!"
        onClick={() => setImportModal({ isOpen: true, type: "activity" })}
      >
        {t("↑ Bulk Import (Wizard)")}
      </button>
      <button
        type="button"
        className="action-btn secondary p-[6px_14px]! text-[length:0.82rem]! whitespace-nowrap!"
        aria-pressed={showUncertainty}
        onClick={() => setShowUncertainty((v) => !v)}
      >
        {showUncertainty ? t("Hide") : t("Show")}{" "}{t("uncertainty columns")}
      </button>
    </div>
    <div className="table-scroll-container" tabIndex={0} role="region" aria-label={t("Entries table")}>
      <table className={`excel-table${showUncertainty ? "" : " hide-uncertainty"}`}>
        <thead>
          <tr>
            <th>{t("Period")}</th>
            <th>{t("Activity")}</th>
            <th>{t("Region")}</th>
            <th>{t("Division")}</th>
            <th>{t("Field")}</th>
            <th>{t("Emission Source")}</th>
            <th>{t("Equipment ID")}</th>
            <th>{t("Process")}</th>
            <th>Activity/Fuel</th>
            <th>{t("Factor Type")}</th>
            <th>{t("Quantity")}</th>
            <th>{t("CO₂ (t)")}</th>
            <th>{t("CH₄ (t)")}</th>
            <th>N₂O (t)</th>
            <th>{t("Total (tCO₂e)")}</th>
            <th className="text-center!" title={t("Standard Combined Uncertainty (1σ)")}>
              {t("CO₂ 1σ (±%)")}
            </th>
            <th className="text-center!" title={t("Standard Combined Uncertainty (1σ)")}>
              {t("CH₄ 1σ (±%)")}
            </th>
            <th className="text-center!" title={t("Standard Combined Uncertainty (1σ)")}>
              N₂O 1σ (±%)
            </th>
            <th className="text-center!" title={t("Expanded Uncertainty (95% Confidence Interval, k=2)")}>
              {t("CO₂ 95%CI (±%)")}
            </th>
            <th className="text-center!" title={t("Expanded Uncertainty (95% Confidence Interval, k=2)")}>
              {t("CH₄ 95%CI (±%)")}
            </th>
            <th className="text-center!" title={t("Expanded Uncertainty (95% Confidence Interval, k=2)")}>
              {t("N₂O 95%CI (±%)")}
            </th>
            <th className="text-center!">{t("Actions")}</th>
          </tr>
        </thead>
        <tbody>
          {(() => {
            const filteredEntries = entries.filter((entry) => {
              const s = filterSearch.toLowerCase();
              const matchSearch =
                !s ||
                (entry.activity || "").toLowerCase().includes(s) ||
                (entry.equipment_id || "").toLowerCase().includes(s) ||
                (entry.fuel || entry.fuel_type || "").toLowerCase().includes(s) ||
                (entry.group || "").toLowerCase().includes(s) ||
                (entry.division || "").toLowerCase().includes(s);
              const matchYear = !filterYear || entry.year?.toString() === filterYear;
              const matchProcess = !filterProcess || (entry.process || entry.process_type) === filterProcess;
              return matchSearch && matchYear && matchProcess;
            });
            if (filteredEntries.length === 0)
              return (
                <tr>
                  <td colSpan={22} className="text-center! text-[color:var(--text-secondary)]! p-[30px]!">
                    {entries.length === 0
                      ? loading
                        ? t("Loading…")
                        : t("No entries yet")
                      : t("No results match your filters")}
                  </td>
                </tr>
              );
            return filteredEntries.map((entry) => {
              const factorType = factorTypeLabel(entry);
              return (
                <tr key={entry.id}>
                  <td>{entry.month ? `${entry.year}-${String(entry.month).padStart(2, "0")}` : entry.year}</td>
                  <td>{entry.activity || "-"}</td>
                  <td>{entry.facility_name || entry.region || "-"}</td>
                  <td>{entry.division || "-"}</td>
                  <td>{entry.field || "-"}</td>
                  <td>{entry.group_name || entry.group || "-"}</td>
                  <td>{entry.equipment_id || "-"}</td>
                  <td>
                    {processLabel(entry)}
                  </td>
                  <td>{entry.fuel || entry.fuel_type || entry.activity_data_label || "-"}</td>
                  <td className={`[font-weight:500]! ${factorType === "Default" ? "[color:var(--color-green-700)]!" : "[color:var(--color-blue-700)]!"}`}>
                    {factorType}
                  </td>
                  <td>
                    {(entry.amount ?? entry.quantity) != null && (entry.amount ?? entry.quantity) !== ""
                      ? `${formatNumber(entry.amount ?? entry.quantity, 2)} ${entry.unit || ""}`
                      : "-"}
                  </td>
                  <td>{formatEmission(entry.co2_emissions || 0, 3)}</td>
                  <td>{formatEmission(entry.ch4_emissions || 0, 5)}</td>
                  <td>{formatEmission(entry.n2o_emissions || 0, 5)}</td>
                  <td className="text-[color:var(--color-link)]! font-semibold!">
                    {formatEmission(entry.co2e_total, 3)}
                    {/* BUG-092: every record shows its maker-checker status */}
                    {entry.status && (
                      <span
                        title={`Status: ${entry.status}`}
                        style={{
                          marginLeft: "8px",
                          fontSize: "0.65rem",
                          padding: "1px 5px",
                          borderRadius: "4px",
                          ...((
                            {
                              Verified: { background: "var(--color-legacy-dcfce7)", color: "var(--color-legacy-166534)" },
                              Pending: { background: "var(--color-legacy-fef9c3)", color: "var(--color-legacy-854d0e)" },
                              Rejected: { background: "var(--color-legacy-fee2e2)", color: "var(--color-red-700)" },
                              Draft: { background: "var(--color-legacy-e0e7ff)", color: "var(--color-legacy-3730a3)" },
                            } as Record<string, React.CSSProperties>
                          )[entry.status] || { background: "var(--color-ink-100)", color: "var(--color-ink-700)" }),
                        }}
                      >
                        {entry.status}
                      </span>
                    )}
                  </td>
                  <td
                    className={`[text-align:center]! [font-size:0.82rem]! ${entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0 ? "[color:var(--color-green-700)]!" : "[color:var(--text-muted)]!"}`}
                    title={t("Standard Combined Uncertainty (1σ)")}
                  >
                    {entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0
                      ? `±${(entry.uncertainty_co2 * 100).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td
                    className={`[text-align:center]! [font-size:0.82rem]! ${entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0 ? "[color:var(--color-blue-700)]!" : "[color:var(--text-muted)]!"}`}
                    title={t("Standard Combined Uncertainty (1σ)")}
                  >
                    {entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0
                      ? `±${(entry.uncertainty_ch4 * 100).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td
                    className={`[text-align:center]! [font-size:0.82rem]! ${entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0 ? "[color:var(--color-violet-700)]!" : "[color:var(--text-muted)]!"}`}
                    title={t("Standard Combined Uncertainty (1σ)")}
                  >
                    {entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0
                      ? `±${(entry.uncertainty_n2o * 100).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td
                    className={`[text-align:center]! [font-size:0.82rem]! ${entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0 ? "[color:var(--color-green-700)]!" : "[color:var(--text-muted)]!"}`}
                    title={t("Expanded Uncertainty (95% Confidence Interval, k=2)")}
                  >
                    {entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0
                      ? `±${(entry.uncertainty_co2 * 200).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td
                    className={`[text-align:center]! [font-size:0.82rem]! ${entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0 ? "[color:var(--color-blue-700)]!" : "[color:var(--text-muted)]!"}`}
                    title={t("Expanded Uncertainty (95% Confidence Interval, k=2)")}
                  >
                    {entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0
                      ? `±${(entry.uncertainty_ch4 * 200).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td
                    className={`[text-align:center]! [font-size:0.82rem]! ${entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0 ? "[color:var(--color-violet-700)]!" : "[color:var(--text-muted)]!"}`}
                    title={t("Expanded Uncertainty (95% Confidence Interval, k=2)")}
                  >
                    {entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0
                      ? `±${(entry.uncertainty_n2o * 200).toFixed(0)}%`
                      : "—"}
                  </td>
                  <td className="text-center! whitespace-nowrap!">
                    <button
                      className="icon-button text-[color:var(--color-blue-700)]! mr-[6px]!"
                      onClick={() => handleInspect(entry)}
                      title={t("Inspect Calculation Details")}
                    >
                      <Eye size={16} />
                    </button>
                    <button
                      className="icon-button text-[color:var(--color-red-700)]!"
                      onClick={() => handleDelete(entry.id)}
                      title={t("Delete")}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              );
            });
          })()}
        </tbody>
        <tfoot>
          <tr className="[background-color:var(--color-legacy-f9fafb)]! [font-weight:bold]!">
            <td colSpan={14} className="text-right! pr-[15px]!">
              {t("Total (")}{filterYear || filterProcess || filterSearch ? t("Filtered") : t("Page")}):
            </td>
            <td className="text-[color:var(--color-link)]!">
              {formatNumber(
                entries
                  .filter((entry) => {
                    const s = filterSearch.toLowerCase();
                    const matchSearch =
                      !s ||
                      (entry.activity || "").toLowerCase().includes(s) ||
                      (entry.equipment_id || "").toLowerCase().includes(s) ||
                      (entry.fuel || entry.fuel_type || "").toLowerCase().includes(s) ||
                      (entry.group || "").toLowerCase().includes(s);
                    return (
                      matchSearch &&
                      (!filterYear || entry.year?.toString() === filterYear) &&
                      (!filterProcess || (entry.process || entry.process_type) === filterProcess)
                    );
                  })
                  .reduce((sum, e) => sum + (e.co2e_total || 0), 0),
                3,
              )}
            </td>
            <td colSpan={7}></td>
          </tr>
        </tfoot>
      </table>
    </div>
    {/* Simplified Pagination */}
    <div className="pagination-controls">
      <button
        className="action-btn secondary"
        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
        disabled={currentPage === 1}
      >
        {t("Previous")}
      </button>
      <span className="text-[color:var(--text-secondary)]!">
        {t("Page")}{" "}{currentPage}{" "}{t("of")}{" "}{totalPages}
      </span>
      <button
        className="action-btn secondary"
        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
        disabled={currentPage === totalPages}
      >
        {t("Next")}
      </button>
    </div>
  </div>
);

export default Scope1History;
