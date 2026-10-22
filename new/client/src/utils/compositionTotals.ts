// Gas analysis total of an import row, read the way the server reads it (calculations/units.composition_fractions):
// an analysis of two or more components (c1..c10, co2_mol, n2_mol, h2s_mol) must total 100 % (99.5 to 100.5 is rounding).
// A CH4 content with an optional CO2 content (ch4_content, co2_content) is the short form: it is not an analysis and is not checked.

export type DecimalMark = "comma" | "point" | null;

export const ANALYSIS_FIELDS = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "co2_mol", "n2_mol", "h2s_mol"] as const;
export const MIN_TOTAL = 99.5;
export const MAX_TOTAL = 100.5;

/** A cell as a number, or null when it is empty or not a number. */
export function readNumber(text: unknown, mark: DecimalMark): number | null {
  let s = String(text ?? "").replace(/%/g, "").replace(/\s+/g, "").trim();
  if (!s || s === "-") return null;
  s = mark === "comma" ? s.replace(/\./g, "").replace(",", ".") : s.replace(/,/g, "");
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export interface RowAnalysis {
  /** two or more analysis components are given in the row */
  isAnalysis: boolean;
  /** total in mol % (a fractional analysis, every value 1 or less adding up to 1.5 or less, is read as fractions) */
  total: number;
  /** the row is an analysis that does not total 100 % */
  off: boolean;
}

export function analysisRowStatus(row: Record<string, unknown>, mapping: Record<string, string>, mark: DecimalMark): RowAnalysis {
  const values: number[] = [];
  for (const field of ANALYSIS_FIELDS) {
    const header = mapping[field];
    if (!header) continue;
    const n = readNumber(row[header], mark);
    if (n !== null) values.push(n);
  }
  if (values.length < 2) return { isAnalysis: false, total: values[0] ?? 0, off: false };
  const sum = values.reduce((a, b) => a + b, 0);
  const fractions = Math.max(...values) <= 1 && sum <= 1.5;
  const total = fractions ? sum * 100 : sum;
  return { isAnalysis: true, total, off: total < MIN_TOTAL || total > MAX_TOTAL };
}

/** True when the mapping has at least two analysis columns, so a row can be an analysis. */
export function mapsAnAnalysis(mapping: Record<string, string>): boolean {
  return ANALYSIS_FIELDS.filter((f) => mapping[f]).length >= 2;
}

export interface CompositionCheck {
  rows: number;
  analysisRows: number;
  /** the first rows that are off, as file line numbers (header = line 1) with their total */
  examples: Array<{ line: number; total: number }>;
  offRows: number;
}

export function emptyCompositionCheck(): CompositionCheck {
  return { rows: 0, analysisRows: 0, examples: [], offRows: 0 };
}

/** Adds one parsed row (1-based data index) to a running check. */
export function addRow(check: CompositionCheck, row: Record<string, unknown>, index: number, mapping: Record<string, string>, mark: DecimalMark, maxExamples = 5): void {
  check.rows += 1;
  const s = analysisRowStatus(row, mapping, mark);
  if (!s.isAnalysis) return;
  check.analysisRows += 1;
  if (!s.off) return;
  check.offRows += 1;
  if (check.examples.length < maxExamples) check.examples.push({ line: index + 1, total: s.total });
}
