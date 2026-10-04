import React, { useState, useEffect } from "react";
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import "./ChartWrappers.css";

const DEFAULT_COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#6366f1",
];

export const PieChart = ({
  data,
  dataKey = "value",
  nameKey = "name",
  title,
  colors = DEFAULT_COLORS,
  height = 300,
  showLegend = true,
  innerRadius = 60, // Default to donut
  outerRadius = 80,
  formatValue = (val) => val,
}) => {
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="[background:rgba(255,_255,_255,_0.95)] [backdrop-filter:blur(8px)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_16px] [box-shadow:var(--shadow-card)]">
          <p className="[margin:0_0_6px_0] [font-size:var(--text-base)] [color:var(--color-ink-500)] [font-weight:600]">{payload[0].name}</p>
          <p
            className="[margin:0] [font-size:var(--text-md)] [font-weight:700]"
            style={{ color: payload[0].payload.fill }}
          >
            {formatValue(payload[0].value)}
          </p>
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
      <div className="[background:var(--color-white)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:20px] [margin-bottom:20px] [box-shadow:var(--shadow-xs)] empty">
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

  const sanitizedData = data.map((item) => ({
    ...item,
    [dataKey]: Math.max(0, Number(item[dataKey]) || 0),
  }));
  const totalValue = sanitizedData.reduce(
    (acc, curr) => acc + (Number(curr[dataKey]) || 0),
    0
  );

  if (totalValue <= 0) {
    return (
      <div className="[background:var(--color-white)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:20px] [margin-bottom:20px] [box-shadow:var(--shadow-xs)] empty">
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
    <div
      className="[border-radius:var(--radius-md)] [margin-bottom:20px]"
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
      {title && <h3 className="[margin:0_0_16px_0] [font-size:var(--text-lg)] [font-weight:600] [color:var(--text-primary)]">{title}</h3>}
      <ResponsiveContainer width="99%" height={height} debounce={200}>
        <RechartsPie>
          <Pie
            data={sanitizedData}
            dataKey={dataKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={5}
            cornerRadius={4}
          >
            {sanitizedData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || colors[index % colors.length]}
                stroke="none"
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          {showLegend && (
            <Legend
              verticalAlign="bottom"
              height={36}
              wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }}
              iconType="circle"
              formatter={(value) => <span className="text-text">{value}</span>}
            />
          )}
        </RechartsPie>
      </ResponsiveContainer>
    </div>
  );
};

export default PieChart;
