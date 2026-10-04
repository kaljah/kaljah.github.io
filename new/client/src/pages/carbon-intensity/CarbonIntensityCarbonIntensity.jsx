import React from "react";
import { Activity, Cloud, Flame, Layers, ShieldCheck } from "lucide-react";
import { Badge, SegmentedControl } from "../../ui";
import { formatNumber } from "../../utils/formatters";
import { getActiveGwpFactors } from "../../constants";
import { HeroPanel, KpiGrid, KpiTile, ProdBar, ProdItem } from "../intensity/IntensityParts";

const fixed = (v) => (v ?? 0).toFixed(2);

/** KPI hero for Carbon Intensity: four intensity tiles, the GWP horizon switch and the production context bar. */
const CarbonIntensityCarbonIntensity = ({ activeGwpStandard, currentDisplayCo2Intensity, currentDisplayScope1Intensity, currentDisplayTotalCo2e, currentDisplayTotalScope1, currentUsedCo2e, currentUsedScope1, excludedNote, gwpHorizon, selectedYear, setGwpHorizon, stats }) => {
  const f100 = getActiveGwpFactors(activeGwpStandard, "100");
  const f20 = getActiveGwpFactors(activeGwpStandard, "20");
  const unit = "kg CO₂e / BOE";
  return (
    <HeroPanel
      icon={Activity}
      title="Carbon Intensity & Product Embodiment"
      badge={
        <Badge tone="brand" className="year-badge px-4 py-1.5 text-base">
          {selectedYear === "all" ? "All-Time" : selectedYear} Performance
        </Badge>
      }
      actions={
        <div className="flex items-center gap-2.5 rounded-md border border-border bg-ink-100 px-2 py-1">
          <span className="text-sm font-semibold text-text-secondary">GWP Horizon:</span>
          <SegmentedControl
            label="GWP horizon"
            size="sm"
            value={gwpHorizon}
            onChange={setGwpHorizon}
            options={[
              { value: "100", label: `${activeGwpStandard} 100-Yr`, title: `IPCC ${activeGwpStandard} 100-Year GWP (CH4: ${f100.CH4}, N2O: ${f100.N2O})` },
              { value: "20", label: `${activeGwpStandard} 20-Yr`, title: `IPCC ${activeGwpStandard} 20-Year GWP (CH4: ${f20.CH4}, N2O: ${f20.N2O})` },
            ]}
          />
        </div>
      }
    >
      <KpiGrid>
        <KpiTile
          icon={Cloud}
          tone="co2"
          label="GHG Intensity (Avg)"
          pending={currentDisplayCo2Intensity === null}
          value={currentDisplayCo2Intensity === null ? "Pending Production" : fixed(currentDisplayCo2Intensity)}
          unit={unit}
          footer={
            <>
              <span className="gwp-subtag text-sm font-semibold text-link">{gwpHorizon === "20" ? "GWP₂₀ Active" : "GWP₁₀₀ Standard"}</span>
              <span>
                Total: <strong>{formatNumber(currentDisplayTotalCo2e)} tCO₂e</strong>
              </span>
            </>
          }
          note={excludedNote(currentDisplayTotalCo2e, currentUsedCo2e)}
        />
        <KpiTile
          icon={Layers}
          tone="scope1"
          label="Scope 1 Direct Intensity"
          pending={currentDisplayScope1Intensity === null}
          value={currentDisplayScope1Intensity === null ? "Pending Production" : fixed(currentDisplayScope1Intensity)}
          unit={unit}
          footer={
            <>
              <span>
                Scope 2: <strong>{stats.avgScope2Intensity === null ? "Pending" : `${fixed(stats.avgScope2Intensity)} kg/BOE`}</strong>
              </span>
              <span>
                Total S1: <strong>{formatNumber(currentDisplayTotalScope1)} t</strong>
              </span>
            </>
          }
          note={excludedNote(currentDisplayTotalScope1, currentUsedScope1)}
        />
        <KpiTile
          icon={Flame}
          tone="flare"
          label="Flaring Carbon Intensity"
          value={fixed(stats.avgFlaringIntensity)}
          unit={unit}
          footer={
            <span>
              Flared: <strong>{formatNumber(stats.totalFlaringEmissions)} tCO₂e</strong>
            </span>
          }
          note={excludedNote(stats.totalFlaringEmissions, stats.usedFlaring)}
        />
        <KpiTile
          icon={ShieldCheck}
          tone="scope3"
          label="Scope 3 Value Chain"
          value={fixed(stats.avgScope3Intensity)}
          unit={unit}
          footer={
            <span>
              Total S3: <strong>{formatNumber(stats.totalScope3)} tCO₂e</strong>
            </span>
          }
          note={excludedNote(stats.totalScope3, stats.usedScope3)}
        />
      </KpiGrid>

      <ProdBar>
        <ProdItem bordered={false} label="Total Oil Production" value={`${formatNumber(stats.totalOilProduction, 0)} bbl`} />
        <ProdItem label="Total Gas Production" value={`${formatNumber(stats.totalGasProduction, 0)} mscf`} />
        <ProdItem label="Combined Production (BOE)" value={`${formatNumber(stats.totalBoe, 0)} BOE`} accent="text-link" />
        <ProdItem label="Total Gas Flared" value={`${formatNumber(stats.totalFlaringVolume, 0)} m³`} accent="text-brand-600" />
      </ProdBar>
    </HeroPanel>
  );
};

export default CarbonIntensityCarbonIntensity;
