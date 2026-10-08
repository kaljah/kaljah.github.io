import React from "react";
import { AlertTriangle, CheckCircle, Compass, Flame, Wind } from "lucide-react";
import { formatNumber } from "../../utils/formatters";

export interface MethaneIntensityStats {
  ogmpGoldStatus?: string;
  avgCh4Intensity?: number | null;
  totalCh4Emissions?: number;
  totalGasProductionM3?: number;
  avgMethaneLossRatePct?: number | null;
  upstreamGasM3?: number;
  upstreamCh4Tonnes?: number;
  upstreamLossRatePct?: number | null;
  midstreamGasM3?: number;
  midstreamCh4Tonnes?: number;
  midstreamLossRatePct?: number | null;
  totalCh4VolumeM3?: number;
  avgFlaringRatePct?: number | null;
  totalFlaringVolume?: number;
  totalGasProductionMscf?: number;
  totalBoe?: number;
  [key: string]: any;
}

export interface MethaneIntensityMethaneIntensityProps {
  midstreamTargetPct: number;
  selectedYear: string | number;
  stats: MethaneIntensityStats;
  upstreamTargetPct: number;
}

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityMethaneIntensity: React.FC<MethaneIntensityMethaneIntensityProps> = ({
  midstreamTargetPct,
  selectedYear,
  stats,
  upstreamTargetPct,
}) => (
  <div className="hero-card">
    <div className="hero-header">
      <div className="flex! items-center! gap-[16px]!">
        <h2 className="grid-title">
          <Wind size={24} color="var(--accent-secondary)" />
          Methane Intensity & Loss Rate Analytics
        </h2>
        <div
          className="year-badge [background:rgba(255,_102,_0,_0.1)] [padding:6px_16px] [border-radius:9999px] [font-size:var(--text-base)] [font-weight:600] [border:1px_solid_rgba(255,_102,_0,_0.2)] bg-[color:rgba(37,_99,_235,_0.1)]! text-[color:var(--color-blue-600)]! [&&]:[border-color:rgba(37,_99,_235,_0.2)]!"
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
              ? "var(--color-green-500)"
              : stats.ogmpGoldStatus === "Warning" ||
                stats.ogmpGoldStatus === "Pending Production"
              ? "var(--color-amber-500)"
              : "var(--color-red-500)"
          }`,
          color:
            stats.ogmpGoldStatus === "Compliant"
              ? "var(--color-green-700)"
              : stats.ogmpGoldStatus === "Warning" ||
                stats.ogmpGoldStatus === "Pending Production"
              ? "var(--color-amber-500)"
              : "var(--color-red-500)",
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

    {/* Horizontal 3-KPI Grid */}
    <div className="[display:grid] [grid-template-columns:repeat(3,_1fr)]! [gap:20px] [@media(max-width:1200px)]:[grid-template-columns:repeat(2,_1fr)]! [@media(max-width:768px)]:[grid-template-columns:1fr]!">
      <div className="kpi-card">
        <div className="[display:flex] [align-items:center] [gap:12px] [margin-bottom:16px]">
          <div className="kpi-icon ch4">
            <Wind size={20} />
          </div>
          <span className="kpi-label">Methane Intensity (Avg)</span>
        </div>
        <div className="[display:flex] [align-items:baseline] [gap:8px]">
          <span className="total-value ch4">
            {(stats.avgCh4Intensity ?? 0).toFixed(4)}
          </span>
          <span className="kpi-unit">kg CH₄ / BOE</span>
        </div>
        <div className="kpi-footer">
          <span>
            Total CH₄:{" "}
            <strong>{formatNumber(stats.totalCh4Emissions ?? 0)} tCH₄</strong>
          </span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="[display:flex] [align-items:center] [gap:12px] [margin-bottom:16px]">
          <div
            className="kpi-icon loss bg-[color:rgba(59,_130,_246,_0.1)]! text-[color:var(--color-blue-700)]!"
          >
            <Compass size={20} />
          </div>
          <span className="kpi-label">Methane Loss Rate</span>
        </div>
        <div className="[display:flex] [align-items:baseline] [gap:8px]">
          <span
            className="total-value"
            style={{
              color:
                stats.totalGasProductionM3 === 0 && (stats.totalCh4Emissions ?? 0) > 0
                  ? "var(--color-amber-700)"
                  : (stats.avgMethaneLossRatePct ?? 0) <= upstreamTargetPct
                    ? "var(--color-green-500)"
                    : (stats.avgMethaneLossRatePct ?? 0) <=
                        upstreamTargetPct * 1.25
                      ? "var(--color-amber-500)"
                      : "var(--color-red-500)",
            }}
          >
            {stats.totalGasProductionM3 === 0 && (stats.totalCh4Emissions ?? 0) > 0
              ? "Pending Prod."
              : `${(stats.avgMethaneLossRatePct ?? 0).toFixed(3)}%`}
          </span>
          <span className="kpi-unit">
            {stats.totalGasProductionM3 === 0 && (stats.totalCh4Emissions ?? 0) > 0
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
            border: "1px solid var(--border-color, var(--color-legacy-e5e7eb))",
          }}
        >
          <div>
            <div
              className="text-[length:0.7rem]! text-[color:var(--text-secondary)]! uppercase! [letter-spacing:0.5px]! font-semibold!"
            >
              Upstream
            </div>
            <div
              style={{
                fontSize: "0.95rem",
                fontWeight: 700,
                color:
                  stats.upstreamGasM3 === 0 && (stats.upstreamCh4Tonnes ?? 0) > 0
                    ? "var(--color-amber-700)"
                    : (stats.upstreamLossRatePct ?? 0) <= upstreamTargetPct
                      ? "var(--color-green-500)"
                      : "var(--color-red-500)",
              }}
            >
              {stats.upstreamGasM3 === 0 && (stats.upstreamCh4Tonnes ?? 0) > 0
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
            className="[border-left:1px_solid_var(--border-color,_var(--color-legacy-e5e7eb))]! pl-[8px]!"
          >
            <div
              className="text-[length:0.7rem]! text-[color:var(--text-secondary)]! uppercase! [letter-spacing:0.5px]! font-semibold!"
            >
              Midstream
            </div>
            <div
              style={{
                fontSize: "0.95rem",
                fontWeight: 700,
                color:
                  stats.midstreamGasM3 === 0 && (stats.midstreamCh4Tonnes ?? 0) > 0
                    ? "var(--color-amber-700)"
                    : (stats.midstreamLossRatePct ?? 0) <= midstreamTargetPct
                      ? "var(--color-green-500)"
                      : "var(--color-red-500)",
              }}
            >
              {stats.midstreamGasM3 === 0 && (stats.midstreamCh4Tonnes ?? 0) > 0
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
            <strong>{formatNumber(stats.totalCh4VolumeM3 ?? 0, 0)} m³</strong>
          </span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="[display:flex] [align-items:center] [gap:12px] [margin-bottom:16px]">
          <div className="kpi-icon flare">
            <Flame size={20} />
          </div>
          <span className="kpi-label">Gas Flaring Rate</span>
        </div>
        <div className="[display:flex] [align-items:baseline] [gap:8px]">
          <span className="total-value flare">
            {(stats.avgFlaringRatePct ?? 0).toFixed(3)}%
          </span>
          <span className="kpi-unit">of Gas Volume</span>
        </div>
        <div className="kpi-footer">
          <span>
            Flared:{" "}
            <strong>
              {formatNumber(stats.totalFlaringVolume ?? 0, 0)} m³
            </strong>
          </span>
        </div>
      </div>
    </div>

    {/* Methane Mass Balance Bar */}
    <div className="scope-breakdown [display:grid] [grid-template-columns:repeat(4,_1fr)]! [gap:20px] [margin-top:32px] [background:var(--bg-hover)] [padding:24px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color)] [@media(max-width:1200px)]:[grid-template-columns:repeat(2,_1fr)]! [@media(max-width:768px)]:[grid-template-columns:1fr]!">
      <div className="scope-item">
        <span className="label">Total Gas Produced</span>
        <span className="val">
          {formatNumber(stats.totalGasProductionM3 ?? 0, 0)} m³{" "}
          <sub
            className="text-[length:0.7em]! text-[color:var(--text-secondary)]!"
          >
            ({formatNumber(stats.totalGasProductionMscf ?? 0, 0)} mscf)
          </sub>
        </span>
      </div>
      <div className="scope-item bordered">
        <span className="label">Methane Loss Volume</span>
        <span
          className="val text-[color:var(--color-blue-600)]! font-bold!"
        >
          {formatNumber(stats.totalCh4VolumeM3 ?? 0, 0)} m³
        </span>
      </div>
      <div className="scope-item bordered">
        <span className="label">Total Gas Flared</span>
        <span className="val flare-val">
          {formatNumber(stats.totalFlaringVolume ?? 0, 0)} m³
        </span>
      </div>
      <div className="scope-item bordered">
        <span className="label">Total Combined BOE</span>
        <span className="val">{formatNumber(stats.totalBoe ?? 0, 0)} BOE</span>
      </div>
    </div>
  </div>
);

export default MethaneIntensityMethaneIntensity;
