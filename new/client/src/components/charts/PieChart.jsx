import React, { useState, useEffect, useMemo } from "react";
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./ChartWrappers.css";

const MODERN_PALETTE = [
  "#ff6600", // Core brand orange
  "#2563eb", // Royal blue
  "#10b981", // Emerald green
  "#8b5cf6", // Purple / Violet
  "#f59e0b", // Amber warm gold
  "#06b6d4", // Cyan
  "#ec4899", // Rose
  "#64748b", // Slate neutral
];

export const PieChart = ({
  data,
  dataKey = "value",
  nameKey = "name",
  title,
  colors = MODERN_PALETTE,
  height = 300,
  showLegend = true,
  innerRadius = 55, // Modern donut default
  outerRadius = 80,
  formatValue,
  centerLabel,
  centerSub,
  showCenterKpi = true,
}) => {
  const [isMounted, setIsMounted] = useState(false);
  const [activeIndex, setActiveIndex] = useState(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const defaultFormat = (val) => {
    if (val === null || val === undefined || isNaN(val)) return "0";
    const num = Number(val);
    if (!isFinite(num)) return "0";
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}k`;
    return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
  };

  const valueFormatter = formatValue || defaultFormat;

  const sanitizedData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    return data
      .map((item, idx) => ({
        ...item,
        [nameKey]: item[nameKey] || `Item ${idx + 1}`,
        [dataKey]: Math.max(0, Number(item[dataKey]) || 0),
        _color:
          item.color ||
          item.fill ||
          colors[idx % colors.length] ||
          MODERN_PALETTE[idx % MODERN_PALETTE.length],
      }))
      .filter((item) => (Number(item[dataKey]) || 0) > 0);
  }, [data, dataKey, nameKey, colors]);

  const totalValue = useMemo(() => {
    return sanitizedData.reduce(
      (acc, curr) => acc + (Number(curr[dataKey]) || 0),
      0
    );
  }, [sanitizedData, dataKey]);

  const activeItem =
    activeIndex !== null && sanitizedData[activeIndex]
      ? sanitizedData[activeIndex]
      : null;

  const totalNumericHeight =
    typeof height === "number" ? height : parseInt(height, 10) || 300;

  // Split height between donut and legend if legend is shown
  const legendSpace = showLegend ? (totalNumericHeight <= 200 ? 36 : 48) : 0;
  const svgHeight = Math.max(110, totalNumericHeight - legendSpace);

  // Auto-clamp radii to guarantee donut never clips within SVG height
  const safeOuterRadius = Math.min(
    outerRadius,
    Math.max(35, Math.floor(svgHeight / 2) - 6)
  );
  const safeInnerRadius =
    innerRadius > 0
      ? Math.min(innerRadius, Math.max(20, safeOuterRadius - 16))
      : 0;

  const isDonut = safeInnerRadius >= 28;

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const item = payload[0];
      const val = Number(item.value) || 0;
      const pct =
        totalValue > 0 ? ((val / totalValue) * 100).toFixed(1) : "0";
      const itemColor = item.payload._color || item.color || "#ff6600";

      return (
        <div className="modern-chart-tooltip">
          <div className="tooltip-header">
            <span className="tooltip-label">{item.name}</span>
            <span className="tooltip-badge">{pct}%</span>
          </div>
          <div className="tooltip-items-list">
            <div className="tooltip-item-row">
              <div className="tooltip-item-left">
                <span
                  className="tooltip-color-dot circle"
                  style={{ backgroundColor: itemColor }}
                />
                <span>Value</span>
              </div>
              <div className="tooltip-item-right">
                <span>{valueFormatter(val)}</span>
              </div>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  if (!isMounted) {
    return (
      <div
        style={{
          height: `${totalNumericHeight}px`,
          width: "100%",
        }}
      />
    );
  }

  if (!sanitizedData || sanitizedData.length === 0 || totalValue <= 0) {
    return (
      <div className="chart-wrapper empty" style={{ height: `${totalNumericHeight}px` }}>
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
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
              <path d="M22 12A10 10 0 0 0 12 2v10z" />
            </svg>
          </div>
          <span>No distribution data available</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="chart-wrapper"
      style={{
        height: `${totalNumericHeight}px`,
        width: "100%",
        minWidth: 0,
        padding: 0,
        background: "transparent",
        boxShadow: "none",
        border: "none",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      {title && <h3 className="chart-title">{title}</h3>}

      {/* Relative container holding donut SVG + Centered KPI Overlay */}
      <div
        className="donut-container-relative"
        style={{ height: `${svgHeight}px`, width: "100%", flexShrink: 0 }}
      >
        <ResponsiveContainer width="100%" height={svgHeight} debounce={100}>
          <RechartsPie>
            <Pie
              data={sanitizedData}
              dataKey={dataKey}
              nameKey={nameKey}
              cx="50%"
              cy="50%"
              innerRadius={safeInnerRadius}
              outerRadius={safeOuterRadius}
              paddingAngle={isDonut ? 3 : 0}
              cornerRadius={isDonut ? 4 : 0}
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              animationDuration={800}
            >
              {sanitizedData.map((entry, index) => {
                const isSelected = activeIndex === index;
                const isDimmed = activeIndex !== null && !isSelected;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry._color}
                    stroke="#ffffff"
                    strokeWidth={isSelected ? 3 : 2}
                    opacity={isDimmed ? 0.4 : 1}
                    style={{
                      cursor: "pointer",
                      transition: "opacity 0.2s ease, transform 0.2s ease",
                      filter: isSelected ? "drop-shadow(0 2px 6px rgba(0,0,0,0.15))" : "none",
                    }}
                  />
                );
              })}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </RechartsPie>
        </ResponsiveContainer>

        {/* Dynamic Center KPI Overlay */}
        {isDonut && showCenterKpi && (
          <div className="donut-center-kpi">
            <span
              className="donut-center-label"
              title={activeItem ? activeItem[nameKey] : centerLabel || "Total"}
            >
              {activeItem ? activeItem[nameKey] : centerLabel || "Total"}
            </span>
            <span className="donut-center-val">
              {activeItem
                ? valueFormatter(activeItem[dataKey])
                : valueFormatter(totalValue)}
            </span>
            <span className="donut-center-sub">
              {activeItem
                ? `${
                    totalValue > 0
                      ? ((Number(activeItem[dataKey]) / totalValue) * 100).toFixed(1)
                      : 0
                  }%`
                : centerSub ||
                  (sanitizedData.length > 1
                    ? `${sanitizedData.length} Sources`
                    : "")}
            </span>
          </div>
        )}
      </div>

      {/* Modern Interactive Legend Pills */}
      {showLegend && sanitizedData.length > 0 && (
        <div className="modern-chart-legend" style={{ paddingTop: "6px" }}>
          {sanitizedData.map((item, idx) => {
            const isDimmed = activeIndex !== null && activeIndex !== idx;
            const val = Number(item[dataKey]) || 0;
            const pct =
              totalValue > 0 ? ((val / totalValue) * 100).toFixed(0) : "0";

            return (
              <div
                key={`legend-${idx}`}
                className={`legend-item-pill ${isDimmed ? "dimmed" : ""}`}
                onMouseEnter={() => setActiveIndex(idx)}
                onMouseLeave={() => setActiveIndex(null)}
                title={`${item[nameKey]}: ${valueFormatter(val)} (${pct}%)`}
              >
                <span
                  className="legend-item-dot"
                  style={{ backgroundColor: item._color }}
                />
                <span className="legend-item-name">{item[nameKey]}</span>
                <span className="legend-item-val">{pct}%</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PieChart;
