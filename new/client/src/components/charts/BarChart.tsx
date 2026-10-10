import React, { useId, useState } from "react";
import {
  BarChart as RechartsBar,
  Bar,
  Cell,
  LabelList,
  ErrorBar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import { ChartExport } from "./ChartExport";
import "./ChartWrappers.css";
import { t } from "../../i18n";

const MODERN_BAR_PALETTE = [
  "var(--color-brand-500)",
  "var(--color-blue-600)",
  "var(--color-green-500)",
  "var(--color-violet-500)",
  "var(--color-amber-500)",
  "var(--color-cyan-500)",
];

// Height of the CSV/PNG row that sits above a chart with exportName (the chart gives up this much height).
const EXPORT_BAND = 32;
// Height of the status legend under a chart with thresholds.
const LEGEND_BAND = 28;

// Phones get a narrower category axis so the bars keep most of the width.
const useNarrow = (): boolean => {
  const query = "(max-width: 639px)";
  const [narrow, setNarrow] = useState<boolean>(() => typeof window !== "undefined" && !!window.matchMedia?.(query).matches);
  React.useEffect(() => {
    const mq = window.matchMedia?.(query);
    if (!mq) return undefined;
    const on = () => setNarrow(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return narrow;
};

const STATUS_COLORS = {
  good: "var(--color-green-600)",
  warn: "var(--color-amber-500)",
  bad: "var(--color-red-500)",
};

const VALUE_LABEL_STYLE: React.CSSProperties = { fill: "var(--color-ink-700)", fontSize: 11, fontWeight: 600 };

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
  /** Horizontal bars (category names on the left): best for ranking and for long names. */
  horizontal?: boolean;
  /** Sort single-series bars from largest to smallest. */
  sortDesc?: boolean;
  /** Append each bar's share of the total to its value label. */
  showShare?: boolean;
  /** Draw a dashed target/threshold line at this value (single-series only). */
  referenceValue?: number;
  referenceLabel?: string;
  /** Makes single-series bars clickable (and reachable by keyboard); receives the clicked data row. */
  onSelect?: (row: any) => void;
  /** Accessible name for a bar button, e.g. (row) => `Open records for ${row.name}`. */
  selectLabel?: (row: any) => string;
  /** Color each single-series bar by status: below warnAt is good, up to badAt is a warning, above badAt is bad. */
  /** Data field holding a symmetric error amount: draws whiskers (value ± error) and hides the value labels. */
  errorKey?: string;
  /** Shows CSV/PNG buttons (on hover/focus) and uses this as the file name. */
  exportName?: string;
  thresholds?: { warnAt: number; badAt: number; labels?: [string, string, string] };
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
  horizontal = false,
  sortDesc = false,
  showShare = false,
  referenceValue,
  referenceLabel,
  onSelect,
  selectLabel,
  thresholds,
  exportName,
  errorKey,
}) => {
  const wrapRef = React.useRef<HTMLDivElement | null>(null);
  const narrow = useNarrow();
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
    const max = horizontal ? (narrow ? 13 : 24) : 16;
    return s.length > max ? `${s.slice(0, max - 1)}…` : s;
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
              {payload.length} {payload.length === 1 ? t("value") : t("breakdowns")}
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
          <span>{t("No benchmark data available")}</span>
        </div>
      </div>
    );
  }

  const hasMultipleBars = bars && bars.length > 0;

  const hasMultiple = bars.length > 0;
  const rows =
    sortDesc && !hasMultiple
      ? [...data].sort((a, b) => Number(b[finalDataKey] || 0) - Number(a[finalDataKey] || 0))
      : data;
  const total = rows.reduce((acc, r) => acc + (Number(r[finalDataKey]) || 0), 0);
  const labelFormatter = (v: any) => {
    const base = valueFormatter(v);
    return showShare && total > 0 ? `${base} (${((Number(v) / total) * 100).toFixed(0)}%)` : base;
  };
  const statusFill = (v: number): string | undefined =>
    !thresholds
      ? undefined
      : v > thresholds.badAt
        ? STATUS_COLORS.bad
        : v >= thresholds.warnAt
          ? STATUS_COLORS.warn
          : STATUS_COLORS.good;
  const chartHeight = typeof height === "number" ? height : parseInt(String(height), 10) || 300;
  return (
    <div
      ref={wrapRef}
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
      {exportName && (
        <ChartExport
          className="h-7"
          name={exportName}
          targetRef={wrapRef}
          header={hasMultipleBars ? [finalXKey, ...bars.map((b) => b.name || b.dataKey)] : [finalXKey, finalDataKey]}
          rows={rows.map((r) => (hasMultipleBars ? [r[finalXKey], ...bars.map((b) => r[b.dataKey])] : [r[finalXKey], r[finalDataKey]]))}
        />
      )}
      {title && <h3 className="chart-title">{title}</h3>}
      <ResponsiveContainer
        width="100%"
        height={chartHeight - (exportName ? EXPORT_BAND : 0) - (thresholds && !hasMultipleBars ? LEGEND_BAND : 0)}
        debounce={100}
      >
        <RechartsBar
          data={rows}
          layout={horizontal ? "vertical" : "horizontal"}
          margin={horizontal ? { top: referenceValue != null ? 24 : 8, right: showShare ? 104 : 64, left: 4, bottom: 4 } : { top: 20, right: 12, left: -4, bottom: 4 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2={horizontal ? "1" : "0"} y2={horizontal ? "0" : "1"}>
              <stop offset="0%" style={{ stopColor: color, stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: color, stopOpacity: 0.72 }} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="4 4"
            stroke="rgba(226, 232, 240, 0.75)"
            vertical={horizontal}
            horizontal={!horizontal}
          />

          {horizontal ? (
            <>
              <XAxis
                type="number"
                tickCount={4}
                domain={referenceValue != null ? [0, (max: number) => Math.max(max, referenceValue * 1.15)] : undefined}
                stroke="var(--color-ink-300)"
                tick={{ fill: "var(--color-ink-500)", fontSize: 11, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={valueFormatter}
              />
              <YAxis
                type="category"
                dataKey={finalXKey}
                width={narrow ? 92 : 150}
                stroke="var(--color-ink-300)"
                tick={{ fill: "var(--color-ink-700)", fontSize: 12, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                interval={0}
                tickFormatter={shortLabel}
              />
            </>
          ) : (
            <>
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
            domain={referenceValue != null ? [0, (max: number) => Math.max(max, referenceValue * 1.15)] : undefined}
            stroke="var(--color-ink-300)"
            tick={{ fill: "var(--color-ink-500)", fontSize: 11, fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={valueFormatter}
            dx={-4}
          />
            </>
          )}

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
              radius={horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0]}
              animationDuration={800}
              className={onSelect ? "cursor-pointer" : undefined}
              onClick={onSelect ? (_: unknown, i: number) => onSelect(rows[i]) : undefined}
              onMouseEnter={(_: unknown, i: number) => setHoverIndex(i)}
              onMouseLeave={() => setHoverIndex(null)}
            >
              {rows.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color || entry.fill || statusFill(Number(entry[finalDataKey]) || 0) || `url(#${gradientId})`}
                  opacity={hoverIndex !== null && hoverIndex !== index ? 0.45 : 1}
                />
              ))}
              {errorKey && (
                <ErrorBar
                  dataKey={errorKey}
                  direction={horizontal ? "x" : "y"}
                  width={6}
                  stroke="var(--color-ink-700)"
                  strokeWidth={1.5}
                />
              )}
              {!errorKey && rows.length <= (horizontal ? 12 : 8) && (
                <LabelList
                  dataKey={finalDataKey}
                  position={horizontal ? "right" : "top"}
                  formatter={labelFormatter}
                  style={VALUE_LABEL_STYLE}
                />
              )}
            </Bar>
          )}

          {referenceValue != null && !hasMultipleBars && (
            <ReferenceLine
              {...(horizontal ? { x: referenceValue } : { y: referenceValue })}
              stroke="var(--color-red-500)"
              strokeDasharray="5 4"
              strokeWidth={1.5}
              label={referenceLabel ? { value: referenceLabel, position: horizontal ? "top" : "insideTopRight", fill: "var(--color-red-500)", fontSize: 11, fontWeight: 600 } : undefined}
            />
          )}
        </RechartsBar>
      </ResponsiveContainer>
      {thresholds && !hasMultipleBars && (
        // Color is not the only signal: the legend names each state and the values stay labeled on the bars.
        <ul className="m-0 mt-1 flex list-none flex-wrap justify-center gap-x-4 gap-y-1 p-0 text-xs text-ink-600">
          {(thresholds.labels || [t("Within target"), t("Near target"), t("Above target")]).map((label, i) => (
            <li key={label} className="inline-flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className={`inline-block size-2.5 rounded-full ${["bg-green-600", "bg-amber-500", "bg-red-500"][i]}`}
              />
              {label}
            </li>
          ))}
        </ul>
      )}
      {onSelect && !hasMultipleBars && (
        // Recharts bars are not focusable: this visually hidden list gives keyboard and screen-reader users the same action.
        <ul className="sr-only">
          {rows.map((r, i) => (
            <li key={i}>
              <button type="button" onClick={() => onSelect(r)}>
                {selectLabel ? selectLabel(r) : t("Open {{name}}", { name: String(r[finalXKey]) })}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default BarChart;
