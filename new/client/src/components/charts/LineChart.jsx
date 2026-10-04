import React, { useState, useEffect, useMemo } from "react";
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

const DEFAULT_LINE_COLORS = [
  "#ff6600", // Core orange
  "#2563eb", // Royal blue
  "#10b981", // Emerald green
  "#8b5cf6", // Violet
  "#f59e0b", // Amber
  "#06b6d4", // Cyan
  "#ec4899", // Rose
  "#64748b", // Slate
];

export const LineChart = ({
  data,
  lines = [],
  series = [], // Alias for lines
  xKey = "name",
  xAxisKey,
  title,
  height = 300,
  showLegend = true,
  formatValue,
}) => {
  const [isMounted, setIsMounted] = useState(false);
  const [activeKey, setActiveKey] = useState(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const finalXKey = xAxisKey || xKey || "name";
  const chartLines = lines.length > 0 ? lines : series;

  const defaultFormat = (val) => {
    if (val === null || val === undefined || isNaN(val)) return "0";
    const num = Number(val);
    if (!isFinite(num)) return "0";
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}k`;
    return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
  };

  const valueFormatter = formatValue || defaultFormat;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const xVal =
        payload[0].payload && payload[0].payload[finalXKey] !== undefined
          ? payload[0].payload[finalXKey]
          : "";

      return (
        <div className="modern-chart-tooltip">
          <div className="tooltip-header">
            <span className="tooltip-label">{xVal}</span>
            <span className="tooltip-badge">
              {payload.length} {payload.length === 1 ? "metric" : "metrics"}
            </span>
          </div>
          <div className="tooltip-items-list">
            {payload.map((entry, idx) => (
              <div key={idx} className="tooltip-item-row">
                <div className="tooltip-item-left">
                  <span
                    className="tooltip-color-dot"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span title={entry.name}>{entry.name}</span>
                </div>
                <div className="tooltip-item-right">
                  <span>{valueFormatter(entry.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  const renderLegend = ({ payload }) => {
    if (!payload || payload.length === 0) return null;
    return (
      <div className="modern-chart-legend">
        {payload.map((entry, idx) => {
          const isDimmed = activeKey !== null && activeKey !== entry.dataKey;
          return (
            <div
              key={`legend-${idx}`}
              className={`legend-item-pill ${isDimmed ? "dimmed" : ""}`}
              onMouseEnter={() => setActiveKey(entry.dataKey)}
              onMouseLeave={() => setActiveKey(null)}
            >
              <span
                className="legend-item-dot"
                style={{ backgroundColor: entry.color }}
              />
              <span className="legend-item-name">{entry.value}</span>
            </div>
          );
        })}
      </div>
    );
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
      <div
        className="chart-wrapper empty"
        style={{ height: typeof height === "number" ? `${height}px` : height }}
      >
        <div className="chart-empty-content">
          <div className="chart-empty-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <span>No trend data available</span>
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
      <ResponsiveContainer width="100%" height={height} debounce={100}>
        <AreaChart
          data={data}
          margin={{ top: 12, right: 12, left: -4, bottom: 4 }}
        >
          <defs>
            {chartLines.map((line, idx) => {
              const lineKey = line.dataKey || line.key || `line_${idx}`;
              const cleanKey = String(lineKey).replace(/[^a-zA-Z0-9_-]/g, "_");
              const strokeColor =
                line.color || DEFAULT_LINE_COLORS[idx % DEFAULT_LINE_COLORS.length];

              return (
                <linearGradient
                  key={`gradient-${cleanKey}`}
                  id={`gradient-${cleanKey}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={strokeColor} stopOpacity={0.24} />
                  <stop offset="80%" stopColor={strokeColor} stopOpacity={0.02} />
                  <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                </linearGradient>
              );
            })}
          </defs>

          <CartesianGrid
            strokeDasharray="4 4"
            stroke="rgba(226, 232, 240, 0.75)"
            vertical={false}
          />

          <XAxis
            dataKey={finalXKey}
            type="category"
            stroke="#cbd5e1"
            tick={{ fill: "#64748b", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            dy={8}
            padding={{ left: 16, right: 16 }}
          />

          <YAxis
            stroke="#cbd5e1"
            tick={{ fill: "#64748b", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={valueFormatter}
            dx={-4}
          />

          <Tooltip
            content={<CustomTooltip />}
            cursor={{
              stroke: "rgba(203, 213, 225, 0.9)",
              strokeWidth: 1.5,
              strokeDasharray: "4 4",
            }}
          />

          {showLegend && chartLines.length > 0 && (
            <Legend content={renderLegend} verticalAlign="bottom" />
          )}

          {chartLines.map((line, idx) => {
            const lineKey = line.dataKey || line.key || "value";
            const cleanKey = String(lineKey).replace(/[^a-zA-Z0-9_-]/g, "_");
            const lineColor =
              line.color || DEFAULT_LINE_COLORS[idx % DEFAULT_LINE_COLORS.length];
            const lineName = line.name || line.label || lineKey;

            const isTrajectory = Boolean(
              line.isTrajectory ||
                String(lineKey).toLowerCase().includes("trajectory") ||
                String(lineKey).toLowerCase().includes("target") ||
                String(lineKey).toLowerCase().includes("bau") ||
                String(lineKey).toLowerCase().includes("benchmark") ||
                line.strokeDasharray ||
                line.dash
            );

            const isDimmed = activeKey !== null && activeKey !== lineKey;
            const isHighlighted = activeKey === lineKey;

            return (
              <Area
                key={`area-${cleanKey}`}
                type="monotone"
                dataKey={lineKey}
                name={lineName}
                stroke={lineColor}
                strokeWidth={
                  isHighlighted
                    ? (line.strokeWidth || 3) + 1
                    : line.strokeWidth || (isTrajectory ? 2 : 2.75)
                }
                strokeDasharray={
                  line.strokeDasharray ||
                  line.dash ||
                  (isTrajectory ? "4 4" : undefined)
                }
                fillOpacity={isTrajectory ? 0 : isDimmed ? 0.05 : 1}
                fill={isTrajectory ? "transparent" : `url(#gradient-${cleanKey})`}
                opacity={isDimmed ? 0.35 : 1}
                dot={
                  isTrajectory || data.length > 15
                    ? false
                    : {
                        fill: "#ffffff",
                        stroke: lineColor,
                        strokeWidth: 2,
                        r: 3.5,
                      }
                }
                activeDot={{
                  fill: lineColor,
                  stroke: "#ffffff",
                  strokeWidth: 2.5,
                  r: isTrajectory ? 4.5 : 6,
                }}
                animationDuration={900}
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
