import React from "react";
import { formatCompactNumber } from "../../utils/formatters";

// Extracted from DashboardEnhanced.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const EmissionsOverviewCard = ({ currentActivity, currentDivision, currentRegion, currentYear, exportingPDF, facilities, goal, handleExportPDF, hasProductionData, intensity, stats, variance }) => (
<div className="card hero-card glass-panel">
          <div className="hero-header flex! justify-between! items-center!">
            <h2 className="hero-title">Emissions Overview</h2>
            <div className="flex! items-center! gap-[10px]!">
              <div className="location-badge">
                {currentRegion !== "all"
                  ? facilities.find((f) => f.id.toString() === currentRegion)
                      ?.name || "Region"
                  : currentDivision !== "all"
                    ? currentDivision
                    : currentActivity !== "all"
                      ? currentActivity
                      : "All Regions"}
              </div>
              <button
                onClick={handleExportPDF}
                disabled={exportingPDF}
                className="btn-secondary-unified"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.9)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: exportingPDF ? 'not-allowed' : 'pointer',
                  color: 'var(--text-primary)',
                  opacity: exportingPDF ? 0.7 : 1,
                }}
                title="Export multi-page executive summary PDF"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                  <path d="M6 14h12v8H6z" />
                </svg>
                {exportingPDF ? "Generating PDF..." : "Export Executive Brief (PDF)"}
              </button>
            </div>
          </div>

          <div className="hero-stats-grid">
            <div className="stat-item">
              <div className="stat-label">Gross Operational Emissions (Scope 1+2)</div>
              <div className="stat-value-row">
                <div className="stat-value">
                  {formatCompactNumber(stats.totalEmissions)}
                </div>
                <span className="stat-unit">tCO₂e</span>
                {currentYear !== "all" && variance.emissions !== "—" && (
                  <span
                    className={`variance-badge ${variance.emissions.startsWith("+") ? "danger" : "success"}`}
                  >
                    {variance.emissions}
                  </span>
                )}
              </div>
              {goal && goal.target_amount > 0 && (
                <div className="stat-sublabel mt-[8px]!">
                  <span
                    className={`goal-progress-badge ${
                      stats.totalEmissions / goal.target_amount > 1
                        ? "danger"
                        : stats.totalEmissions / goal.target_amount > 0.9
                          ? "warning"
                          : "normal"
                    }`}
                  >
                    {(
                      (stats.totalEmissions / goal.target_amount) *
                      100
                    ).toFixed(1)}
                    % GOAL
                  </span>
                </div>
              )}
            </div>

            <div className="stat-item border-left">
              <div className="stat-label">Net Emissions</div>
              <div className="stat-value-row">
                <div className="stat-value success">
                  {formatCompactNumber(stats.netEmissions)}
                </div>
                <span className="stat-unit">tCO₂e</span>
              </div>
              <div className="stat-sublabel">
                Less{" "}
                <span className="success-text">
                  {formatCompactNumber(stats.mitigation)}
                </span>{" "}
                Mitigation
              </div>
            </div>

            <div className="stat-item border-left">
              <div className="stat-label">Total CH4 (Methane)</div>
              <div className="stat-value-row">
                <div className="stat-value warning">
                  {formatCompactNumber(stats.methaneEmissions)}
                </div>
                <span className="stat-unit">tCH₄</span>
              </div>
            </div>

            <div className="stat-item border-left">
              <div className="stat-label">Performance Intensity</div>
              <div className="stat-value-row">
                <div
                  className="stat-value"
                  style={{
                    color: !hasProductionData && stats.totalEmissions > 0 ? "#b45309" : "var(--text-primary)",
                    fontSize: !hasProductionData && stats.totalEmissions > 0 ? "1.25rem" : undefined,
                  }}
                >
                  {!hasProductionData && stats.totalEmissions > 0 ? "Pending" : formatCompactNumber(intensity, 2)}
                </div>
                <span className="stat-unit">
                  {!hasProductionData && stats.totalEmissions > 0 ? "Production" : "kg/BOE"}
                </span>
                {currentYear !== "all" && variance.intensity !== "—" && hasProductionData && (
                  <span
                    className={`variance-badge ${variance.intensity.startsWith("+") ? "danger" : "success"}`}
                  >
                    {variance.intensity}
                  </span>
                )}
              </div>
              <div className="stat-sublabel">
                {!hasProductionData && stats.totalEmissions > 0 ? (
                  <span style={{ color: "#d97706", fontWeight: 600 }}>Production figures required</span>
                ) : (
                  "CO₂e Intensity (Scope 1+2)"
                )}
              </div>
            </div>
          </div>

          <div className="scope-pills-row">
            <div className="scope-pill scope-1">
              <span className="pill-label">Scope 1 (Direct)</span>
              <span className="pill-value">
                {formatCompactNumber(stats.scope1)} tCO₂e
              </span>
            </div>
            <div className="scope-pill scope-2">
              <span className="pill-label">Scope 2 (Indirect)</span>
              <span className="pill-value">
                {formatCompactNumber(stats.scope2)} tCO₂e
              </span>
            </div>
            <div className="scope-pill scope-3">
              <span className="pill-label">Scope 3 (Supply Chain)</span>
              <span className="pill-value">
                {formatCompactNumber(stats.scope3)} tCO₂e
              </span>
            </div>
          </div>
        </div>
);

export default EmissionsOverviewCard;
