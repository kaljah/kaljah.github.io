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
            <div className="[display:flex]! [align-items:center] [gap:10px] [background:var(--bg-hover)]! [padding:4px_8px]! [border-radius:var(--radius-md)]! [border:1px_solid_var(--border-color)]!">
              <span className="[font-size:var(--text-sm)]! [font-weight:600]! [color:var(--text-secondary)]!">GWP Horizon:</span>
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
          <div className="[display:grid]! [grid-template-columns:repeat(4,_1fr)]! [gap:20px] [@media(max-width:1200px)]:[grid-template-columns:repeat(2,_1fr)]! [@media(max-width:768px)]:[grid-template-columns:1fr]!">
            <div className="kpi-card">
              <div className="[display:flex]! [align-items:center] [gap:12px] [margin-bottom:16px]!">
                <div className="[&.scope1]:[background:rgba(37,_99,_235,_0.1)] [&.scope1]:[color:var(--accent-secondary)] [&&]:[&.scope3]:[background:rgba(139,_92,_246,_0.1)] [&&]:[&.scope3]:[color:var(--color-violet-700)] [width:38px]! [height:38px]! [border-radius:var(--radius-md)]! [display:flex]! [align-items:center] [justify-content:center] [flex-shrink:0] [&&]:[&&]:[&.co2]:[background:rgba(255,_102,_0,_0.1)] [&&]:[&&]:[&.co2]:[color:var(--color-link)] [&&]:[&&]:[&&]:[&.ch4]:[background:rgba(37,_99,_235,_0.1)] [&&]:[&&]:[&&]:[&.ch4]:[color:var(--accent-secondary)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[background:rgba(234,_88,_12,_0.1)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[color:var(--accent-tertiary)] co2">
                  <Cloud size={20} />
                </div>
                <span className="kpi-label">GHG Intensity (Avg)</span>
              </div>
              <div className="[display:flex]! [align-items:baseline] [gap:8px]">
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
              <div className="kpi-footer [margin-top:16px]! [padding-top:16px]! [border-top:1px_dashed_var(--border-color)]! [font-size:var(--text-sm)]! [color:var(--text-secondary)]! [display:flex]! [justify-content:space-between] [align-items:center] [&_strong]:[color:var(--text-primary)]!">
                <span className="gwp-subtag [font-size:var(--text-sm)]! [color:var(--color-link)]! [font-weight:600]!">
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
              <div className="[display:flex]! [align-items:center] [gap:12px] [margin-bottom:16px]!">
                <div className="[&.scope1]:[background:rgba(37,_99,_235,_0.1)] [&.scope1]:[color:var(--accent-secondary)] [&&]:[&.scope3]:[background:rgba(139,_92,_246,_0.1)] [&&]:[&.scope3]:[color:var(--color-violet-700)] [width:38px]! [height:38px]! [border-radius:var(--radius-md)]! [display:flex]! [align-items:center] [justify-content:center] [flex-shrink:0] [&&]:[&&]:[&.co2]:[background:rgba(255,_102,_0,_0.1)] [&&]:[&&]:[&.co2]:[color:var(--color-link)] [&&]:[&&]:[&&]:[&.ch4]:[background:rgba(37,_99,_235,_0.1)] [&&]:[&&]:[&&]:[&.ch4]:[color:var(--accent-secondary)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[background:rgba(234,_88,_12,_0.1)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[color:var(--accent-tertiary)] scope1">
                  <Layers size={20} />
                </div>
                <span className="kpi-label">Scope 1 Direct Intensity</span>
              </div>
              <div className="[display:flex]! [align-items:baseline] [gap:8px]">
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
              <div className="kpi-footer [margin-top:16px]! [padding-top:16px]! [border-top:1px_dashed_var(--border-color)]! [font-size:var(--text-sm)]! [color:var(--text-secondary)]! [display:flex]! [justify-content:space-between] [align-items:center] [&_strong]:[color:var(--text-primary)]!">
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
              <div className="[display:flex]! [align-items:center] [gap:12px] [margin-bottom:16px]!">
                <div className="[&.scope1]:[background:rgba(37,_99,_235,_0.1)] [&.scope1]:[color:var(--accent-secondary)] [&&]:[&.scope3]:[background:rgba(139,_92,_246,_0.1)] [&&]:[&.scope3]:[color:var(--color-violet-700)] [width:38px]! [height:38px]! [border-radius:var(--radius-md)]! [display:flex]! [align-items:center] [justify-content:center] [flex-shrink:0] [&&]:[&&]:[&.co2]:[background:rgba(255,_102,_0,_0.1)] [&&]:[&&]:[&.co2]:[color:var(--color-link)] [&&]:[&&]:[&&]:[&.ch4]:[background:rgba(37,_99,_235,_0.1)] [&&]:[&&]:[&&]:[&.ch4]:[color:var(--accent-secondary)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[background:rgba(234,_88,_12,_0.1)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[color:var(--accent-tertiary)] flare">
                  <Flame size={20} />
                </div>
                <span className="kpi-label">Flaring Carbon Intensity</span>
              </div>
              <div className="[display:flex]! [align-items:baseline] [gap:8px]">
                <span className="total-value flare">
                  {(stats.avgFlaringIntensity ?? 0).toFixed(2)}
                </span>
                <span className="kpi-unit">kg CO₂e / BOE</span>
              </div>
              <div className="kpi-footer [margin-top:16px]! [padding-top:16px]! [border-top:1px_dashed_var(--border-color)]! [font-size:var(--text-sm)]! [color:var(--text-secondary)]! [display:flex]! [justify-content:space-between] [align-items:center] [&_strong]:[color:var(--text-primary)]!">
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
              <div className="[display:flex]! [align-items:center] [gap:12px] [margin-bottom:16px]!">
                <div className="[&.scope1]:[background:rgba(37,_99,_235,_0.1)] [&.scope1]:[color:var(--accent-secondary)] [&&]:[&.scope3]:[background:rgba(139,_92,_246,_0.1)] [&&]:[&.scope3]:[color:var(--color-violet-700)] [width:38px]! [height:38px]! [border-radius:var(--radius-md)]! [display:flex]! [align-items:center] [justify-content:center] [flex-shrink:0] [&&]:[&&]:[&.co2]:[background:rgba(255,_102,_0,_0.1)] [&&]:[&&]:[&.co2]:[color:var(--color-link)] [&&]:[&&]:[&&]:[&.ch4]:[background:rgba(37,_99,_235,_0.1)] [&&]:[&&]:[&&]:[&.ch4]:[color:var(--accent-secondary)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[background:rgba(234,_88,_12,_0.1)] [&&]:[&&]:[&&]:[&&]:[&.flare]:[color:var(--accent-tertiary)] scope3">
                  <ShieldCheck size={20} />
                </div>
                <span className="kpi-label">Scope 3 Value Chain</span>
              </div>
              <div className="[display:flex]! [align-items:baseline] [gap:8px]">
                <span className="total-value scope3">
                  {(stats.avgScope3Intensity ?? 0).toFixed(2)}
                </span>
                <span className="kpi-unit">kg CO₂e / BOE</span>
              </div>
              <div className="kpi-footer [margin-top:16px]! [padding-top:16px]! [border-top:1px_dashed_var(--border-color)]! [font-size:var(--text-sm)]! [color:var(--text-secondary)]! [display:flex]! [justify-content:space-between] [align-items:center] [&_strong]:[color:var(--text-primary)]!">
                <span>
                  Total S3:{" "}
                  <strong>{formatNumber(stats.totalScope3)} tCO₂e</strong>
                </span>
              </div>
              {excludedNote(stats.totalScope3, stats.usedScope3)}
            </div>
          </div>

          {/* Production Context Bar */}
          <div className="scope-breakdown [display:grid]! [grid-template-columns:repeat(4,_1fr)]! [gap:20px] [margin-top:32px]! [background:var(--bg-hover)]! [padding:24px]! [border-radius:var(--radius-md)]! [border:1px_solid_var(--border-color)]! [@media(max-width:1200px)]:[grid-template-columns:repeat(2,_1fr)]! [@media(max-width:768px)]:[grid-template-columns:1fr]!">
            <div className="scope-item [display:flex]! [flex-direction:column] [gap:8px] [&.bordered]:[border-left:1px_solid_var(--border-color)] [&.bordered]:[padding-left:20px] [&_.label]:[font-size:var(--text-sm)] [&_.label]:[color:var(--text-secondary)] [&_.label]:[font-weight:600] [&_.label]:[text-transform:uppercase] [&_.label]:[letter-spacing:0.05em] [&&]:[&&]:[&_.val]:[font-size:var(--text-lg)] [&&]:[&&]:[&_.val]:[font-weight:700] [&&]:[&_.val]:[color:var(--text-primary)] [&&]:[&&]:[&_.val]:[font-family:inherit] [&&]:[&&]:[&_.val.flare-val]:[color:var(--accent-tertiary)]">
              <span className="label">Total Oil Production</span>
              <span className="val">
                {formatNumber(stats.totalOilProduction, 0)} bbl
              </span>
            </div>
            <div className="scope-item [display:flex]! [flex-direction:column] [gap:8px] [&.bordered]:[border-left:1px_solid_var(--border-color)] [&.bordered]:[padding-left:20px] [&_.label]:[font-size:var(--text-sm)] [&_.label]:[color:var(--text-secondary)] [&_.label]:[font-weight:600] [&_.label]:[text-transform:uppercase] [&_.label]:[letter-spacing:0.05em] [&&]:[&&]:[&_.val]:[font-size:var(--text-lg)] [&&]:[&&]:[&_.val]:[font-weight:700] [&&]:[&_.val]:[color:var(--text-primary)] [&&]:[&&]:[&_.val]:[font-family:inherit] [&&]:[&&]:[&_.val.flare-val]:[color:var(--accent-tertiary)] bordered">
              <span className="label">Total Gas Production</span>
              <span className="val">
                {formatNumber(stats.totalGasProduction, 0)} mscf
              </span>
            </div>
            <div className="scope-item [display:flex]! [flex-direction:column] [gap:8px] [&.bordered]:[border-left:1px_solid_var(--border-color)] [&.bordered]:[padding-left:20px] [&_.label]:[font-size:var(--text-sm)] [&_.label]:[color:var(--text-secondary)] [&_.label]:[font-weight:600] [&_.label]:[text-transform:uppercase] [&_.label]:[letter-spacing:0.05em] [&&]:[&&]:[&_.val]:[font-size:var(--text-lg)] [&&]:[&&]:[&_.val]:[font-weight:700] [&&]:[&_.val]:[color:var(--text-primary)] [&&]:[&&]:[&_.val]:[font-family:inherit] [&&]:[&&]:[&_.val.flare-val]:[color:var(--accent-tertiary)] bordered">
              <span className="label">Combined Production (BOE)</span>
              <span
                className="val text-[color:var(--color-link)]! font-bold!"
               
              >
                {formatNumber(stats.totalBoe, 0)} BOE
              </span>
            </div>
            <div className="scope-item [display:flex]! [flex-direction:column] [gap:8px] [&.bordered]:[border-left:1px_solid_var(--border-color)] [&.bordered]:[padding-left:20px] [&_.label]:[font-size:var(--text-sm)] [&_.label]:[color:var(--text-secondary)] [&_.label]:[font-weight:600] [&_.label]:[text-transform:uppercase] [&_.label]:[letter-spacing:0.05em] [&&]:[&&]:[&_.val]:[font-size:var(--text-lg)] [&&]:[&&]:[&_.val]:[font-weight:700] [&&]:[&_.val]:[color:var(--text-primary)] [&&]:[&&]:[&_.val]:[font-family:inherit] [&&]:[&&]:[&_.val.flare-val]:[color:var(--accent-tertiary)] bordered">
              <span className="label">Total Gas Flared</span>
              <span className="val flare-val">
                {formatNumber(stats.totalFlaringVolume, 0)} m³
              </span>
            </div>
          </div>
        </div>
);

export default CarbonIntensityCarbonIntensity;
