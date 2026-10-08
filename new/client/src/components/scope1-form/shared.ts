import { PROCESS_TYPES as PROCESS_TYPES_MAP } from "../../utils/EmissionFactors";

export const PROCESS_TYPES = PROCESS_TYPES_MAP;

// Emission UI shows no API Compendium / table citations (user request); legal references stay
export const hideApiCitation = (t?: string | null): string | null =>
  t && /\bAPI\b|Compendium|\bTables?\s*\d/.test(t) ? null : (t ?? null);

// Tier shown in the table and CSV: a saved library / custom factor is "Custom", a Tier 2 site
// property override is "Tier 2" (browser test #13: both were shown as "Specific")
// Process label shown in the table and the CSV export (PROCESS_TYPES values are strings or {label})
export const processLabel = (entry: { process?: string; process_type?: string }): string => {
  const k = String(entry.process || entry.process_type || "");
  const v = (PROCESS_TYPES as Record<string, any>)[k];
  // keys the form does not list (e.g. stoichiometry) get a readable label
  const other: Record<string, string> = { stoichiometry: "Carbon Mass Balance (Stoichiometry)" };
  return (
    (typeof v === "string" ? v : v?.label) ||
    other[k] ||
    k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())
  );
};

export function factorTypeLabel(entry: { factor_source?: string; custom_factor_id?: any }): string {
  if (entry.factor_source === "default") return "Default";
  if (entry.factor_source === "custom") return entry.custom_factor_id ? "Custom" : "Tier 2";
  if (entry.factor_source === "specific") return "Specific";
  return "-";
}
