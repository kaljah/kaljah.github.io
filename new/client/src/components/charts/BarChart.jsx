import React from "react";
import {
  BarChart as RechartsBar,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import "./ChartWrappers.css";

export const BarChart = ({
  data,
  dataKey,
  key: barKey,
  bars = [],
  xKey = "name",
  xAxisKey,
  title,
  color = "#10b981",
  height = 300,
  showLegend = true,
  formatValue = (val) => {
    if (val === null || val === undefined) return "0";
    if (Math.abs(val) >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (Math.abs(val) >= 1000) return `${(val / 1000).toFixed(1)}k`;
    return Number(val).toLocaleString();
  },
}) => {
  const finalXKey = xAxisKey || xKey || "name";
  const finalDataKey = dataKey || barKey || "value";

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const label = payload[0].payload && payload[0].payload[finalXKey]
        ? payload[0].payload[finalXKey]
        : "";
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{label}</p>
          {payload.map((entry, idx) => (
            <p
              key={idx}
              className="tooltip-value"
              style={{ color: entry.color || entry.fill }}
            >
              {entry.name || entry.dataKey}: {formatValue(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-wrapper">
      {title && <h3 className="chart-title">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBar data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#e2e8f0"
            vertical={false}
          />
          <XAxis
            dataKey={finalXKey}
            stroke="#cbd5e1"
            tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            stroke="#cbd5e1"
            tick={{ fill: "#475569", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatValue}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(241, 245, 249, 0.6)" }} />
          {showLegend && <Legend />}
          {bars && bars.length > 0 ? (
            bars.map((b, idx) => (
              <Bar
                key={idx}
                dataKey={b.dataKey}
                name={b.name || b.dataKey}
                fill={b.color || color}
                stackId={b.stackId}
                radius={b.stackId ? [0, 0, 0, 0] : [6, 6, 0, 0]}
              />
            ))
          ) : (
            <Bar dataKey={finalDataKey} fill={color} radius={[6, 6, 0, 0]} />
          )}
        </RechartsBar>
      </ResponsiveContainer>
    </div>
  );
};

export default BarChart;

