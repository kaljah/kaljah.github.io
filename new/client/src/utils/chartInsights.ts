// One-sentence takeaways shown under charts. Pure functions: the data is already on the client.
import { formatCompactNumber } from "./formatters";

export interface BridgeStep {
  name: string;
  delta: number;
}

type Fmt = (v: number) => string;

const signed = (d: number, fmt: Fmt): string => `${d < 0 ? "−" : "+"}${fmt(Math.abs(d))}`;

/** "Scope 1+2 fell 7.1% (−84K tCO₂e), mainly Combustion (−62K) and Flaring (−48K)." */
export const describeBridge = (
  start: number,
  end: number,
  steps: BridgeStep[],
  fmt: Fmt = (v) => formatCompactNumber(v),
  scopeLabel = "Scope 1+2",
): string => {
  const change = end - start;
  const movers = steps
    .filter((s) => Math.abs(s.delta) > 0)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  if (Math.abs(change) < 0.5 && !movers.length) return `${scopeLabel} emissions did not change.`;
  const pct = start > 0 ? ` ${Math.abs((change / start) * 100).toFixed(1)}%` : "";
  const verb = change === 0 ? "was flat" : change < 0 ? `fell${pct}` : `rose${pct}`;
  const head = `${scopeLabel} ${verb}${change === 0 ? "" : ` (${signed(change, fmt)} tCO₂e)`}`;
  if (!movers.length) return `${head}.`;
  const named = movers.slice(0, 2).map((m) => `${m.name} (${signed(m.delta, fmt)})`);
  return `${head}, mainly ${named.join(" and ")}.`;
};

export interface RankedItem {
  name: string;
  value: number;
}

/** "Combustion is the largest, 55% of the total; the top 2 make up 79%." */
export const describeRanking = (items: RankedItem[], noun = "contributor"): string => {
  const rows = items.filter((i) => Number.isFinite(i.value) && i.value > 0).sort((a, b) => b.value - a.value);
  const total = rows.reduce((a, r) => a + r.value, 0);
  if (!rows.length || total <= 0) return "";
  const share = (v: number) => Math.round((v / total) * 100);
  if (rows.length === 1) return `${rows[0].name} is the only ${noun}.`;
  // Sum of the rounded shares, so the sentence matches the percentages printed on the bars.
  const top2 = share(rows[0].value) + share(rows[1].value);
  const tail = rows.length > 2 ? `; the top 2 make up ${top2}%` : "";
  return `${rows[0].name} is the largest ${noun}, ${share(rows[0].value)}% of the total${tail}.`;
};
