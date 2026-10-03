import React from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { activateOnKey } from "../../utils/a11yKeys";
import { formatCompactNumber } from "../../utils/formatters";

// Extracted from DashboardEnhanced.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const DetailedBreakdownSection = ({ detailedBreakdownCollapsed, expandedActivities, expandedDivisions, flaringData, formatActivityName, getHierarchicalData, navigate, setDetailedBreakdownCollapsed, stats, toggleActivity, toggleDivision }) => (
<div className="[display:grid]! [grid-template-columns:8fr_4fr] [gap:24px] max-[1200px]:[grid-template-columns:1fr] max-[1200px]:[gap:20px]">
          <div className="detailed-breakdown-section">
            <div
              className={`card detailed-table-card glass-panel ${detailedBreakdownCollapsed ? "collapsed-card" : ""}`}
            >
              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="table-header-row clickable-card-header"
                onClick={() =>
                  setDetailedBreakdownCollapsed(!detailedBreakdownCollapsed)
                }
                style={{
                  cursor: "pointer",
                  userSelect: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <h3 className="card-title m-[0px]!">
                  Detailed Breakdown
                </h3>
                <div
                  className="[@mediaprint]:[display:none]! flex! items-center! text-[color:#64748b]!"
                 
                >
                  {detailedBreakdownCollapsed ? (
                    <ChevronDown size={18} />
                  ) : (
                    <ChevronUp size={18} />
                  )}
                </div>
              </div>
              <div
                className={`collapsible-body-wrapper ${detailedBreakdownCollapsed ? "collapsed" : ""}`}
              >
                <div className="table-container mt-[16px]!">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Category / Source</th>
                        <th className="text-right">Results (tCO₂e)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="summary-row">
                        <td>Scope 1 (Direct)</td>
                        <td className="text-right font-bold">
                          {formatCompactNumber(stats.scope1)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="[padding-left:28px]!">Combustion (stationary &amp; mobile)</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.combustion)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="[padding-left:28px]!">Flaring</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.flaring)}
                        </td>
                      </tr>
                      {flaringData && (flaringData.routine_flaring?.volume_knm3 > 0 || flaringData.non_routine_flaring?.volume_knm3 > 0 || flaringData.safety_flaring?.volume_knm3 > 0) && (
                        <>
                          <tr className="detail-row text-[length:0.82rem]! text-[color:#64748b]! bg-[color:rgba(248,_250,_252,_0.5)]!">
                            <td className="pl-[36px]!">↳ Routine ({flaringData.routine_flaring?.percentage ?? 0}%)</td>
                            <td className="text-right font-normal">
                              {formatCompactNumber(flaringData.routine_flaring?.tco2e ?? 0)}
                            </td>
                          </tr>
                          <tr className="detail-row text-[length:0.82rem]! text-[color:#64748b]! bg-[color:rgba(248,_250,_252,_0.5)]!">
                            <td className="pl-[36px]!">↳ Non-Routine ({flaringData.non_routine_flaring?.percentage ?? 0}%)</td>
                            <td className="text-right font-normal">
                              {formatCompactNumber(flaringData.non_routine_flaring?.tco2e ?? 0)}
                            </td>
                          </tr>
                          <tr className="detail-row text-[length:0.82rem]! text-[color:#64748b]! bg-[color:rgba(248,_250,_252,_0.5)]!">
                            <td className="pl-[36px]!">↳ Safety &amp; Purge ({flaringData.safety_flaring?.percentage ?? 0}%)</td>
                            <td className="text-right font-normal">
                              {formatCompactNumber(flaringData.safety_flaring?.tco2e ?? 0)}
                            </td>
                          </tr>
                        </>
                      )}
                      <tr className="detail-row">
                        <td className="[padding-left:28px]!">Venting</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.venting)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="[padding-left:28px]!">Equipment Leaks / Fugitives</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.fugitive)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="[padding-left:28px]!">Other Sources</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.other)}
                        </td>
                      </tr>
                      <tr className="summary-row">
                        <td>Scope 2 (Indirect - Energy)</td>
                        <td className="text-right font-bold">
                          {formatCompactNumber(stats.scope2)}
                        </td>
                      </tr>
                      <tr className="summary-row">
                        <td>Scope 3 (Supply Chain)</td>
                        <td className="text-right font-bold">
                          {formatCompactNumber(stats.scope3)}
                        </td>
                      </tr>
                      <tr className="total-row">
                        <td>Total Footprint (Scopes 1+2+3)</td>
                        <td className="text-right">
                          {formatCompactNumber(
                            (stats.scope1 || 0) +
                              (stats.scope2 || 0) +
                              (stats.scope3 || 0)
                          )}
                        </td>
                      </tr>
                      <tr
                        className="total-row"
                        style={{ color: "#2e7d32", borderTop: "none" }}
                      >
                        <td>Net Footprint</td>
                        <td className="text-right">
                          {formatCompactNumber(
                            (stats.scope1 || 0) +
                              (stats.scope2 || 0) +
                              (stats.scope3 || 0) -
                              (stats.mitigation || 0)
                          )}
                        </td>
                      </tr>

                      <tr className="header-divider">
                        <td colSpan="2">Organizational Breakdown</td>
                      </tr>
                      {Object.entries(getHierarchicalData).map(
                        ([act, actData]) => (
                          <React.Fragment key={act}>
                            <tr tabIndex={0} onKeyDown={activateOnKey}
                              className="act-row clickable"
                              onClick={() => toggleActivity(act)}
                            >
                              <td>
                                <span className="[display:inline-block]! [width:16px]! [font-size:var(--text-xs)]! [color:var(--color-ink-600)]!">
                                  {expandedActivities[act] ? "▼" : "▶"}
                                </span>
                                {formatActivityName(act)}
                              </td>
                              <td className="text-right font-bold">
                                {formatCompactNumber(actData.total)}
                              </td>
                            </tr>
                            {expandedActivities[act] &&
                              Object.entries(actData.divisions).map(
                                ([div, divData]) => (
                                  <React.Fragment key={div}>
                                    <tr tabIndex={0} onKeyDown={activateOnKey}
                                      className="div-row clickable"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleDivision(div);
                                      }}
                                    >
                                      <td className="[padding-left:28px]!">
                                        <span className="[display:inline-block]! [width:16px]! [font-size:var(--text-xs)]! [color:var(--color-ink-600)]!">
                                          {expandedDivisions[div] ? "▼" : "▶"}
                                        </span>
                                        {div}
                                      </td>
                                      <td className="text-right">
                                        {formatCompactNumber(divData.total)}
                                      </td>
                                    </tr>
                                    {expandedDivisions[div] &&
                                      divData.regions.map((reg, ridx) => (
                                        <tr key={ridx} className="reg-row">
                                          <td className="[padding-left:44px]!">
                                            {reg.region}
                                          </td>
                                          <td className="text-right">
                                            {formatCompactNumber(
                                              reg.total_emissions,
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                  </React.Fragment>
                                ),
                              )}
                          </React.Fragment>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <div className="[display:flex]! [flex-direction:column] [gap:24px]">
            {/* Moved Trend Chart to Top */}

            <div className="card [padding:24px]!">
              <div className="[display:flex]! [justify-content:space-between] [align-items:center] [margin-bottom:24px]! max-[768px]:[flex-direction:column] max-[768px]:[align-items:flex-start] max-[768px]:[gap:12px]">
                <h3 className="card-title">Reference Libraries</h3>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="opacity-[0.3]!"
                >
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
              </div>
              <div className="[display:flex]! [flex-direction:column] [gap:12px] [margin:16px_0_20px_0]!">
                <div className="library-item">
                  <div className="dot blue"></div>
                  API Compendium: 2021
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
                <div className="library-item">
                  <div className="dot green"></div>
                  ISO 14064-1:2018
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
                <div className="library-item">
                  <div className="dot orange"></div>
                  GRI 305 Standards
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
              </div>
              <button
                className="manage-factors-btn"
                onClick={() =>
                  navigate("/manage-data", { state: { tab: "factors" } })
                }
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Manage Custom Factors
              </button>
            </div>
          </div>
        </div>
);

export default DetailedBreakdownSection;
