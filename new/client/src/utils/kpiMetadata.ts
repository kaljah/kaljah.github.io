import { t } from "../i18n";
import type { KpiMeta } from "../ui";

export interface BuildKpiMetaOptions {
  year?: string | number;
  scope?: string;
  verifiedOnly?: boolean;
  gwpStandard?: string;
  gwpHorizon?: string;
  scope2Method?: string;
  lastUpdated?: string;
}

/** Formats applied filters into a single readable string. */
export function formatFiltersApplied(opts: BuildKpiMetaOptions): string {
  const parts: string[] = [];
  parts.push(opts.year && opts.year !== "all" ? t("Year {{year}}", { year: opts.year }) : t("All reporting years"));
  if (opts.scope) {
    parts.push(opts.scope);
  }
  parts.push(opts.verifiedOnly !== false ? t("Verified records only") : t("Including unverified drafts"));
  if (opts.scope2Method) {
    parts.push(opts.scope2Method === "market" ? t("Scope 2 Market-based") : t("Scope 2 Location-based"));
  }
  return parts.join(" · ");
}

/** Standardized metadata definitions for KPIs displayed across multiple pages. */
export function getKpiDefinition(metric: "grossEmissions" | "carbonIntensity" | "methane" | "methaneIntensity" | "flaring" | "pending" | "uncertainty"): { definition: string; formula: string } {
  switch (metric) {
    case "grossEmissions":
      return {
        definition: t("Total greenhouse gas emissions from Scope 1 direct operations and Scope 2 indirect purchased energy, expressed in metric tonnes of CO2 equivalent."),
        formula: "Scope 1 + Scope 2 (Location or Market)",
      };
    case "carbonIntensity":
      return {
        definition: t("Carbon intensity ratio measuring greenhouse gas emissions generated per barrel of oil equivalent produced across operated assets."),
        formula: "Gross GHG (Scope 1+2 tCO2e) × 1,000 / Total Production (BOE)",
      };
    case "methane":
      return {
        definition: t("Total methane mass emitted from venting, flaring slip, fugitives, and incomplete combustion, expressed in metric tonnes of CH4."),
        formula: "Σ(CH4 Venting + CH4 Flaring + CH4 Fugitives + CH4 Combustion)",
      };
    case "methaneIntensity":
      return {
        definition: t("Methane loss rate comparing total fugitive, vented, and flaring methane emissions against total marketable natural gas volume produced."),
        formula: "Volume of CH4 emitted (scf) / Total Natural Gas produced (scf) × 100%",
      };
    case "flaring":
      return {
        definition: t("Emissions from routine, safety, and non-routine flaring, calculated per API Compendium 2021 Table 5-4 with combustion efficiency."),
        formula: "Flared Gas Volume × Heat Value × Carbon Content × Combustion Efficiency (98%)",
      };
    case "pending":
      return {
        definition: t("Total activity records submitted by operators currently awaiting secondary review and formal verification under maker-checker segregation of duties."),
        formula: "Count of records with status = 'Pending review'",
      };
    case "uncertainty":
      return {
        definition: t("Quantified inventory statistical uncertainty at a 95% confidence interval (coverage factor k=2) evaluated per ISO 14064-1 and GHG Protocol."),
        formula: "SRSS: √(Σ (U_i × E_i)²) / E_total × 100%",
      };
    default:
      return {
        definition: "",
        formula: "",
      };
  }
}

/** Builds complete KPI metadata for StatCard tooltips. */
export function buildKpiMetadata(
  metric: "grossEmissions" | "carbonIntensity" | "methane" | "methaneIntensity" | "flaring" | "pending" | "uncertainty",
  opts: BuildKpiMetaOptions = {},
): KpiMeta {
  const { definition, formula } = getKpiDefinition(metric);
  const filtersApplied = formatFiltersApplied(opts);
  const gwp = opts.gwpStandard
    ? `${opts.gwpStandard.toUpperCase()} (GWP-${opts.gwpHorizon || "100"})`
    : `AR5 (GWP-${opts.gwpHorizon || "100"})`;

  return {
    definition,
    formula,
    filtersApplied,
    gwpStandard: gwp,
    lastUpdated: opts.lastUpdated || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };
}
