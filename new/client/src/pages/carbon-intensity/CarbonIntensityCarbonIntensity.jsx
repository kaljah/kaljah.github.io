import React from "react";
import { SegmentedControl } from "../../ui";
import { Activity, Cloud, Flame, Layers, ShieldCheck } from "lucide-react";
import { formatNumber } from "../../utils/formatters";
import { getActiveGwpFactors } from "../../constants";

// Extracted from CarbonIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const CarbonIntensityCarbonIntensity = ({ activeGwpStandard, currentDisplayCo2Intensity, currentDisplayScope1Intensity, currentDisplayTotalCo2e, currentDisplayTotalScope1, currentUsedCo2e, currentUsedScope1, excludedNote, gwpHorizon, selectedYear, setGwpHorizon, stats }) => (
<div className="hero-card">
          <div className="hero-header">
            <div className="flex! items-center! gap-[16px]!">
              <h2 className="grid-title">
                <Activity size={24} color="var(--accent-color)" />
                Carbon Intensity & Product Embodiment
              </h2>
              <div className="year-badge">
                {selectedYear === "all" ? "All-Time" : selectedYear} Performance
              </div>
            </div>

            {/* GWP Time Horizon Toggle */}
            <div className="gwp-toggle-container">
              <span className="gwp-toggle-label">GWP Horizon:</span>
              {(() => {
                const f100 = getActiveGwpFactors(activeGwpStandard, "100");
                const f20 = getActiveGwpFactors(activeGwpStandard, "20");
                return (
                  <SegmentedControl
                    label="GWP horizon"
                    size="sm"
                    value={gwpHorizon}
                    onChange={setGwpHorizon}
                    options={[
                      {
                        value: "100",
                        label: `${activeGwpStandard} 100-Yr`,
                        title: `IPCC ${activeGwpStandard} 100-Year GWP (CH4: ${f100.CH4}, N2O: ${f100.N2O})`,
                      },
                      {
                        value: "20",
                        label: `${activeGwpStandard} 20-Yr`,
                        title: `IPCC ${activeGwpStandard} 20-Year GWP (CH4: ${f20.CH4}, N2O: ${f20.N2O})`,
                      },
                    ]}
                  />
                );
              })()}
            </div>
          </div>

          {/* Horizontal 4-KPI Grid */}
          <div className="kpi-grid-4">
            <div className="kpi-card">
              <div className="kpi-header">
                <div className="kpi-icon co2">
                  <Cloud size={20} />
                </div>
                <span className="kpi-label">GHG Intensity (Avg)</span>
              </div>
              <div className="kpi-value-container">
                <span
                  className="total-value co2"
                  style={
                    currentDisplayCo2Intensity === null
                      ? { fontSize: "1.25rem", color: "#f59e0b" }
                      : undefined
                  }
                >
                  {currentDisplayCo2Intensity === null
                    ? "Pending Production"
                    : (currentDisplayCo2Intensity ?? 0).toFixed(2)}
                </span>
                <span className="kpi-unit">
                  {currentDisplayCo2Intensity === null ? "" : "kg CO₂e / BOE"}
                </span>
              </div>
              <div className="kpi-footer">
                <span className="gwp-subtag">
                  {gwpHorizon === "20" ? "GWP₂₀ Active" : "GWP₁₀₀ Standard"}
                </span>
                <span>
                  Total:{" "}
                  <strong>{formatNumber(currentDisplayTotalCo2e)} tCO₂e</strong>
                </span>
              </div>
              {excludedNote(currentDisplayTotalCo2e, currentUsedCo2e)}
            </div>

            <div className="kpi-card">
              <div className="kpi-header">
                <div className="kpi-icon scope1">
                  <Layers size={20} />
                </div>
                <span className="kpi-label">Scope 1 Direct Intensity</span>
              </div>
              <div className="kpi-value-container">
                <span
                  className="total-value scope1"
                  style={
                    currentDisplayScope1Intensity === null
                      ? { fontSize: "1.25rem", color: "#f59e0b" }
                      : undefined
                  }
                >
                  {currentDisplayScope1Intensity === null
                    ? "Pending Production"
                    : (currentDisplayScope1Intensity ?? 0).toFixed(2)}
                </span>
                <span className="kpi-unit">
                  {currentDisplayScope1Intensity === null ? "" : "kg CO₂e / BOE"}
                </span>
              </div>
              <div className="kpi-footer">
                <span>
                  Scope 2:{" "}
                  <strong>
                    {stats.avgScope2Intensity === null
                      ? "Pending"
                      : `${(stats.avgScope2Intensity ?? 0).toFixed(2)} kg/BOE`}
                  </strong>
                </span>
                <span>
                  Total S1: <strong>{formatNumber(currentDisplayTotalScope1)} t</strong>
                </span>
              </div>
              {excludedNote(currentDisplayTotalScope1, currentUsedScope1)}
            </div>

            <div className="kpi-card">
              <div className="kpi-header">
                <div className="kpi-icon flare">
                  <Flame size={20} />
                </div>
                <span className="kpi-label">Flaring Carbon Intensity</span>
              </div>
              <div className="kpi-value-container">
                <span className="total-value flare">
                  {(stats.avgFlaringIntensity ?? 0).toFixed(2)}
                </span>
                <span className="kpi-unit">kg CO₂e / BOE</span>
              </div>
              <div className="kpi-footer">
                <span>
                  Flared:{" "}
                  <strong>
                    {formatNumber(stats.totalFlaringEmissions)} tCO₂e
                  </strong>
                </span>
              </div>
              {excludedNote(stats.totalFlaringEmissions, stats.usedFlaring)}
            </div>

            <div className="kpi-card">
              <div className="kpi-header">
                <div className="kpi-icon scope3">
                  <ShieldCheck size={20} />
                </div>
                <span className="kpi-label">Scope 3 Value Chain</span>
              </div>
              <div className="kpi-value-container">
                <span className="total-value scope3">
                  {(stats.avgScope3Intensity ?? 0).toFixed(2)}
                </span>
                <span className="kpi-unit">kg CO₂e / BOE</span>
              </div>
              <div className="kpi-footer">
                <span>
                  Total S3:{" "}
                  <strong>{formatNumber(stats.totalScope3)} tCO₂e</strong>
                </span>
              </div>
              {excludedNote(stats.totalScope3, stats.usedScope3)}
            </div>
          </div>

          {/* Production Context Bar */}
          <div className="scope-breakdown">
            <div className="scope-item">
              <span className="label">Total Oil Production</span>
              <span className="val">
                {formatNumber(stats.totalOilProduction, 0)} bbl
              </span>
            </div>
            <div className="scope-item bordered">
              <span className="label">Total Gas Production</span>
              <span className="val">
                {formatNumber(stats.totalGasProduction, 0)} mscf
              </span>
            </div>
            <div className="scope-item bordered">
              <span className="label">Combined Production (BOE)</span>
              <span
                className="val text-[color:var(--color-link)]! font-bold!"
               
              >
                {formatNumber(stats.totalBoe, 0)} BOE
              </span>
            </div>
            <div className="scope-item bordered">
              <span className="label">Total Gas Flared</span>
              <span className="val flare-val">
                {formatNumber(stats.totalFlaringVolume, 0)} m³
              </span>
            </div>
          </div>
        </div>
);

export default CarbonIntensityCarbonIntensity;
