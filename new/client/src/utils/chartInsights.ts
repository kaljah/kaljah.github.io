// One-sentence takeaways shown under charts. Pure functions: the data is already on the client.
import { formatCompactNumber } from "./formatters";
import { t } from "../i18n";

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
  if (Math.abs(change) < 0.5 && !movers.length) return t("{{scope}} emissions did not change.", { scope: scopeLabel });
  const vars = { scope: scopeLabel, pct: Math.abs(start > 0 ? (change / start) * 100 : 0).toFixed(1), change: signed(change, fmt) };
  const head =
    change === 0
      ? t("{{scope}} was flat", vars)
      : change < 0
        ? start > 0
          ? t("{{scope}} fell {{pct}}% ({{change}} tCO₂e)", vars)
          : t("{{scope}} fell ({{change}} tCO₂e)", vars)
        : start > 0
          ? t("{{scope}} rose {{pct}}% ({{change}} tCO₂e)", vars)
          : t("{{scope}} rose ({{change}} tCO₂e)", vars);
  if (!movers.length) return `${head}.`;
  const named = movers.slice(0, 2).map((m) => `${m.name} (${signed(m.delta, fmt)})`);
  return named.length > 1
    ? t("{{summary}}, mainly {{first}} and {{second}}.", { summary: head, first: named[0], second: named[1] })
    : t("{{summary}}, mainly {{first}}.", { summary: head, first: named[0] });
};

export interface RankedItem {
  name: string;
  value: number;
}

/** "Combustion is the largest, 55% of the total; the top 2 make up 79%." */
export const describeRanking = (items: RankedItem[], noun = t("contributor")): string => {
  const rows = items.filter((i) => Number.isFinite(i.value) && i.value > 0).sort((a, b) => b.value - a.value);
  const total = rows.reduce((a, r) => a + r.value, 0);
  if (!rows.length || total <= 0) return "";
  // whole-percent shares that add up to 100 (largest remainder), as the pie labels: 1/1/1 read "33 %, top 2 66 %"
  // next to labels 34 / 33 / 33 (audit 2026-11 F-CLIENT-15)
  const raw = rows.map((r) => (r.value / total) * 100);
  const pct = raw.map(Math.floor);
  let left = 100 - pct.reduce((a, b) => a + b, 0);
  raw.map((v, i) => [v - Math.floor(v), i] as [number, number]).sort((a, b) => b[0] - a[0])
    .forEach(([, i]) => { if (left > 0) { pct[i] += 1; left -= 1; } });
  if (rows.length === 1) return t("{{name}} is the only {{noun}}.", { name: rows[0].name, noun });
  const top2 = pct[0] + pct[1];
  const vars = { name: rows[0].name, noun, share: pct[0], top2 };
  return rows.length > 2
    ? t("{{name}} is the largest {{noun}}, {{share}}% of the total; the top 2 make up {{top2}}%.", vars)
    : t("{{name}} is the largest {{noun}}, {{share}}% of the total.", vars);
};
