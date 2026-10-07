/**
 * API 2021 Emission Factors Utilities
 * Helper functions to interact with the emission factors API endpoints
 */

import api from "../api";

export interface ProcessTypeItem {
  id: string;
  name: string;
  category?: string;
  [key: string]: any;
}

export interface FactorVersionInfo {
  version: string;
  source: string;
  [key: string]: any;
}

/**
 * Get all available segments
 */
export const getSegments = async (): Promise<string[]> => {
  try {
    const response = await api.get("/emission-factors/segments");
    return Array.isArray(response.data) ? response.data : ["Upstream", "Midstream", "Downstream"];
  } catch (error) {
    console.error("Error fetching segments:", error);
    return ["Upstream", "Midstream", "Downstream"]; // Fallback
  }
};

/**
 * Get process types for a specific segment
 */
export const getProcessTypesForSegment = async (segment: string): Promise<ProcessTypeItem[]> => {
  try {
    const response = await api.get(
      `/emission-factors/process-types/${segment.toLowerCase()}`,
    );
    return response.data?.process_types || [];
  } catch (error) {
    console.error(`Error fetching process types for ${segment}:`, error);
    return [];
  }
};

/**
 * Get emission factors for a specific segment
 */
export const getFactorsBySegment = async (segment: string): Promise<Record<string, any>> => {
  try {
    const response = await api.get(`/emission-factors/by-segment/${segment}`);
    return response.data?.factors || {};
  } catch (error) {
    console.error(`Error fetching factors for ${segment}:`, error);
    return {};
  }
};

/**
 * Get emission factors for a specific process category
 */
export const getFactorsByProcess = async (processCategory: string): Promise<Record<string, any>> => {
  try {
    const response = await api.get(
      `/emission-factors/by-process/${processCategory}`,
    );
    return response.data?.factors || {};
  } catch (error) {
    console.error(
      `Error fetching factors for process ${processCategory}:`,
      error,
    );
    return {};
  }
};

/**
 * Get emission factors for a specific segment AND process category
 */
export const getFactorsBySegmentAndProcess = async (
  segment: string,
  processCategory: string,
): Promise<Record<string, any>> => {
  try {
    const response = await api.get("/emission-factors/by-segment-and-process", {
      params: { segment, process: processCategory },
    });
    return response.data?.factors || {};
  } catch (error) {
    console.error(
      `Error fetching factors for ${segment} + ${processCategory}:`,
      error,
    );
    return {};
  }
};

/**
 * Search emission factors by query
 */
export const searchEmissionFactors = async (
  query: string,
  segment: string | null = null,
  process: string | null = null,
): Promise<Record<string, any>> => {
  try {
    const params: Record<string, string> = { q: query };
    if (segment) params.segment = segment;
    if (process) params.process = process;

    const response = await api.get("/emission-factors/search", { params });
    return response.data?.factors || {};
  } catch (error) {
    console.error("Error searching emission factors:", error);
    return {};
  }
};

/**
 * Get emission factors with uncertainty information
 */
export const getFactorsWithUncertainties = async (
  minUncertainty: number | null = null,
  maxUncertainty: number | null = null,
): Promise<Record<string, any>> => {
  try {
    const params: Record<string, number> = {};
    if (minUncertainty !== null) params.min_uncertainty = minUncertainty;
    if (maxUncertainty !== null) params.max_uncertainty = maxUncertainty;

    const response = await api.get("/emission-factors/uncertainties", {
      params,
    });
    return response.data?.factors || {};
  } catch (error) {
    console.error("Error fetching factors with uncertainties:", error);
    return {};
  }
};

/**
 * Get database statistics
 */
export const getFactorStats = async (): Promise<Record<string, any>> => {
  try {
    const response = await api.get("/emission-factors/stats");
    return response.data || {};
  } catch (error) {
    console.error("Error fetching factor stats:", error);
    return {};
  }
};

/**
 * Get database version information
 */
export const getFactorVersion = async (): Promise<FactorVersionInfo> => {
  try {
    const response = await api.get("/emission-factors/version");
    return response.data || { version: "Unknown", source: "API Compendium 2021" };
  } catch (error) {
    console.error("Error fetching version info:", error);
    return { version: "Unknown", source: "API Compendium 2021" };
  }
};

/**
 * Get uncertainty for a specific emission factor
 */
export const getFactorUncertainty = (factor: any, gas: string = "co2"): number => {
  if (!factor || !factor.uncertainty) return 0;
  return factor.uncertainty[gas] || 0;
};

/**
 * Format uncertainty for display
 */
export const formatUncertainty = (uncertainty?: number | null): string => {
  if (!uncertainty || uncertainty === 0) return "N/A";
  return `±${(uncertainty * 100).toFixed(1)}%`;
};

/**
 * Get segment badge color
 */
export const getSegmentColor = (segment?: string): string => {
  const colors: Record<string, string> = {
    Upstream: "#10b981", // Green
    Midstream: "#3b82f6", // Blue
    Downstream: "#8b5cf6", // Purple
  };
  return (segment && colors[segment]) || "#6b7280"; // Gray default
};

/**
 * Get segment badge background color
 */
export const getSegmentBgColor = (segment?: string): string => {
  const colors: Record<string, string> = {
    Upstream: "rgba(16, 185, 129, 0.1)",
    Midstream: "rgba(59, 130, 246, 0.1)",
    Downstream: "rgba(139, 92, 246, 0.1)",
  };
  return (segment && colors[segment]) || "rgba(107, 114, 128, 0.1)";
};

/**
 * Convert activity data to base unit
 */
export const convertActivityData = (amount: number, fromUnit: string, toUnit: string): number => {
  if (!amount || !fromUnit || !toUnit || fromUnit === toUnit) return amount;

  const u1 = fromUnit.toLowerCase();
  const u2 = toUnit.toLowerCase();

  // Direct factors
  const factors: Record<string, number> = {
    // Volume - Liquid
    bbl_gal: 42,
    gal_bbl: 1 / 42,
    bbl_m3: 0.1589873,
    m3_bbl: 6.28981,
    bbl_l: 158.9873,
    l_bbl: 1 / 158.9873,
    m3_gal: 264.172,
    gal_m3: 0.00378541,
    l_gal: 0.264172,
    gal_l: 3.78541,

    // Volume - Gas
    mcf_scf: 1000,
    scf_mcf: 0.001,
    mscf_scf: 1000,
    scf_mscf: 0.001,
    mmscf_scf: 1000000,
    scf_mmscf: 0.000001,
    mmscf_mcf: 1000,
    mcf_mmscf: 0.001,
    mmscf_mscf: 1000,
    mscf_mmscf: 0.001,
    m3_scf: 35.3147,
    scf_m3: 0.0283168,
    mcf_m3: 28.316846592,
    m3_mcf: 1 / 28.316846592,
    mscf_m3: 28.316846592,
    m3_mscf: 1 / 28.316846592,
    mmscf_m3: 28316.846592,
    m3_mmscf: 1 / 28316.846592,

    // Mass
    ton_kg: 907.185,
    kg_ton: 1 / 907.185,
    tonne_kg: 1000,
    kg_tonne: 0.001,
    tonne_ton: 1.10231,
    ton_tonne: 0.907185,
    lb_ton: 0.0005,
    ton_lb: 2000,
    lb_kg: 0.45359237,
    kg_lb: 2.20462262,
    lb_tonne: 0.00045359237,
    tonne_lb: 2204.62262,
    g_kg: 0.001,
    kg_g: 1000,
  };

  const key = `${u1}_${u2}`;
  if (factors[key] !== undefined) {
    return amount * factors[key];
  }

  return amount;
};
