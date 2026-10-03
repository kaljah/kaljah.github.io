import React from "react";
import { ChevronDown, ChevronUp, Radio } from "lucide-react";
import { activateOnKey } from "../../utils/a11yKeys";
import { formatNumber } from "../../utils/formatters";

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityOGMP20Level = ({ globalThreshold, ogmpCollapsed, ogmpSurveys, regionalData, setOgmpCollapsed }) => (
<div className="card ogmp-section">
          <div role="button" tabIndex={0} onKeyDown={activateOnKey}
            className="chart-header"
            onClick={() => setOgmpCollapsed(!ogmpCollapsed)}
            style={{ cursor: "pointer", userSelect: "none" }}
          >
            <div>
              <h3 className="flex! items-center! gap-[8px]!">
                <Radio size={20} color="var(--accent-secondary)" />
                OGMP 2.0 Level 4/5 Top-Down Survey & Bottom-Up Reconciliation
              </h3>
              <p
                className="text-[color:var(--text-secondary)]! text-[length:0.875rem]! m-[4px_0_0_0]!"
              >
                Site-level measurement (Satellite, OGI, Drone, Aircraft)
                reconciled with source-level bottom-up inventory
              </p>
            </div>
            <div className="flex! items-center! gap-[12px]!">
              <div
                className="ogmp-level-badge bg-[color:rgba(37,_99,_235,_0.1)]! text-[color:#2563eb]! p-[6px_14px]! rounded-[8px]! text-[length:0.85rem]! font-semibold!"
               
              >
                Gold Standard Pathway: Level 5 Reconciled
              </div>
              {ogmpCollapsed ? (
                <ChevronDown size={18} color="var(--text-secondary)" />
              ) : (
                <ChevronUp size={18} color="var(--text-secondary)" />
              )}
            </div>
          </div>

          <div
            className={`[max-height:1500px]! [opacity:1] [overflow:hidden]! [transition:max-height_0.4s_cubic-bezier(0.4,_0,_0.2,_1),_opacity_0.3s_ease,_margin-top_0.3s_ease]! [margin-top:16px]! [&.collapsed]:[max-height:0]! [&.collapsed]:[opacity:0] [&.collapsed]:[margin-top:0]! [&.collapsed]:[pointer-events:none] ${ogmpCollapsed ? "collapsed" : ""}`}
          >
            {ogmpSurveys.length > 0 ? (
              <div className="table-responsive">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Facility</th>
                      <th>Survey Date</th>
                      <th>Technology / Method</th>
                      <th>Measured Rate (kg CH₄/hr)</th>
                      <th>Annualized Rate (tCH₄/yr)</th>
                      <th>Bottom-Up Annual (tCH₄)</th>
                      <th>Variance (%)</th>
                      <th>Reconciliation Status</th>
                      <th>Operator Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ogmpSurveys.map((s, idx) => {
                      const fid = s.facilityId ?? s.facility_id;
                      const matchingFac = regionalData.find(
                        (f) => String(f.facility_id) === String(fid),
                      );
                      const bottomUpCh4 = matchingFac
                        ? matchingFac.total_ch4
                        : null;
                      const facName =
                        s.facilityName ||
                        s.facility_name ||
                        (matchingFac ? matchingFac.facility_name : "—");
                      const sDate = s.surveyDate || s.survey_date || "—";
                      const sType = s.surveyType || s.survey_type || "Top-Down";
                      const rateKgHr =
                        s.measuredRateKgHr ?? s.measured_rate_kg_hr;
                      const annTch4 =
                        s.estimatedAnnualTch4 ?? s.estimated_annual_tch4 ?? 0;
                      const recStatus =
                        s.reconciliationStatus ||
                        s.reconciliation_status ||
                        "Reconciled";
                      const notes = s.operatorNotes || s.operator_notes || "—";

                      let variancePct =
                        s.variance_pct ?? s.reconciliation_variance_pct ?? null;
                      if (variancePct === null && bottomUpCh4 && bottomUpCh4 > 0 && annTch4 > 0) {
                        variancePct =
                          ((annTch4 - bottomUpCh4) / bottomUpCh4) * 100.0;
                      }

                      return (
                        <tr key={s.id || idx}>
                          <td className="font-semibold!">{facName}</td>
                          <td>{sDate}</td>
                          <td>
                            <span className="code-pill [background:var(--bg-hover)]! [padding:3px_8px]! [border-radius:var(--radius-sm)]! [font-family:monospace]! [font-size:var(--text-sm)]! [color:var(--text-primary)]! [border:1px_solid_var(--border-color)]!">{sType}</span>
                          </td>
                          <td>
                            <strong className="text-[color:#2563eb]!">
                              {typeof rateKgHr === "number"
                                ? rateKgHr.toFixed(2)
                                : "—"}
                            </strong>
                          </td>
                          <td>
                            <strong>{formatNumber(annTch4, 2)}</strong>
                          </td>
                          <td>
                            {bottomUpCh4 !== null
                              ? `${bottomUpCh4.toFixed(2)} t`
                              : "—"}
                          </td>
                          <td>
                            {variancePct !== null ? (
                              <span
                                style={{
                                  fontWeight: 700,
                                  color:
                                    Math.abs(variancePct) <= (globalThreshold || 20.0)
                                      ? "#2e7d32"
                                      : "#b91c1c",
                                }}
                              >
                                {variancePct >= 0
                                  ? `+${variancePct.toFixed(1)}%`
                                  : `${variancePct.toFixed(1)}%`}
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>
                            <span
                              className={`status-badge ${recStatus === "Reconciled" ? "badge-success" : "badge-warning"}`}
                              style={{
                                padding: "4px 10px",
                                borderRadius: "6px",
                                fontSize: "0.8rem",
                                fontWeight: 600,
                                background:
                                  recStatus === "Reconciled"
                                    ? "rgba(16, 185, 129, 0.1)"
                                    : "rgba(245, 158, 11, 0.1)",
                                color:
                                  recStatus === "Reconciled"
                                    ? "#2e7d32"
                                    : "#b45309",
                              }}
                            >
                              {recStatus}
                            </span>
                          </td>
                          <td
                            className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!"
                          >
                            {notes}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="[padding:32px]! [text-align:center]! [background:var(--bg-app)]! [border-radius:var(--radius-md)]! [border:1px_dashed_var(--border-color)]! [color:var(--text-secondary)]! [font-size:var(--text-base)]! [margin-top:16px]!">
                <p>
                  No OGMP 2.0 top-down surveys registered for the selected
                  filters. Record survey campaigns via{" "}
                  <strong>Manage Data &gt; OGMP Surveys</strong>.
                </p>
              </div>
            )}
          </div>
        </div>
);

export default MethaneIntensityOGMP20Level;
