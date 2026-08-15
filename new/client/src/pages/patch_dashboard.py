import re

with open('DashboardEnhanced.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add sbtiData state
sbti_state = """  const [sbtiData, setSbtiData] = useState(null);
  const [sbtiLoading, setSbtiLoading] = useState(false);"""
content = content.replace("  const [trendData, setTrendData] = useState([]);", sbti_state + "\n  const [trendData, setTrendData] = useState([]);")

# 2. Fetch SBTi Data
fetch_sbti = """      // Fetch SBTi Trajectory Data
      try {
        setSbtiLoading(true);
        const sbtiRes = await api.get('/dashboard/sbti-trajectory');
        if (sbtiRes.data && sbtiRes.data.has_target) {
            setSbtiData(sbtiRes.data);
        } else {
            setSbtiData(null);
        }
      } catch (err) {
        console.error("Failed to load SBTi data", err);
      } finally {
        setSbtiLoading(false);
      }
"""
content = content.replace("      setCategoricalData(catData);", "      setCategoricalData(catData);\n\n" + fetch_sbti)

# 3. Add SBTi Chart below the main chart
sbti_chart = """
          {/* SBTi Trajectory Chart */}
          {sbtiData && sbtiData.trajectory && sbtiData.trajectory.length > 0 && (
            <div className="card full-width-card glass-panel" style={{ marginTop: '24px' }}>
              <div className="card-header-row">
                <div>
                  <h3 className="card-subtitle">SBTi Trajectory Pathway ({sbtiData.pathway_type})</h3>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                    Tracking emissions against Science Based Targets from Base Year {sbtiData.base_year} to Target Year {sbtiData.target_year}
                  </p>
                </div>
              </div>
              <div className="chart-container" style={{ height: "400px", width: "100%" }}>
                <LineChartWrapper
                  data={sbtiData.trajectory}
                  xAxisKey="year"
                  series={[
                    {
                      dataKey: "actual",
                      name: "Actual Emissions (Verified)",
                      color: "#3b82f6",
                      strokeWidth: 3
                    },
                    {
                      dataKey: "sbti_target",
                      name: "SBTi Target Pathway",
                      color: "#10b981",
                      strokeDasharray: "5 5",
                      strokeWidth: 2
                    },
                    {
                      dataKey: "bau_projection",
                      name: "Business as Usual",
                      color: "#ef4444",
                      strokeDasharray: "3 3",
                      strokeWidth: 2
                    }
                  ]}
                  height={400}
                />
              </div>
            </div>
          )}
"""
content = content.replace("          {/* Donut Charts - Side by Side */}", sbti_chart + "\n          {/* Donut Charts - Side by Side */}")

with open('DashboardEnhanced.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching DashboardEnhanced.jsx for SBTi chart")
