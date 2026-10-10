import React, { useMemo } from "react";
import {
  BarChart as RechartsBar,
  Bar,
  Cell,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartExport } from "./ChartExport";
import "./ChartWrappers.css";
import { t } from "../../i18n";

export interface WaterfallStep {
  name: string;
  delta: number;
}

export interface WaterfallChartProps {
  startLabel: string;
  endLabel: string;
  start: number;
  end: number;
  steps: WaterfallStep[];
  height?: number;
  formatValue?: (val: number) => string;
  /** Click (or keyboard) on a change step; the start and end totals are not clickable. */
  onSelectStep?: (step: WaterfallStep) => void;
  /** Step labels as absolute values or as a percentage of the starting total. */
  labelMode?: "absolute" | "percent";
  /** Shows CSV/PNG buttons (on hover/focus) and uses this as the file name. */
  exportName?: string;
}

interface Row {
  name: string;
  base: number;
  value: number;
  kind: "total" | "up" | "down";
  delta?: number;
  top: number;
}

const COLORS = {
  total: "var(--color-blue-600)",
  // More emissions is the bad direction, fewer is the good one.
  up: "var(--color-red-500)",
  down: "var(--color-green-500)",
};

// Two decimals: on a zoomed axis one decimal repeats ("1.2M, 1.2M, 1.1M, 1.1M").
const AXIS_FORMAT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 });

const VALUE_LABEL_STYLE: React.CSSProperties = { fill: "var(--color-ink-700)", fontSize: 11, fontWeight: 600 };

/** Bridge from a start total to an end total: floating bars show what moved it in between. */
export const WaterfallChart: React.FC<WaterfallChartProps> = ({
  startLabel,
  endLabel,
  start,
  end,
  steps,
  height = 300,
  formatValue = (v) => String(v),
  onSelectStep,
  labelMode = "absolute",
  exportName,
}) => {
  const wrapRef = React.useRef<HTMLDivElement | null>(null);
  // Eight step names do not fit side by side on a phone: tilt them there.
  const [narrow, setNarrow] = React.useState<boolean>(() => typeof window !== "undefined" && !!window.matchMedia?.("(max-width: 639px)").matches);
  React.useEffect(() => {
    const mq = window.matchMedia?.("(max-width: 639px)");
    if (!mq) return undefined;
    const on = () => setNarrow(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  const { rows, domain } = useMemo(() => {
    const out: Row[] = [{ name: startLabel, base: 0, value: start, kind: "total", top: start }];
    let running = start;
    let lo = start;
    let hi = start;
    for (const s of steps) {
      const next = running + s.delta;
      out.push({
        name: s.name,
        base: Math.min(running, next),
        value: Math.abs(s.delta),
        kind: s.delta >= 0 ? "up" : "down",
        delta: s.delta,
        top: Math.max(running, next),
      });
      running = next;
      lo = Math.min(lo, running);
      hi = Math.max(hi, running);
    }
    out.push({ name: endLabel, base: 0, value: end, kind: "total", top: end });
    lo = Math.min(lo, end);
    hi = Math.max(hi, end);
    // The deltas are small next to the totals, so the axis is zoomed on the range they move through.
    const pad = (hi - lo) * 0.6 || hi * 0.05 || 1;
    return { rows: out, domain: [Math.max(0, lo - pad), hi + pad] as [number, number] };
  }, [startLabel, endLabel, start, end, steps]);

  const sign = (d: number) => (d > 0 ? "+" : d < 0 ? "−" : "");
  const absSigned = (d: number) => `${sign(d)}${formatValue(Math.abs(d))}`;
  const pctSigned = (d: number) => (start > 0 ? `${sign(d)}${Math.abs((d / start) * 100).toFixed(1)}%` : "");
  const signed = (d: number) => (labelMode === "percent" && start > 0 ? pctSigned(d) : absSigned(d));

  return (
    <div ref={wrapRef} className="chart-wrapper" role="figure" aria-label={t("Emissions bridge from {{start}} to {{end}}", { start: startLabel, end: endLabel })}>
      {exportName && (
        <ChartExport
          className="h-7"
          name={exportName}
          targetRef={wrapRef}
          header={["Step", "Change (tCO2e)"]}
          rows={[[startLabel, start], ...steps.map((s) => [s.name, s.delta]), [endLabel, end]]}
        />
      )}
      <ResponsiveContainer width="100%" height={exportName ? height - 32 : height} debounce={100}>
        <RechartsBar data={rows} margin={{ top: 22, right: 12, left: -4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="rgba(226, 232, 240, 0.75)" vertical={false} />
          <XAxis
            dataKey="name"
            interval={0}
            angle={narrow ? -45 : 0}
            textAnchor={narrow ? "end" : "middle"}
            height={narrow ? 70 : 30}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--color-ink-600)", fontSize: 11, fontWeight: 600 }}
          />
          <YAxis
            domain={domain}
            allowDataOverflow
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--color-ink-500)", fontSize: 11, fontWeight: 600 }}
            tickFormatter={(v) => AXIS_FORMAT.format(Number(v))}
            tickCount={5}
          />
          <Tooltip
            cursor={{ fill: "rgba(241, 245, 249, 0.65)" }}
            content={({ active, payload }: any) => {
              if (!active || !payload?.length) return null;
              const r: Row = payload[0].payload;
              return (
                <div className="modern-chart-tooltip">
                  <div className="tooltip-header">
                    <span className="tooltip-label">{r.name}</span>
                  </div>
                  <div className="tooltip-items-list">
                    <div className="tooltip-item-row">
                      <div className="tooltip-item-right">
                        <span>
                          {r.kind === "total"
                            ? `${formatValue(r.value)} tCO₂e`
                            : `${absSigned(r.delta ?? 0)} tCO₂e${pctSigned(r.delta ?? 0) ? ` (${pctSigned(r.delta ?? 0)})` : ""}`}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            }}
          />
          {/* invisible spacer that lifts each step to where the running total is */}
          <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
          <Bar
            dataKey="value"
            stackId="w"
            maxBarSize={48}
            radius={[4, 4, 0, 0]}
            animationDuration={700}
            className={onSelectStep ? "cursor-pointer" : undefined}
            onClick={
              onSelectStep
                ? (_: unknown, i: number) => {
                    const r = rows[i];
                    if (r && r.kind !== "total") onSelectStep({ name: r.name, delta: r.delta ?? 0 });
                  }
                : undefined
            }
          >
            {rows.map((r, i) => (
              <Cell key={i} fill={COLORS[r.kind]} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              style={VALUE_LABEL_STYLE}
              content={(p: any) => {
                const r: Row | undefined = rows[p.index];
                if (!r) return null;
                const text = r.kind === "total" ? formatValue(r.value) : signed(r.delta ?? 0);
                return (
                  <text x={p.x + p.width / 2} y={p.y - 6} textAnchor="middle" style={VALUE_LABEL_STYLE}>
                    {text}
                  </text>
                );
              }}
            />
          </Bar>
        </RechartsBar>
      </ResponsiveContainer>
      {onSelectStep && (
        // Recharts bars are not focusable: a visually hidden list gives keyboard and screen-reader users the same action.
        <ul className="sr-only">
          {steps.map((s) => (
            <li key={s.name}>
              <button type="button" onClick={() => onSelectStep(s)}>
                {t("Open {{name}} records", { name: s.name })}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default WaterfallChart;
