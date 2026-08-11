/**
 * API 2021 Emission Factors Utilities
 * Helper functions to interact with the emission factors API endpoints
 */

import api from "../api";

/**
 * Get all available segments
 * @returns {Promise<Array>} Array of segments ['Upstream', 'Midstream', 'Downstream']
 */
export const getSegments = async () => {
  try {
    const response = await api.get("/emission-factors/segments");
    return response.data;
  } catch (error) {
    console.error("Error fetching segments:", error);
    return ["Upstream", "Midstream", "Downstream"]; // Fallback
  }
};

/**
 * Get process types for a specific segment
 * @param {string} segment - 'upstream', 'midstream', or 'downstream'
 * @returns {Promise<Array>} Array of process type objects with id, name, and category
 */
export const getProcessTypesForSegment = async (segment) => {
  try {
    const response = await api.get(
      `/emission-factors/process-types/${segment.toLowerCase()}`,
    );
    return response.data.process_types || [];
  } catch (error) {
    console.error(`Error fetching process types for ${segment}:`, error);
    return [];
  }
};

/**
 * Get emission factors for a specific segment
 * @param {string} segment - 'Upstream', 'Midstream', or 'Downstream'
 * @returns {Promise<Object>} Emission factors for that segment
 */
export const getFactorsBySegment = async (segment) => {
  try {
    const response = await api.get(`/emission-factors/by-segment/${segment}`);
    return response.data.factors || {};
  } catch (error) {
    console.error(`Error fetching factors for ${segment}:`, error);
    return {};
  }
};

/**
 * Get emission factors for a specific process category
 * @param {string} processCategory - Process category ID (e.g., 'stationary_combustion', 'flaring')
 * @returns {Promise<Object>} Emission factors for that process category
 */
export const getFactorsByProcess = async (processCategory) => {
  try {
    const response = await api.get(
      `/emission-factors/by-process/${processCategory}`,
    );
    return response.data.factors || {};
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
 * @param {string} segment - 'Upstream', 'Midstream', or 'Downstream'
 * @param {string} processCategory - Process category ID
 * @returns {Promise<Object>} Emission factors matching both criteria
 */
export const getFactorsBySegmentAndProcess = async (
  segment,
  processCategory,
) => {
  try {
    const response = await api.get("/emission-factors/by-segment-and-process", {
      params: { segment, process: processCategory },
    });
    return response.data.factors || {};
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
 * @param {string} query - Search query
 * @param {string} segment - Optional segment filter
 * @param {string} process - Optional process category filter
 * @returns {Promise<Object>} Matching emission factors
 */
export const searchEmissionFactors = async (
  query,
  segment = null,
  process = null,
) => {
  try {
    const params = { q: query };
    if (segment) params.segment = segment;
    if (process) params.process = process;

    const response = await api.get("/emission-factors/search", { params });
    return response.data.factors || {};
  } catch (error) {
    console.error("Error searching emission factors:", error);
    return {};
  }
};

/**
 * Get emission factors with uncertainty information
 * @param {number} minUncertainty - Optional minimum uncertainty threshold (0-1)
 * @param {number} maxUncertainty - Optional maximum uncertainty threshold (0-1)
 * @returns {Promise<Object>} Emission factors with uncertainties
 */
export const getFactorsWithUncertainties = async (
  minUncertainty = null,
  maxUncertainty = null,
) => {
  try {
    const params = {};
    if (minUncertainty !== null) params.min_uncertainty = minUncertainty;
    if (maxUncertainty !== null) params.max_uncertainty = maxUncertainty;

    const response = await api.get("/emission-factors/uncertainties", {
      params,
    });
    return response.data.factors || {};
  } catch (error) {
    console.error("Error fetching factors with uncertainties:", error);
    return {};
  }
};

/**
 * Get database statistics
 * @returns {Promise<Object>} Database statistics
 */
export const getFactorStats = async () => {
  try {
    const response = await api.get("/emission-factors/stats");
    return response.data;
  } catch (error) {
    console.error("Error fetching factor stats:", error);
    return {};
  }
};

/**
 * Get database version information
 * @returns {Promise<Object>} Version and source information
 */
export const getFactorVersion = async () => {
  try {
    const response = await api.get("/emission-factors/version");
    return response.data;
  } catch (error) {
    console.error("Error fetching version info:", error);
    return { version: "Unknown", source: "API Compendium 2021" };
  }
};

/**
 * Get uncertainty for a specific emission factor
 * @param {Object} factor - Emission factor object
 * @param {string} gas - Gas type ('co2', 'ch4', 'n2o')
 * @returns {number} Uncertainty as fractional value (e.g., 0.05 = ±5%)
 */
export const getFactorUncertainty = (factor, gas = "co2") => {
  if (!factor || !factor.uncertainty) return 0;
  return factor.uncertainty[gas] || 0;
};

/**
 * Format uncertainty for display
 * @param {number} uncertainty - Fractional uncertainty (e.g., 0.05)
 * @returns {string} Formatted uncertainty string (e.g., '±5%')
 */
export const formatUncertainty = (uncertainty) => {
  if (!uncertainty || uncertainty === 0) return "N/A";
  return `±${(uncertainty * 100).toFixed(1)}%`;
};

/**
 * Get segment badge color
 * @param {string} segment - 'Upstream', 'Midstream', or 'Downstream'
 * @returns {string} CSS color for the segment badge
 */
export const getSegmentColor = (segment) => {
  const colors = {
    Upstream: "#10b981", // Green
    Midstream: "#3b82f6", // Blue
    Downstream: "#8b5cf6", // Purple
  };
  return colors[segment] || "#6b7280"; // Gray default
};

/**
 * Get segment badge background color
 * @param {string} segment - 'Upstream', 'Midstream', or 'Downstream'
 * @returns {string} CSS background color for the segment badge
 */
export const getSegmentBgColor = (segment) => {
  const colors = {
    Upstream: "rgba(16, 185, 129, 0.1)",
    Midstream: "rgba(59, 130, 246, 0.1)",
    Downstream: "rgba(139, 92, 246, 0.1)",
  };
  return colors[segment] || "rgba(107, 114, 128, 0.1)";
};

/**
 * Convert activity data to base unit
 * @param {number} amount - quantity
 * @param {string} fromUnit - e.g. 'bbl', 'Mcf'
 * @param {string} toUnit - e.g. 'gal', 'scf'
 * @returns {number} converted amount
 */
export const convertActivityData = (amount, fromUnit, toUnit) => {
  if (!amount || !fromUnit || !toUnit || fromUnit === toUnit) return amount;

  const u1 = fromUnit.toLowerCase();
  const u2 = toUnit.toLowerCase();

  // Direct factors
  const factors = {
    // Volume - Liquid
    bbl_gal: 42,
    gal_bbl: 1 / 42,
    m3_gal: 264.172,
    gal_m3: 0.00378541,
    l_gal: 0.264172,
    gal_l: 3.78541,

    // Volume - Gas
    mcf_scf: 1000,
    scf_mcf: 0.001,
    m3_scf: 35.3147,
    scf_m3: 0.0283168,

    // Mass
    ton_kg: 907.185,
    kg_ton: 1 / 907.185,
    tonne_kg: 1000,
    kg_tonne: 0.001,
    tonne_ton: 1.10231,
    ton_tonne: 0.907185,
    lb_ton: 0.0005,
    ton_lb: 2000,
  };

  const key = `${u1}_${u2}`;
  if (factors[key] !== undefined) {
    return amount * factors[key];
  }

  // Double hop check (rare but useful)
  // e.g. bbl -> m3 (bbl->gal->m3)
  // Not implementing complex graph search, just basic direct pairs requested (BBL/MCF)

  return amount;
};
