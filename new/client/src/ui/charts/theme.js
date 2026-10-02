// Shared chart styling from the design tokens. Use these in Recharts components instead of literal colors.
export const SERIES = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
];

export const SCOPE_COLORS = {
  1: "var(--color-scope-1)",
  2: "var(--color-scope-2)",
  3: "var(--color-scope-3)",
};

export const axisProps = {
  stroke: "var(--color-ink-300)",
  tick: { fill: "var(--color-ink-600)", fontSize: 12, fontWeight: 500 },
};

export const gridProps = { stroke: "var(--color-ink-200)", strokeDasharray: "3 3", vertical: false };

export const tooltipStyle = {
  contentStyle: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    boxShadow: "var(--shadow-overlay)",
    fontSize: 13,
  },
  labelStyle: { color: "var(--color-text)", fontWeight: 600 },
};
