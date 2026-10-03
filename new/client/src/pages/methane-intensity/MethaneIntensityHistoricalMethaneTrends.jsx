import React from "react";
import { BarChart2, Grid } from "lucide-react";
import { LineChart } from "../../components/charts";

// Extracted from MethaneIntensity.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MethaneIntensityHistoricalMethaneTrends = ({ getHeatmapClass, midstreamTargetPct, rawTrendData, regionalData, setTrendView, trendChartData, trendView, upstreamTargetPct }) => (
<div className="card trend-section">
          <div className="chart-header">
            <div>
              <h3 className="mb-[4px]!">
                Historical Methane Trends & Targets
              </h3>
              <p
                className="text-[color:var(--text-secondary)]! text-[length:0.9rem]! m-[0px]!"
              >
                5-Year Methane Loss Rate (%) vs OGMP 2.0 Targets (&le;{upstreamTargetPct.toFixed(2)}% Upstream / &le;{midstreamTargetPct.toFixed(2)}% Midstream)
              </p>
            </div>
            <div className="[display:flex] [gap:12px] [align-items:center]">
              <div className="[background:var(--bg-hover)] [padding:4px] [border-radius:var(--radius-md)] [display:flex] [gap:4px] [border:1px_solid_var(--border-color)]">
                <button
                  className={`view-btn ${trendView === "chart" ? "active" : ""}`}
                  onClick={() => setTrendView("chart")}
                >
                  <BarChart2 size={16} /> Chart
                </button>
                <button
                  className={`view-btn ${trendView === "heatmap" ? "active" : ""}`}
                  onClick={() => setTrendView("heatmap")}
                >
                  <Grid size={16} /> Heatmap
                </button>
              </div>
            </div>
          </div>

          {trendView === "chart" ? (
            <div className="h-[350px]!">
              <LineChart
                data={trendChartData}
                xKey="year"
                series={[
                  {
                    key: "loss_rate_pct",
                    color: "#2563eb",
                    name: "Overall Loss Rate (%)",
                  },
                  {
                    key: "loss_rate_upstream_pct",
                    color: "#c2410c",
                    name: "Upstream Loss Rate (%)",
                  },
                  {
                    key: "loss_rate_midstream_pct",
                    color: "#f59e0b",
                    name: "Midstream Loss Rate (%)",
                  },
                  {
                    key: "target_020",
                    color: "#10b981",
                    name: `OGMP Upstream Target (≤${upstreamTargetPct.toFixed(2)}%)`,
                    strokeDasharray: "4 4",
                  },
                  {
                    key: "target_005",
                    color: "#8b5cf6",
                    name: `OGMP Midstream Target (≤${midstreamTargetPct.toFixed(2)}%)`,
                    strokeDasharray: "2 2",
                  },
                ]}
              />
            </div>
          ) : (
            <div className="heatmap-container">
              <div className="heatmap-header">
                <div
                  className="[font-size:var(--text-sm)] [font-weight:700] [color:var(--text-secondary)] [text-transform:uppercase] [text-align:center] [letter-spacing:0.05em] text-left!"
                 
                >
                  FACILITY / REGION
                </div>
                {rawTrendData.map((d) => (
                  <div key={d.year} className="[font-size:var(--text-sm)] [font-weight:700] [color:var(--text-secondary)] [text-transform:uppercase] [text-align:center] [letter-spacing:0.05em]">
                    {d.year}
                  </div>
                ))}
              </div>
              <div className="heatmap-body">
                {regionalData.length > 0 ? (
                  regionalData.map((facData) => (
                    <div key={facData.facility_id} className="heatmap-row">
                      <div className="[font-weight:600] [font-size:var(--text-base)] [color:var(--text-primary)]">
                        {facData.facility_name}
                      </div>
                      {rawTrendData.map((yData) => {
                        const record = yData.data.find(
                          (r) => r.facility_id === facData.facility_id,
                        );
                        const missing = record && record.methane_loss_rate_pct == null && record.total_ch4 > 0;
                        const rawVal = record ? record.methane_loss_rate_pct || 0 : 0;
                        const numVal = Number(rawVal);
                        const val = isFinite(numVal) ? numVal : 0;
                        return (
                          <div
                            key={yData.year}
                            className={`heatmap-cell ${missing ? "" : getHeatmapClass(val)}`}
                            title={missing ? `${yData.year}: methane reported but no gas production recorded` : `${yData.year} Loss Rate: ${val.toFixed(3)}%`}
                          >
                            {missing ? "n/a" : val > 0 ? `${val.toFixed(3)}%` : "-"}
                          </div>
                        );
                      })}
                    </div>
                  ))
                ) : (
                  <p
                    className="text-center! p-[40px]! text-[color:var(--text-secondary)]!"
                  >
                    No regional data available
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
);

export default MethaneIntensityHistoricalMethaneTrends;
