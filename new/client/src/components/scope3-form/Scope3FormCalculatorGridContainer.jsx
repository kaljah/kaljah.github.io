import React from "react";
import { Button } from "../../ui";
import { Eye, Trash2 } from "lucide-react";
import { UNCERTAINTY_COVERAGE_K } from "../../constants";
import { formatEmission, formatNumber } from "../../utils/formatters";

// Extracted from Scope3Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope3FormCalculatorGridContainer = ({ currentPage, entries, facilities, handleDelete, handleInspect, loadEntries, loadError, setCurrentPage, setShowWizard, totalPages }) => (
<div className="calculator-grid-container mt-[30px]!">
        <div 
          className="table-controls flex! justify-between! items-center! p-[15px]!"
         
        >
          <strong className="text-[length:1rem]! text-[color:#374151]!">Documented Scope 3 Emissions</strong>
          <button
            className="action-btn secondary flex! items-center! gap-[8px]! whitespace-nowrap!"
            onClick={() => setShowWizard(true)}
           
          >
            ↑ Bulk Import (Wizard)
          </button>
        </div>
        <div className="table-scroll-container">
          <table className="excel-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Facility</th>
                <th>Category</th>
                <th>Activity/Product</th>
                <th>Volume</th>
                <th>EF (kg/unit)</th>
                <th>Total (tCO₂e)</th>
                <th
                  title="Standard Combined Uncertainty (1σ)"
                  style={{ cursor: "help" }}
                >
                  CO₂e 1σ (±%)
                </th>
                <th
                  title="Expanded Uncertainty (95% Confidence Interval)"
                  style={{ cursor: "help" }}
                >
                  CO₂e 95% CI (±%)
                </th>
                <th className="text-center!">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loadError ? (
                <tr>
                  <td colSpan="10" className="text-center! text-[color:var(--danger,_#dc2626)]!">
                    Could not load the records.{" "}
                    <Button type="button" variant="ghost" onClick={loadEntries}>Retry</Button>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td
                    colSpan="10"
                    className="text-center! text-[color:var(--text-secondary)]!"
                  >
                    No entries yet
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.month ? `${entry.year}-${String(entry.month).padStart(2, "0")}` : entry.year}</td>
                    <td>
                      {facilities.find((f) => f.id === entry.facility_id)
                        ?.name || "Unknown"}
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
                    <td className="text-[color:#8b5cf6]! font-semibold!">
                      {formatEmission(entry.co2e || entry.emissions_tco2e, 3)}
                    </td>
                    <td className="text-[color:#6b7280]! text-[length:0.85rem]!">
                      {entry.uncertainty != null
                        ? `${formatNumber(entry.uncertainty * 100, 1)}%`
                        : "—"}
                    </td>
                    <td className="text-[color:#6b7280]! text-[length:0.85rem]!">
                      {entry.uncertainty != null
                        ? `${formatNumber(entry.uncertainty * UNCERTAINTY_COVERAGE_K * 100, 1)}%`
                        : "—"}
                      {entry.status === "Draft" && (
                        <span
                          className="ml-[8px]! text-[length:0.65rem]! bg-[color:#fee2e2]! text-[color:#b91c1c]! p-[1px_5px]! rounded-[4px]!"
                        >
                          Draft
                        </span>
                      )}
                    </td>
                    <td className="text-center! whitespace-nowrap!">
                      <button
                        className="icon-button text-[color:#3b82f6]! mr-[8px]!"
                        onClick={() => handleInspect(entry)}
                       
                        title="Inspect Calculation Details"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        className="icon-button text-[color:#ef4444]!"
                        onClick={() => handleDelete(entry.id)}
                       
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr style={{ backgroundColor: "#f9fafb", fontWeight: "bold" }}>
                <td
                  colSpan="6"
                  className="text-right! pr-[15px]!"
                >
                  Total (Page):
                </td>
                <td className="text-[color:#8b5cf6]!">
                  {formatNumber(
                    entries.reduce(
                      (sum, e) => sum + (e.co2e || e.emissions_tco2e || 0),
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
            Previous
          </button>
          <span className="text-[color:var(--text-secondary)]!">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="action-btn secondary"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      </div>
);

export default Scope3FormCalculatorGridContainer;
