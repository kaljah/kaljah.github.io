import React, { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import "./ChartWrappers.css";

export const LineChart = ({
  data,
  lines = [],
  series = [], // Alias for lines
  xKey = "name",
  title,
  height = 300,
  showLegend = true,
  formatValue = (val) => {
    if (Math.abs(val) >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
    if (Math.abs(val) >= 1000) return `${(val / 1000).toFixed(1)}k`;
    return val.toLocaleString();
  },
}) => {
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const chartLines = lines.length > 0 ? lines : series;
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const label =
        payload[0].payload && payload[0].payload[xKey]
          ? payload[0].payload[xKey]
          : "";
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{label}</p>
          {payload.map((entry, idx) => (
            <p
              key={idx}
              className="tooltip-value"
              style={{ color: entry.color }}
            >
              {entry.name}: {formatValue(entry.value)}
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
      <div className="chart-wrapper empty">
        <div
          style={{
            height,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "rgba(255,255,255,0.3)",
          }}
        >
          No trend data available
        </div>
      </div>
    );
  }

  return (
    <div
      className="chart-wrapper"
      style={{
        height: "100%",
        width: "100%",
        minWidth: 0,
        padding: 0,
        background: "transparent",
        boxShadow: "none",
        border: "none",
      }}
    >
      {title && <h3 className="chart-title">{title}</h3>}
      <ResponsiveContainer width="99%" height={height} debounce={200}>
        <AreaChart
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorScope1" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff6600" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#ff6600" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorScope2" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#e2e8f0"
            vertical={false}
          />
          <XAxis
            dataKey={xKey}
            type="category"
            stroke="#94a3b8"
            tick={{ fill: "#64748b", fontSize: 11, fontWeight: 500 }}
            axisLine={false}
            tickLine={false}
            padding={{ left: 20, right: 20 }}
          />
          <YAxis
            stroke="#94a3b8"
            tick={{ fill: "#64748b", fontSize: 11, fontWeight: 500 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatValue}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{
              stroke: "#cbd5e1",
              strokeWidth: 1,
              strokeDasharray: "4 4",
            }}
          />
          {showLegend && chartLines.length > 0 && (
            <Legend wrapperStyle={{ color: "var(--text-primary)" }} />
          )}
          {chartLines.map((line, idx) => {
            const isTrajectory = line.dataKey === "trajectory";
            const isArea =
              (line.dataKey === "scope1" ||
                line.dataKey === "scope2" ||
                line.dataKey === "emissions") &&
              !isTrajectory;
            const gradientId =
              line.dataKey === "scope2" ? "colorScope2" : "colorScope1";

            return (
              <Area
                key={idx}
                type="monotone"
                dataKey={line.dataKey || line.key || "value"}
                name={line.name}
                stroke={line.color}
                strokeWidth={isTrajectory ? 2 : 3}
                strokeDasharray={
                  line.strokeDasharray || (isTrajectory ? "5 5" : "0")
                }
                fillOpacity={isArea ? 0.3 : 0}
                fill={isArea ? `url(#${gradientId})` : "transparent"}
                dot={
                  isTrajectory
                    ? false
                    : {
                        fill: "#ffffff",
                        stroke: line.color,
                        strokeWidth: 2,
                        r: 4,
                      }
                }
                activeDot={
                  isTrajectory
                    ? { r: 4 }
                    : { fill: line.color, stroke: "#fff", strokeWidth: 2, r: 6 }
                }
                animationDuration={1500}
                connectNulls
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default LineChart;
