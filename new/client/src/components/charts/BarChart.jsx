import React, { useState, useEffect } from "react";
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
    if (val === null || val === undefined || isNaN(val)) return "0";
    const num = Number(val);
    if (!isFinite(num)) return "0";
    if (Math.abs(num) >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (Math.abs(num) >= 1000) return `${(num / 1000).toFixed(1)}k`;
    return num.toLocaleString();
  },
}) => {
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const finalXKey = xAxisKey || xKey || "name";
  const finalDataKey = dataKey || barKey || "value";

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const label = payload[0].payload && payload[0].payload[finalXKey]
        ? payload[0].payload[finalXKey]
        : "";
      return (
        <div className="[background:rgba(255,_255,_255,_0.95)]! [backdrop-filter:blur(8px)] [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [padding:12px_16px]! [box-shadow:var(--shadow-card)]!">
          <p className="[margin:0_0_6px_0]! [font-size:var(--text-base)]! [color:var(--color-ink-500)]! [font-weight:600]!">{label}</p>
          {payload.map((entry, idx) => (
            <p
              key={idx}
              className="[margin:0]! [font-size:var(--text-md)]! [font-weight:700]! [color:var(--color-ink-800)]!"
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

  if (!isMounted) {
    return (
      <div
        style={{
          height: typeof height === "number" ? `${height}px` : height,
          width: "100%",
        }}
      />
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="[background:var(--color-white)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [padding:20px]! [margin-bottom:20px]! [box-shadow:var(--shadow-xs)]! empty">
        <div
          style={{
            height,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-muted, #94a3b8)",
          }}
        >
          No data available
        </div>
      </div>
    );
  }

  return (
    <div className="[background:var(--color-white)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [padding:20px]! [margin-bottom:20px]! [box-shadow:var(--shadow-xs)]!">
      {title && <h3 className="[margin:0_0_16px_0]! [font-size:var(--text-lg)]! [font-weight:600]! [color:var(--text-primary)]!">{title}</h3>}
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

