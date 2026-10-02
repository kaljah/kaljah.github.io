import React from "react";
import { AlertTriangle, CheckCircle2, Flame } from "lucide-react";
import { formatCompactNumber, formatNumber } from "../../utils/formatters";

// Extracted from DashboardEnhanced.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const FlaringComplianceCard = ({ flaringData }) => (
<div className="card glass-panel flaring-kpi-banner">
            <div className="flaring-banner-header">
              <div className="flaring-banner-title-group">
                <div className="flaring-banner-icon">
                  <Flame size={22} />
                </div>
                <div>
                  <h3 className="flaring-banner-title">
                    Operational Flaring &amp; Regulatory Compliance
                  </h3>
                  <p className="flaring-banner-sub">
                    Executive Decree 21-330 Article 9 (1.00% Gas Production Threshold) •{" "}
                    {flaringData.year === "all" ? "All years" : `Year ${flaringData.year}`} • GWP-{flaringData.gwp_horizon || "100"}
                    {flaringData.includes_pending ? " • incl. Pending" : " • Verified only"}
                  </p>
                </div>
              </div>

              <div className="flaring-banner-badges">
                <span
                  className={`flaring-badge ${flaringData.is_compliant === true ? "compliant" : flaringData.is_compliant === false ? "non-compliant" : ""}`}
                >
                  {flaringData.is_compliant === true ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <AlertTriangle size={13} />
                  )}
                  {flaringData.compliance_status}
                </span>

                <span className="flaring-badge dre">
                  {flaringData.measured_dre_pct != null
                    ? `${flaringData.dre_method}: ${flaringData.measured_dre_pct}% DRE`
                    : flaringData.dre_method}
                </span>

                {flaringData.yoy_change_pct != null && flaringData.yoy_change_pct !== 0 && (
                  <span className="flaring-badge yoy">
                    {flaringData.yoy_change_pct > 0 ? `+${flaringData.yoy_change_pct}% YoY` : `${flaringData.yoy_change_pct}% YoY`}
                  </span>
                )}
              </div>
            </div>

            <div className="flaring-streams-grid">
              <div className="flaring-stream-item total-stream">
                <div className="stream-label">Total Flared Volume</div>
                <div className="stream-value">
                  {formatNumber(flaringData.total_flaring?.volume_knm3 ?? 0, 0)}
                  <span className="stream-unit" title="thousand standard m³ (15.6 °C / 60 °F, 1 atm)">kSm³</span>
                </div>
                <div className="stream-sublabel">
                  <strong>{formatCompactNumber(flaringData.total_flaring?.tco2e ?? 0)}</strong> tCO₂e • 100% Stream
                </div>
              </div>

              <div className="flaring-stream-item routine-stream">
                <div className="stream-label">Routine Flaring</div>
                <div className="stream-value">
                  {formatNumber(flaringData.routine_flaring?.volume_knm3 ?? 0, 0)}
                  <span className="stream-unit" title="thousand standard m³ (15.6 °C / 60 °F, 1 atm)">kSm³</span>
                </div>
                <div className="stream-sublabel">
                  <strong>{flaringData.routine_flaring?.percentage ?? 0}%</strong> of total • {formatCompactNumber(flaringData.routine_flaring?.tco2e ?? 0)} tCO₂e
                </div>
              </div>

              <div className="flaring-stream-item non-routine-stream">
                <div className="stream-label">Non-Routine Flaring</div>
                <div className="stream-value">
                  {formatNumber(flaringData.non_routine_flaring?.volume_knm3 ?? 0, 0)}
                  <span className="stream-unit" title="thousand standard m³ (15.6 °C / 60 °F, 1 atm)">kSm³</span>
                </div>
                <div className="stream-sublabel">
                  <strong>{flaringData.non_routine_flaring?.percentage ?? 0}%</strong> of total • {formatCompactNumber(flaringData.non_routine_flaring?.tco2e ?? 0)} tCO₂e
                </div>
              </div>

              <div className="flaring-stream-item safety-stream">
                <div className="stream-label">Safety &amp; Purge Flaring</div>
                <div className="stream-value">
                  {formatNumber(flaringData.safety_flaring?.volume_knm3 ?? 0, 0)}
                  <span className="stream-unit" title="thousand standard m³ (15.6 °C / 60 °F, 1 atm)">kSm³</span>
                </div>
                <div className="stream-sublabel">
                  <strong>{flaringData.safety_flaring?.percentage ?? 0}%</strong> of total • {formatCompactNumber(flaringData.safety_flaring?.tco2e ?? 0)} tCO₂e
                </div>
              </div>

              {flaringData.unclassified_flaring?.volume_knm3 > 0 && (
                <div className="flaring-stream-item">
                  <div className="stream-label">Unclassified Flaring</div>
                  <div className="stream-value">
                    {formatNumber(flaringData.unclassified_flaring.volume_knm3, 0)}
                    <span className="stream-unit" title="thousand standard m³ (15.6 °C / 60 °F, 1 atm)">kSm³</span>
                  </div>
                  <div className="stream-sublabel">
                    <strong>{flaringData.unclassified_flaring.percentage}%</strong> of total • {formatCompactNumber(flaringData.unclassified_flaring.tco2e)} tCO₂e • stream not recorded
                  </div>
                </div>
              )}
            </div>

            {flaringData.gas_production_m3 > 0 && flaringData.flaring_intensity_pct != null && (
              <div className="flaring-intensity-bar-card">
                <div className="flaring-intensity-meta">
                  <span>
                    <strong>Decree 21-330 Flaring Intensity:</strong>{" "}
                    <span style={{ color: flaringData.is_compliant ? "#15803d" : "#b91c1c", fontWeight: 700 }}>
                      {flaringData.flaring_intensity_pct}%
                    </span>{" "}
                    of Gross Gas Produced ({formatCompactNumber(flaringData.gas_production_m3 / 1e6, 2)} MMSm³)
                  </span>
                  <span style={{ fontSize: "0.78rem", color: "#64748b" }}>
                    Statutory Limit: <strong>1.00%</strong> (Executive Decree 21-330 Art. 9)
                  </span>
                </div>
                <div className="flaring-progress-track">
                  <div
                    className="flaring-progress-fill"
                    style={{
                      width: `${Math.min(100, (flaringData.flaring_intensity_pct / 1.00) * 100)}%`,
                      backgroundColor: flaringData.is_compliant ? "#10b981" : "#ef4444",
                    }}
                  />
                  <div
                    className="flaring-progress-marker"
                    style={{ left: "100%" }}
                    title="1.00% Statutory Ceiling"
                  />
                </div>
              </div>
            )}
          </div>
);

export default FlaringComplianceCard;
