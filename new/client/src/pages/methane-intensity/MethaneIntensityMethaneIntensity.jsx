import React from "react";
import { AlertTriangle, CheckCircle, Compass, Flame, Wind } from "lucide-react";
import { formatNumber } from "../../utils/formatters";

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityMethaneIntensity = ({ midstreamTargetPct, selectedYear, stats, upstreamTargetPct }) => (
<div className="hero-card">
          <div className="hero-header">
            <div className="flex! items-center! gap-[16px]!">
              <h2 className="grid-title">
                <Wind size={24} color="var(--accent-secondary)" />
                Methane Intensity & Loss Rate Analytics
              </h2>
              <div
                className="year-badge"
                style={{
                  background: "rgba(37, 99, 235, 0.1)",
                  color: "#2563eb",
                  borderColor: "rgba(37, 99, 235, 0.2)",
                }}
              >
                {selectedYear === "all" ? "All-Time" : selectedYear} Performance
              </div>
            </div>

            {/* OGMP 2.0 Gold Standard Badge */}
            <div
              className="ogmp-gold-badge"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "8px",
                background:
                  stats.ogmpGoldStatus === "Compliant"
                    ? "rgba(16, 185, 129, 0.1)"
                    : stats.ogmpGoldStatus === "Warning" ||
                      stats.ogmpGoldStatus === "Pending Production"
                    ? "rgba(245, 158, 11, 0.1)"
                    : "rgba(239, 68, 68, 0.1)",
                border: `1px solid ${
                  stats.ogmpGoldStatus === "Compliant"
                    ? "#10b981"
                    : stats.ogmpGoldStatus === "Warning" ||
                      stats.ogmpGoldStatus === "Pending Production"
                    ? "#f59e0b"
                    : "#ef4444"
                }`,
                color:
                  stats.ogmpGoldStatus === "Compliant"
                    ? "#2e7d32"
                    : stats.ogmpGoldStatus === "Warning" ||
                      stats.ogmpGoldStatus === "Pending Production"
                    ? "#f59e0b"
                    : "#ef4444",
                fontWeight: 600,
                fontSize: "0.85rem",
              }}
            >
              {stats.ogmpGoldStatus === "Compliant" ? (
                <CheckCircle size={16} />
              ) : (
                <AlertTriangle size={16} />
              )}
              <span>
                OGMP 2.0 Targets: {stats.ogmpGoldStatus}{" "}
                {stats.ogmpGoldStatus === "Pending Production"
                  ? "(Gas production figures required)"
                  : `(≤${upstreamTargetPct.toFixed(2)}% Upstream / ≤${midstreamTargetPct.toFixed(2)}% Midstream)`}
              </span>
            </div>
          </div>

          {/* Horizontal 4-KPI Grid */}
          <div className="kpi-grid-4">
            <div className="kpi-card">
              <div className="kpi-header">
                <div className="kpi-icon ch4">
                  <Wind size={20} />
                </div>
                <span className="kpi-label">Methane Intensity (Avg)</span>
              </div>
              <div className="kpi-value-container">
                <span className="total-value ch4">
                  {(stats.avgCh4Intensity ?? 0).toFixed(4)}
                </span>
                <span className="kpi-unit">kg CH₄ / BOE</span>
              </div>
              <div className="kpi-footer">
                <span>
                  Total CH₄:{" "}
                  <strong>{formatNumber(stats.totalCh4Emissions)} tCH₄</strong>
                </span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-header">
                <div
                  className="kpi-icon loss bg-[color:rgba(59,_130,_246,_0.1)]! text-[color:#1d4ed8]!"
                 
                >
                  <Compass size={20} />
                </div>
                <span className="kpi-label">Methane Loss Rate</span>
              </div>
              <div className="kpi-value-container">
                <span
                  className="total-value"
                  style={{
                    color:
                      stats.totalGasProductionM3 === 0 && stats.totalCh4Emissions > 0
                        ? "#b45309"
                        : stats.avgMethaneLossRatePct <= upstreamTargetPct
                          ? "#10b981"
                          : stats.avgMethaneLossRatePct <=
                              upstreamTargetPct * 1.25
                            ? "#f59e0b"
                            : "#ef4444",
                  }}
                >
                  {stats.totalGasProductionM3 === 0 && stats.totalCh4Emissions > 0
                    ? "Pending Prod."
                    : `${(stats.avgMethaneLossRatePct ?? 0).toFixed(3)}%`}
                </span>
                <span className="kpi-unit">
                  {stats.totalGasProductionM3 === 0 && stats.totalCh4Emissions > 0
                    ? "Gas prod. required"
                    : "Overall Avg"}
                </span>
              </div>

              {/* Upstream & Midstream Segment Loss Rates */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "6px",
                  margin: "8px 0 6px 0",
                  padding: "6px 8px",
                  background: "var(--bg-secondary, rgba(255,255,255,0.03))",
                  borderRadius: "8px",
                  border: "1px solid var(--border-color, #e5e7eb)",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "0.7rem",
                      color: "var(--text-secondary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      fontWeight: 600,
                    }}
                  >
                    Upstream
                  </div>
                  <div
                    style={{
                      fontSize: "0.95rem",
                      fontWeight: 700,
                      color:
                        stats.upstreamGasM3 === 0 && stats.upstreamCh4Tonnes > 0
                          ? "#b45309"
                          : stats.upstreamLossRatePct <= upstreamTargetPct
                            ? "#10b981"
                            : "#ef4444",
                    }}
                  >
                    {stats.upstreamGasM3 === 0 && stats.upstreamCh4Tonnes > 0
                      ? "Pending Prod."
                      : `${(stats.upstreamLossRatePct ?? 0).toFixed(3)}%`}
                  </div>
                  <div
                    className="text-[length:0.68rem]! text-[color:var(--text-secondary)]!"
                  >
                    Target &le; {upstreamTargetPct.toFixed(2)}%
                  </div>
                </div>

                <div
                  style={{
                    borderLeft: "1px solid var(--border-color, #e5e7eb)",
                    paddingLeft: "8px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.7rem",
                      color: "var(--text-secondary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      fontWeight: 600,
                    }}
                  >
                    Midstream
                  </div>
                  <div
                    style={{
                      fontSize: "0.95rem",
                      fontWeight: 700,
                      color:
                        stats.midstreamGasM3 === 0 && stats.midstreamCh4Tonnes > 0
                          ? "#b45309"
                          : stats.midstreamLossRatePct <= midstreamTargetPct
                            ? "#10b981"
                            : "#ef4444",
                    }}
                  >
                    {stats.midstreamGasM3 === 0 && stats.midstreamCh4Tonnes > 0
                      ? "Pending Prod."
                      : `${(stats.midstreamLossRatePct ?? 0).toFixed(3)}%`}
                  </div>
                  <div
                    className="text-[length:0.68rem]! text-[color:var(--text-secondary)]!"
                  >
                    Target &le; {midstreamTargetPct.toFixed(2)}%
                  </div>
                </div>
              </div>

              <div className="kpi-footer">
                <span>
                  OGMP 2.0:{" "}
                  <strong>
                    &le;{upstreamTargetPct.toFixed(2)}% Up / &le;{midstreamTargetPct.toFixed(2)}% Mid
                  </strong>
                </span>
                <span>
                  Vol:{" "}
                  <strong>{formatNumber(stats.totalCh4VolumeM3, 0)} m³</strong>
                </span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-header">
                <div className="kpi-icon flare">
                  <Flame size={20} />
                </div>
                <span className="kpi-label">Gas Flaring Rate</span>
              </div>
              <div className="kpi-value-container">
                <span className="total-value flare">
                  {(stats.avgFlaringRatePct ?? 0).toFixed(3)}%
                </span>
                <span className="kpi-unit">of Gas Volume</span>
              </div>
              <div className="kpi-footer">
                <span>
                  Flared:{" "}
                  <strong>
                    {formatNumber(stats.totalFlaringVolume, 0)} m³
                  </strong>
                </span>
              </div>
            </div>

            <div className="kpi-card">
              <div className="kpi-header">
                <div
                  className="kpi-icon wec bg-[color:rgba(239,_68,_68,_0.1)]! text-[color:#b91c1c]!"
                 
                >
                  <AlertTriangle size={20} />
                </div>
                <span className="kpi-label">EPA WEC Liability</span>
              </div>
              <div className="kpi-value-container">
                <span
                  className="total-value"
                  style={{
                    color: !stats.wecAssessed ? "#64748b" : stats.totalWecFeeUsd > 0 ? "#ef4444" : "#10b981",
                  }}
                >
                  {stats.wecAssessed ? `$${formatNumber(stats.totalWecFeeUsd, 0)}` : "—"}
                </span>
                <span className="kpi-unit">
                  {stats.wecAssessed ? "USD Est." : stats.wecReason || "Select a single year"}
                </span>
              </div>
              <div className="kpi-footer">
                <span>
                  Rate:{" "}
                  <strong>
                    {stats.wecRate
                      ? `$${formatNumber(stats.wecRate, 0)}`
                      : selectedYear === "all"
                        ? "per year"
                        : "—"}
                    /t CH₄
                  </strong>{" "}
                  (CAA §136, from 2034 emissions)
                </span>
              </div>
            </div>
          </div>

          {/* Methane Mass Balance Bar */}
          <div className="scope-breakdown">
            <div className="scope-item">
              <span className="label">Total Gas Produced</span>
              <span className="val">
                {formatNumber(stats.totalGasProductionM3, 0)} m³{" "}
                <sub
                  className="text-[length:0.7em]! text-[color:var(--text-secondary)]!"
                >
                  ({formatNumber(stats.totalGasProductionMscf, 0)} mscf)
                </sub>
              </span>
            </div>
            <div className="scope-item bordered">
              <span className="label">Methane Loss Volume</span>
              <span
                className="val text-[color:#2563eb]! font-bold!"
               
              >
                {formatNumber(stats.totalCh4VolumeM3, 0)} m³
              </span>
            </div>
            <div className="scope-item bordered">
              <span className="label">Total Gas Flared</span>
              <span className="val flare-val">
                {formatNumber(stats.totalFlaringVolume, 0)} m³
              </span>
            </div>
            <div className="scope-item bordered">
              <span className="label">Total Combined BOE</span>
              <span className="val">{formatNumber(stats.totalBoe, 0)} BOE</span>
            </div>
          </div>
        </div>
);

export default MethaneIntensityMethaneIntensity;
