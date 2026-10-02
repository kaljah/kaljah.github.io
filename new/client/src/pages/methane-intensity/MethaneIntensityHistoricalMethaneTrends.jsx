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
                style={{
                  color: "var(--text-secondary)",
                  fontSize: "0.9rem",
                  margin: 0,
                }}
              >
                5-Year Methane Loss Rate (%) vs OGMP 2.0 Targets (&le;{upstreamTargetPct.toFixed(2)}% Upstream / &le;{midstreamTargetPct.toFixed(2)}% Midstream)
              </p>
            </div>
            <div className="trend-view-controls">
              <div className="view-toggle">
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
                  className="heatmap-header-cell text-left!"
                 
                >
                  FACILITY / REGION
                </div>
                {rawTrendData.map((d) => (
                  <div key={d.year} className="heatmap-header-cell">
                    {d.year}
                  </div>
                ))}
              </div>
              <div className="heatmap-body">
                {regionalData.length > 0 ? (
                  regionalData.map((facData) => (
                    <div key={facData.facility_id} className="heatmap-row">
                      <div className="heatmap-label">
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
                    style={{
                      textAlign: "center",
                      padding: "40px",
                      color: "var(--text-secondary)",
                    }}
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
