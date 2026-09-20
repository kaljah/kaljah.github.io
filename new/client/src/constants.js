// IPCC Assessment Report GWP Standards
export const GWP_AR4 = {
  CO2: 1,
  CH4: 25,
  N2O: 298,
  CH4_20: 72,
  N2O_20: 289,
};

export const GWP_AR5 = {
  CO2: 1,
  CH4: 28,
  N2O: 265, // IPCC AR5 WG1 Table 8.7 (2013)
  CH4_20: 82.5,
  N2O_20: 268,
};

export const GWP_AR6 = {
  CO2: 1,
  CH4: 27.9,
  N2O: 273,
  CH4_20: 82.5,
  N2O_20: 273,
};

export const GWP_STANDARDS = {
  AR4: GWP_AR4,
  AR5: GWP_AR5,
  AR6: GWP_AR6,
};

// Standard GWP for the application (default to AR5)
export const DEFAULT_GWP = GWP_AR5;

export const getActiveGwpFactors = (standard = "AR5", horizon = "100") => {
  const std = GWP_STANDARDS[standard] || GWP_AR5;
  if (String(horizon) === "20") {
    return {
      CO2: 1,
      CH4: std.CH4_20 || 82.5,
      N2O: std.N2O_20 || 268,
    };
  }
  return {
    CO2: 1,
    CH4: std.CH4,
    N2O: std.N2O,
  };
};

export const BOUNDARY_OPTIONS = {
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
