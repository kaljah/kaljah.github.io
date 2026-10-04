import { PROCESS_TYPES as PROCESS_TYPES_MAP } from "../../utils/EmissionFactors";

export const PROCESS_TYPES = PROCESS_TYPES_MAP;

// Emission UI shows no API Compendium / table citations (user request); legal references stay
export const hideApiCitation = (t) => (t && /\bAPI\b|Compendium|\bTables?\s*\d/.test(t) ? null : t);

// Tier shown in the table and CSV: a saved library / custom factor is "Custom", a Tier 2 site
// property override is "Tier 2" (browser test #13: both were shown as "Specific")
export function factorTypeLabel(entry) {
  if (entry.factor_source === "default") return "Default";
  if (entry.factor_source === "custom") return entry.custom_factor_id ? "Custom" : "Tier 2";
  if (entry.factor_source === "specific") return "Specific";
  return "-";
}
