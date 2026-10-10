import React from "react";
import { Button } from "../../ui";
import { Eye, Trash2 } from "lucide-react";
import { UNCERTAINTY_COVERAGE_K } from "../../constants";
import { formatEmission, formatNumber } from "../../utils/formatters";
import { t } from "../../i18n";

export interface Scope3GridEntry {
  id: string | number;
  year?: number | string;
  month?: number | string;
  facility_id?: string | number;
  category?: string;
  sub_category?: string;
  product_type?: string;
  activity_data?: number | string;
  volume?: number | string;
  unit?: string;
  emission_factor?: number | string;
  co2e?: number;
  emissions_tco2e?: number;
  uncertainty?: number | null;
  status?: string;
  [key: string]: any;
}

export interface Scope3FormCalculatorGridContainerProps {
  currentPage: number;
  entries: Scope3GridEntry[];
  facilities: Array<{ id: string | number; name: string; [key: string]: any }>;
  handleDelete: (id: string | number) => void;
  handleInspect: (entry: Scope3GridEntry) => void;
  loadEntries: () => void;
  loadError: boolean | string | null;
  setCurrentPage: React.Dispatch<React.SetStateAction<number>>;
  setShowWizard: (show: boolean) => void;
  totalPages: number;
}

// Extracted from Scope3Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
export const Scope3FormCalculatorGridContainer: React.FC<Scope3FormCalculatorGridContainerProps> = ({
  currentPage,
  entries,
  facilities,
  handleDelete,
  handleInspect,
  loadEntries,
  loadError,
  setCurrentPage,
  setShowWizard,
  totalPages,
}) => (
  <div className="calculator-grid-container [background:white] [border-radius:var(--radius-md)] [overflow:hidden] [box-shadow:var(--shadow-xs)] mt-[30px]!">
    <div className="table-controls flex! justify-between! items-center! p-[15px]!">
      <strong className="text-[length:1rem]! text-[color:var(--color-legacy-374151)]!">{t("Documented Scope 3 Emissions")}</strong>
      <button
        className="action-btn secondary flex! items-center! gap-[8px]! whitespace-nowrap!"
        onClick={() => setShowWizard(true)}
      >
        {t("↑ Bulk Import (Wizard)")}
      </button>
    </div>
    <div className="table-scroll-container" tabIndex={0} role="region" aria-label={t("Entries table")}>
      <table className="excel-table">
        <thead>
          <tr>
            <th>{t("Period")}</th>
            <th>{t("Facility")}</th>
            <th>{t("Category")}</th>
            <th>Activity/Product</th>
            <th>{t("Volume")}</th>
            <th>{t("EF (kg/unit)")}</th>
            <th>{t("Total (tCO₂e)")}</th>
            <th
              title={t("Standard Combined Uncertainty (1σ)")}
              className="[cursor:help]!"
            >
              {t("CO₂e 1σ (±%)")}
            </th>
            <th
              title={t("Expanded Uncertainty (95% Confidence Interval)")}
              className="[cursor:help]!"
            >
              {t("CO₂e 95% CI (±%)")}
            </th>
            <th className="text-center!">{t("Actions")}</th>
          </tr>
        </thead>
        <tbody>
          {loadError ? (
            <tr>
              <td colSpan={10} className="text-center! text-[color:var(--danger,_var(--color-red-600))]!">
                {t("Could not load the records.")}{" "}
                <Button type="button" variant="ghost" onClick={loadEntries}>
                  {t("Retry")}
                </Button>
              </td>
            </tr>
          ) : entries.length === 0 ? (
            <tr>
              <td
                colSpan={10}
                className="text-center! text-[color:var(--text-secondary)]!"
              >
                {t("No entries yet")}
              </td>
            </tr>
          ) : (
            entries.map((entry) => (
              <tr key={entry.id}>
                <td>{entry.month ? `${entry.year}-${String(entry.month).padStart(2, "0")}` : entry.year}</td>
                <td>
                  {facilities.find((f) => f.id === entry.facility_id)
                    ?.name || t("Unknown")}
                </td>
                <td>{entry.category}</td>
                <td>{entry.sub_category || entry.product_type}</td>
                <td>
                  {formatNumber(entry.activity_data || entry.volume, 2)}{" "}
                  {entry.unit}
                </td>
                <td>
                  {/* kg CO2e per activity unit; a supplier-reported total has no factor */}
                  {Number(entry.emission_factor) > 0 ? formatEmission(entry.emission_factor, 4) : "—"}
                </td>
                <td className="text-[color:var(--color-violet-700)]! font-semibold!">
                  {formatEmission(entry.co2e || entry.emissions_tco2e, 3)}
                </td>
                <td className="text-[color:var(--color-legacy-6b7280)]! text-[length:0.85rem]!">
                  {entry.uncertainty != null
                    ? `${formatNumber(entry.uncertainty * 100, 1)}%`
                    : "—"}
                </td>
                <td className="text-[color:var(--color-legacy-6b7280)]! text-[length:0.85rem]!">
                  {entry.uncertainty != null
                    ? `${formatNumber(entry.uncertainty * UNCERTAINTY_COVERAGE_K * 100, 1)}%`
                    : "—"}
                  {entry.status === "Draft" && (
                    <span
                      className="ml-[8px]! text-[length:0.65rem]! bg-[color:var(--color-legacy-fee2e2)]! text-[color:var(--color-red-700)]! p-[1px_5px]! rounded-[4px]!"
                    >
                      {t("Draft")}
                    </span>
                  )}
                </td>
                <td className="text-center! whitespace-nowrap!">
                  <button
                    className="icon-button text-[color:var(--color-blue-700)]! mr-[8px]!"
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
            ))
          )}
        </tbody>
        <tfoot>
          <tr className={`[background-color:var(--color-legacy-f9fafb)]! [font-weight:bold]!`}>
            <td
              colSpan={6}
              className="text-right! pr-[15px]!"
            >
              {t("Total (Page):")}
            </td>
            <td className="text-[color:var(--color-violet-700)]!">
              {formatNumber(
                entries.reduce(
                  (sum, e) => sum + Number(e.co2e || e.emissions_tco2e || 0),
                  0,
                ),
                3,
              )}
            </td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
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

export default Scope3FormCalculatorGridContainer;
