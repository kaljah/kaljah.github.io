// Column mapping helpers shared by the bulk import wizards.
import { t } from "../i18n";

export interface ImportField {
  key: string;
  label: string;
  required?: boolean;
  hint?: string;
  [key: string]: any;
}

// Header as compared: template tags ("[Required] date") and unit notes ("Bleed Rate (scf/hr)")
// are dropped, then lower case words
export function normHeader(h?: string | null): string {
  return String(h ?? "")
    .replace(/^\s*(\[[^\]]*\]\s*)+/, "")
    .replace(/\([^)]*\)/g, " ")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

// Generic single words that are also words of other columns ("activity" in "activity_key", "hours" in
// "operating_hours", "region" in "unload_region"): they map only a header that is exactly that word
// (S1K-F12: the Activity field was mapped to the activity_key column)
const EXACT_ONLY = new Set(["activity", "division", "field", "region", "notes", "hours", "pressure", "events",
  "diameter", "gor", "co2", "n2", "ppm", "service"]);

const hasWord = (text: string, term: string): boolean =>
  Boolean(term && new RegExp(`(^| )${term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}( |$)`).test(text));

// Field -> header. An exact name (field key or label) wins; otherwise a header that contains the
// whole field name. Each header is used once, so a column such as "Type" or "Unit" is not
// assigned to every field whose label contains that word.
export function autoDetectMapping(headers: string[], fields: ImportField[]): Record<string, string> {
  const mapping: Record<string, string> = {};
  const used = new Set<string>();
  const norm: Array<[string, string]> = headers.map((h) => [h, normHeader(h)]);
  const terms = (f: ImportField): string[] => [normHeader(f.key.replace(/_/g, " ")), normHeader(f.label)].filter(Boolean);

  fields.forEach((f) => {
    const hit = norm.find(([h, n]) => !used.has(h) && terms(f).includes(n));
    if (hit) {
      mapping[f.key] = hit[0];
      used.add(hit[0]);
    }
  });
  // longer field names first, so "Tank Control Eff" is matched before "Control Eff"
  [...fields]
    .filter((f) => !mapping[f.key])
    .sort((a, b) => Math.max(...terms(b).map((t) => t.length)) - Math.max(...terms(a).map((t) => t.length)))
    .forEach((f) => {
      const hit = norm.find(([h, n]) => !used.has(h) && terms(f).some((t) => t.length > 2 && !EXACT_ONLY.has(t) && hasWord(n, t)));
      if (hit) {
        mapping[f.key] = hit[0];
        used.add(hit[0]);
      }
    });
  // a short header ("Facility") that is a word of exactly one field name ("Region / Facility")
  norm
    .filter(([h, n]) => !used.has(h) && n.length >= 4)
    .forEach(([h, n]) => {
      const cands = fields.filter((f) => terms(f).some((t) => hasWord(t, n)));
      if (cands.length === 1 && !mapping[cands[0].key]) {
        mapping[cands[0].key] = h;
        used.add(h);
      }
    });
  return mapping;
}

// Required fields that are not mapped. The period is a date column OR year and month columns.
export function missingRequiredFields(fields: ImportField[], mapping: Record<string, string>): ImportField[] {
  const has = (k: string) => Boolean(mapping[k]);
  const withDate = fields.some((f) => f.key === "date");
  const periodOk = has("date") || (has("year") && has("month"));
  return fields
    .filter((f) => {
      if (!f.required || has(f.key)) return false;
      if (withDate && ["date", "year", "month"].includes(f.key)) return !periodOk && f.key === "date";
      return true;
    })
    .map((f) => (withDate && f.key === "date" ? { ...f, label: t("Date (or Year and Month)") } : f));
}
