// IPCC Assessment Report GWP Standards
export interface GwpEntry {
  CO2: number;
  CH4: number;
  N2O: number;
  CH4_20: number;
  N2O_20: number;
}

export const GWP_AR4: GwpEntry = {
  CO2: 1,
  CH4: 25,
  N2O: 298,
  CH4_20: 72,
  N2O_20: 289,
};

export const GWP_AR5: GwpEntry = {
  CO2: 1,
  CH4: 28,
  N2O: 265, // IPCC AR5 WG1 Table 8.7 (2013), without climate-carbon feedback
  CH4_20: 84, // BUG-013: AR5 Table 8.7 GWP-20 (was 82.5, the AR6 fossil value)
  N2O_20: 264, // BUG-013: AR5 Table 8.7 GWP-20 (was 268)
};

export const GWP_AR6: GwpEntry = {
  CO2: 1,
  CH4: 27.9, // IPCC AR6 WG1 Table 7.15, generic CH4
  N2O: 273,
  CH4_20: 81.2, // BUG-013: GWP-20 matching the generic 27.9 GWP-100 (was 82.5, fossil)
  N2O_20: 273,
};

export const GWP_STANDARDS: Record<string, GwpEntry> = {
  AR4: GWP_AR4,
  AR5: GWP_AR5,
  AR6: GWP_AR6,
};

// Standard GWP for the application (default to AR5)
export const DEFAULT_GWP: GwpEntry = GWP_AR5;

export interface ActiveGwpFactors {
  CO2: number;
  CH4: number;
  N2O: number;
}

export const getActiveGwpFactors = (standard: string = "AR5", horizon: string | number = "100"): ActiveGwpFactors => {
  const std = GWP_STANDARDS[standard] || GWP_AR5;
  if (String(horizon) === "20") {
    return {
      CO2: 1,
      CH4: std.CH4_20 || GWP_AR5.CH4_20,
      N2O: std.N2O_20 || GWP_AR5.N2O_20,
    };
  }
  return {
    CO2: 1,
    CH4: std.CH4,
    N2O: std.N2O,
  };
};

// BUG-062: one coverage factor for every "95 % CI" shown in the UI
// (expanded uncertainty U = k·u, k = 2 per GHG Protocol / IPCC GPG).
export const UNCERTAINTY_COVERAGE_K: number = 2;

export const BOUNDARY_OPTIONS: Record<string, string[]> = {
  "Operational Control": [
    "Wholly Owned",
    "Majority Operated",
    "Minority Operated",
    "Contractual Authority",
  ],
  "Financial Control": [
    "Wholly Owned",
    "Consolidated Subsidiary",
    "Financial Lease",
  ],
  "Equity Share": [
    "Proportional Interest",
    "Equity Method Investment",
    "Joint Venture",
  ],
};

// CH4 density at the API Compendium standard conditions (60 F, 14.696 psia): 16.04 g/mol / 23.685 m3 per
// kg-mole (379.3 scf/lb-mole). Same value as the server (calculations/units.py CONVERSIONS).
export const CH4_DENSITY_KG_M3: number = 16.04 / 23.685;
