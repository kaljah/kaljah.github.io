import React, { useState } from "react";
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
import { t } from "../../i18n";

const DEFAULT_LINE_COLORS = [
  "var(--color-brand-500)", // Core orange
  "var(--color-blue-600)", // Royal blue
  "var(--color-green-500)", // Emerald green
  "var(--color-violet-500)", // Violet
  "var(--color-amber-500)", // Amber
  "var(--color-cyan-500)", // Cyan
  "var(--color-pink-500)", // Rose
  "var(--color-ink-500)", // Slate
];

export interface LineSeriesConfig {
  dataKey?: string;
  key?: string;
  name?: string;
  label?: string;
  color?: string;
  isTrajectory?: boolean;
  strokeWidth?: number;
  strokeDasharray?: string;
  dash?: string;
}

export interface LineChartProps {
  data?: any[];
  lines?: LineSeriesConfig[];
  series?: LineSeriesConfig[]; // Alias for lines
  xKey?: string;
  xAxisKey?: string;
  title?: string;
  height?: number | string;
  showLegend?: boolean;
  formatValue?: (val: any) => string;
}

export const LineChart: React.FC<LineChartProps> = ({
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
  const [isMounted] = useState<boolean>(() => typeof window !== "undefined");
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const finalXKey = xAxisKey || xKey || "name";
  const chartLines = lines.length > 0 ? lines : series;

  const defaultFormat = (val: any): string => {
    if (val === null || val === undefined || isNaN(val)) return "0";
    const num = Number(val);
    if (!isFinite(num)) return "0";
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}k`;
    return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
  };

  const valueFormatter = formatValue || defaultFormat;

  const renderTooltip = ({ active, payload }: any) => {
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
              {payload.length} {payload.length === 1 ? t("metric") : t("metrics")}
            </span>
          </div>
          <div className="tooltip-items-list">
            {payload.map((entry: any, idx: number) => (
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

  const renderLegend = ({ payload }: any) => {
    if (!payload || payload.length === 0) return null;
    return (
      <div className="modern-chart-legend">
        {payload.map((entry: any, idx: number) => {
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
          <span>{t("No trend data available")}</span>
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
      <ResponsiveContainer
        width="100%"
        height={typeof height === "number" ? height : (parseInt(String(height), 10) || 300)}
        debounce={100}
      >
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
            stroke="var(--color-ink-300)"
            tick={{ fill: "var(--color-ink-500)", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            dy={8}
            padding={{ left: 16, right: 16 }}
          />

          <YAxis
            stroke="var(--color-ink-300)"
            tick={{ fill: "var(--color-ink-500)", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={valueFormatter}
            dx={-4}
          />

          <Tooltip
            content={renderTooltip}
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
                        fill: "var(--color-white)",
                        stroke: lineColor,
                        strokeWidth: 2,
                        r: 3.5,
                      }
                }
                activeDot={{
                  fill: lineColor,
                  stroke: "var(--color-white)",
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
