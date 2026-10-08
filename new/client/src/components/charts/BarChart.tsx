import React, { useId, useState } from "react";
import {
  BarChart as RechartsBar,
  Bar,
  Cell,
  LabelList,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import "./ChartWrappers.css";

const MODERN_BAR_PALETTE = [
  "var(--color-brand-500)",
  "var(--color-blue-600)",
  "var(--color-green-500)",
  "var(--color-violet-500)",
  "var(--color-amber-500)",
  "var(--color-cyan-500)",
];

export interface BarItemConfig {
  dataKey: string;
  name?: string;
  color?: string;
  fill?: string;
  stackId?: string;
}

export interface BarChartProps {
  data?: any[];
  dataKey?: string;
  bars?: BarItemConfig[];
  xKey?: string;
  xAxisKey?: string;
  title?: string;
  color?: string;
  height?: number | string;
  showLegend?: boolean;
  formatValue?: (val: any) => string;
}

export const BarChart: React.FC<BarChartProps> = ({
  data,
  dataKey,
  bars = [],
  xKey = "name",
  xAxisKey,
  title,
  color = "var(--color-brand-500)",
  height = 300,
  showLegend = true,
  formatValue,
}) => {
  const [isMounted] = useState<boolean>(() => typeof window !== "undefined");
  const [activeBarKey, setActiveBarKey] = useState<string | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const gradientId = `bar-grad-${useId().replace(/:/g, "")}`;

  const finalXKey = xAxisKey || xKey || "name";
  const finalDataKey = dataKey || "value";

  const defaultFormat = (val: any): string => {
    if (val === null || val === undefined || isNaN(val)) return "0";
    const num = Number(val);
    if (!isFinite(num)) return "0";
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}k`;
    // Small magnitudes (rates, intensities) need more digits or every tick collapses to "0" / "0.1".
    const digits = Math.abs(num) >= 10 ? 1 : Math.abs(num) >= 1 ? 2 : 3;
    return num.toLocaleString(undefined, { maximumFractionDigits: digits });
  };

  // Show every category label (long names are shortened; the tooltip carries the full name).
  const manyCategories = (data?.length || 0) > 4;
  const shortLabel = (v: any): string => {
    const s = String(v ?? "");
    return s.length > 16 ? `${s.slice(0, 15)}…` : s;
  };

  const valueFormatter = formatValue || defaultFormat;

  const renderTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const label =
        payload[0].payload && payload[0].payload[finalXKey] !== undefined
          ? payload[0].payload[finalXKey]
          : "";

      return (
        <div className="modern-chart-tooltip">
          <div className="tooltip-header">
            <span className="tooltip-label">{label}</span>
            <span className="tooltip-badge">
              {payload.length} {payload.length === 1 ? "value" : "breakdowns"}
            </span>
          </div>
          <div className="tooltip-items-list">
            {payload.map((entry: any, idx: number) => (
              <div key={idx} className="tooltip-item-row">
                <div className="tooltip-item-left">
                  <span
                    className="tooltip-color-dot"
                    style={{ backgroundColor: entry.color || entry.fill }}
                  />
                  <span title={entry.name || entry.dataKey}>
                    {entry.name || entry.dataKey}
                  </span>
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
          const isDimmed =
            activeBarKey !== null && activeBarKey !== entry.dataKey;
          return (
            <div
              key={`legend-${idx}`}
              className={`legend-item-pill ${isDimmed ? "dimmed" : ""}`}
              onMouseEnter={() => setActiveBarKey(entry.dataKey)}
              onMouseLeave={() => setActiveBarKey(null)}
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
              <line x1="12" y1="20" x2="12" y2="10" />
              <line x1="18" y1="20" x2="18" y2="4" />
              <line x1="6" y1="20" x2="6" y2="16" />
            </svg>
          </div>
          <span>No benchmark data available</span>
        </div>
      </div>
    );
  }

  const hasMultipleBars = bars && bars.length > 0;

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
        <RechartsBar
          data={data}
          margin={{ top: 20, right: 12, left: -4, bottom: 4 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" style={{ stopColor: color, stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: color, stopOpacity: 0.72 }} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="4 4"
            stroke="rgba(226, 232, 240, 0.75)"
            vertical={false}
          />

          <XAxis
            dataKey={finalXKey}
            stroke="var(--color-ink-300)"
            tick={{ fill: "var(--color-ink-500)", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            dy={8}
            interval={0}
            tickFormatter={shortLabel}
            angle={manyCategories ? -30 : 0}
            textAnchor={manyCategories ? "end" : "middle"}
            height={manyCategories ? 64 : 30}
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
            cursor={{ fill: "rgba(241, 245, 249, 0.65)", radius: 6 }}
          />

          {showLegend && hasMultipleBars && (
            <Legend content={renderLegend} verticalAlign="bottom" />
          )}

          {hasMultipleBars ? (
            bars.map((b, idx) => {
              const bKey = b.dataKey;
              const isDimmed = activeBarKey !== null && activeBarKey !== bKey;
              const barColor =
                b.color ||
                b.fill ||
                MODERN_BAR_PALETTE[idx % MODERN_BAR_PALETTE.length];
              const isTopInStack =
                !b.stackId || idx === bars.length - 1;

              return (
                <Bar
                  key={idx}
                  dataKey={bKey}
                  name={b.name || bKey}
                  fill={barColor}
                  stackId={b.stackId}
                  maxBarSize={44}
                  radius={isTopInStack ? [6, 6, 0, 0] : [0, 0, 0, 0]}
                  opacity={isDimmed ? 0.35 : 1}
                  animationDuration={800}
                />
              );
            })
          ) : (
            <Bar
              dataKey={finalDataKey}
              fill={`url(#${gradientId})`}
              maxBarSize={44}
              radius={[6, 6, 0, 0]}
              animationDuration={800}
              onMouseEnter={(_: unknown, i: number) => setHoverIndex(i)}
              onMouseLeave={() => setHoverIndex(null)}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color || entry.fill || `url(#${gradientId})`}
                  opacity={hoverIndex !== null && hoverIndex !== index ? 0.45 : 1}
                />
              ))}
              {data.length <= 8 && (
                <LabelList
                  dataKey={finalDataKey}
                  position="top"
                  formatter={valueFormatter}
                  style={{ fill: "var(--color-ink-700)", fontSize: 11, fontWeight: 600 }}
                />
              )}
            </Bar>
          )}
        </RechartsBar>
      </ResponsiveContainer>
    </div>
  );
};

export default BarChart;
