import React, { useMemo } from "react";
import { BarChart2, Grid } from "lucide-react";
import { LineChart } from "../../components/charts";
import { activateOnKey } from "../../utils/a11yKeys";
import { t } from "../../i18n";

export interface MethaneIntensityHistoricalMethaneTrendsProps {
  getHeatmapClass: (val: number) => string;
  /** Clicking a cell opens that facility's records for that year. */
  onOpenCell?: (facilityId: number | string, year: number | string) => void;
  midstreamTargetPct: number;
  rawTrendData: { year: number | string; data: any[] }[];
  regionalData: { facility_id: number | string; facility_name: string; [key: string]: any }[];
  setTrendView: (view: "chart" | "heatmap") => void;
  trendChartData: any[];
  trendView: "chart" | "heatmap" | string;
  upstreamTargetPct: number;
}

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityHistoricalMethaneTrends: React.FC<MethaneIntensityHistoricalMethaneTrendsProps> = ({
  getHeatmapClass,
  onOpenCell,
  midstreamTargetPct,
  rawTrendData,
  regionalData,
  setTrendView,
  trendChartData,
  trendView,
  upstreamTargetPct,
}) => {
  const regionalRows = useMemo(() => {
    const map = new Map<string, { id: number | string; name: string; facIds: (number | string)[] }>();
    regionalData.forEach((fac) => {
      const regName = fac.region || fac.facility_name;
      if (!map.has(regName)) {
        map.set(regName, { id: fac.facility_id, name: regName, facIds: [] });
      }
      map.get(regName)!.facIds.push(fac.facility_id);
    });
    return Array.from(map.values());
  }, [regionalData]);

  return (
    <div className="card trend-section mt-2">
      <div className="chart-header">
        <div>
          <h3 className="mb-1">
            {t("Historical Methane Trends & Targets")}
          </h3>
          <p className="text-text-secondary text-sm m-0">
            {t("5-Year Methane Loss Rate (%) vs OGMP 2.0 Targets (≤")}{upstreamTargetPct.toFixed(2)}{t("% Upstream / ≤")}{midstreamTargetPct.toFixed(2)}{t("% Midstream)")}
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <div className="bg-ink-100 p-1 rounded-md flex gap-1 border border-border">
            <button
              className={`view-btn ${trendView === "chart" ? "active" : ""}`}
              onClick={() => setTrendView("chart")}
            >
              <BarChart2 size={16} />{" "}{t("Chart")}
            </button>
            <button
              className={`view-btn ${trendView === "heatmap" ? "active" : ""}`}
              onClick={() => setTrendView("heatmap")}
            >
              <Grid size={16} />{" "}{t("Heatmap")}
            </button>
          </div>
        </div>
      </div>

      {trendView === "chart" ? (
        <div className="h-[380px]">
          <LineChart
            data={trendChartData}
            xKey="year"
            formatValue={(v) => `${Number(v || 0).toFixed(2)}%`}
            height={380}
            series={[
              {
                key: "loss_rate_pct",
                color: "var(--color-blue-600)",
                name: t("Overall Loss Rate (%)"),
              },
              {
                key: "loss_rate_upstream_pct",
                color: "var(--color-brand-700)",
                name: t("Upstream Loss Rate (%)"),
              },
              {
                key: "loss_rate_midstream_pct",
                color: "var(--color-amber-500)",
                name: t("Midstream Loss Rate (%)"),
              },
              {
                key: "target_020",
                color: "var(--color-green-500)",
                name: t("OGMP Upstream Target (≤{{value}}%)", { value: upstreamTargetPct.toFixed(2) }),
                strokeDasharray: "4 4",
              },
              {
                key: "target_005",
                color: "var(--color-violet-500)",
                name: t("OGMP Midstream Target (≤{{value}}%)", { value: midstreamTargetPct.toFixed(2) }),
                strokeDasharray: "2 2",
              },
            ]}
          />
        </div>
      ) : (
        <div className="heatmap-container mt-6 overflow-x-auto bg-ink-50 rounded-md border border-border p-4">
          <div className="heatmap-header grid grid-cols-[200px_repeat(5,_1fr)] gap-3 mb-4 px-3">
            <div className="text-xs font-medium text-text-secondary text-left">
              {t("Region")}
            </div>
            {rawTrendData.map((d) => (
              <div key={d.year} className="text-xs font-medium text-text-secondary text-center">
                {d.year}
              </div>
            ))}
          </div>
          <div className="heatmap-body">
            {regionalRows.length > 0 ? (
              regionalRows.map((regData) => (
                <div key={regData.name} className="heatmap-row grid grid-cols-[200px_repeat(5,_1fr)] gap-3 p-3 border-b border-border items-center transition-colors last:border-b-0 hover:bg-surface hover:rounded-md hover:shadow-xs">
                  <div className="font-semibold text-base text-text">
                    {regData.name}
                  </div>
                  {rawTrendData.map((yData) => {
                    const records = yData.data.filter((r: any) => regData.facIds.includes(r.facility_id));
                    let totalGasM3 = 0;
                    let totalCh4GasM3 = 0;
                    let hasMissing = false;
                    records.forEach((record: any) => {
                      if (record && record.methane_loss_rate_pct == null && record.total_ch4 > 0) {
                        hasMissing = true;
                      }
                      if (record && record.methane_loss_rate_pct != null) {
                        const gm3 = record.total_gas_m3 || (record.total_gas || 0) * 28.3168;
                        totalGasM3 += gm3;
                        totalCh4GasM3 += (record.methane_loss_rate_pct / 100.0) * gm3;
                      }
                    });
                    const val = totalGasM3 > 0 ? (totalCh4GasM3 / totalGasM3) * 100.0 : 0;
                    const missing = hasMissing && totalGasM3 === 0;
                    return (
                      <div
                        key={yData.year}
                        className={`heatmap-cell tabular-nums ${missing ? "" : getHeatmapClass(val)} ${onOpenCell ? "cursor-pointer" : ""}`}
                        role={onOpenCell ? "button" : undefined}
                        tabIndex={onOpenCell ? 0 : undefined}
                        aria-label={onOpenCell ? t("Open {{facility}} records for {{year}}", { facility: regData.name, year: yData.year }) : undefined}
                        onClick={onOpenCell ? () => onOpenCell(regData.id, yData.year) : undefined}
                        onKeyDown={onOpenCell ? activateOnKey : undefined}
                        title={missing ? t("{{year}}: methane reported but no gas production recorded", { year: yData.year }) : t("{{year}} Loss Rate: {{pct}}%", { year: yData.year, pct: val.toFixed(3) })}
                      >
                        {missing ? "n/a" : val > 0 ? `${val.toFixed(3)}%` : "-"}
                      </div>
                    );
                  })}
                </div>
              ))
            ) : (
              <p className="text-center p-10 text-text-secondary">
                {t("No regional data available")}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MethaneIntensityHistoricalMethaneTrends;
