import React, { useMemo } from "react";
import CustomDropdown from "../CustomDropdown";

// ============================================================================
// API GHG COMPENDIUM (2021) CHAPTER 7 — ONSHORE REFERENCE TABLES & DATA
// ============================================================================

const TIER1_FACILITIES = [
  {
    id: "gas_production",
    label: "Gas Production Facility (Table 7-1)",
    sub: "Whole Facility Average: 810 kg CH₄/day, 120 kg CO₂/day",
    api_table: "Table 7-1",
    factor_ch4: 810.0,
    factor_co2: 120.0,
    factor_unit: "kg/day/facility",
    default_unit: "facilities",
    default_days: 365,
  },
  {
    id: "oil_production",
    label: "Oil Production Facility (Table 7-1)",
    sub: "Whole Facility Average: 140 kg CH₄/day, 26 kg CO₂/day",
    api_table: "Table 7-1",
    factor_ch4: 140.0,
    factor_co2: 26.0,
    factor_unit: "kg/day/facility",
    default_unit: "facilities",
    default_days: 365,
  },
  {
    id: "gathering_station",
    label: "Gas Gathering Compressor Station (Table 7-2)",
    sub: "Whole Station Average: 210 kg CH₄/hr, 7.3 kg CO₂/hr",
    api_table: "Table 7-2",
    factor_ch4: 210.0,
    factor_co2: 7.3,
    factor_unit: "kg/hr/station",
    default_unit: "stations",
    default_hours: 8760,
  },
];

const TIER2A_EQUIPMENT_DATA = {
  gas_production: {
    label: "Onshore Gas Production (Table 7-9)",
    api_table: "Table 7-9",
    default_stream: { ch4: 78.8, co2: 1.4 },
    equipment: [
      { id: "wellhead", label: "Wellhead", factor: 0.163, unit: "kg CH₄/hr/wellhead", co2_factor: 0.0029 },
      { id: "separator", label: "Separator", factor: 0.334, unit: "kg CH₄/hr/separator", co2_factor: 0.0059 },
      { id: "heater_treater", label: "Heater-Treater", factor: 0.077, unit: "kg CH₄/hr/heater", co2_factor: 0.0014 },
      { id: "header", label: "Header", factor: 0.106, unit: "kg CH₄/hr/header", co2_factor: 0.0019 },
      { id: "compressor", label: "Reciprocating Compressor", factor: 1.450, unit: "kg CH₄/hr/compressor", co2_factor: 0.026 },
      { id: "dehydrator", label: "Dehydrator", factor: 0.126, unit: "kg CH₄/hr/dehydrator", co2_factor: 0.0022 },
      { id: "storage_tank", label: "Storage Tank Leaks", factor: 0.035, unit: "kg CH₄/hr/tank", co2_factor: 0.00062 },
    ],
  },
  gathering_boosting: {
    label: "Onshore Gathering & Boosting (Table 7-10)",
    api_table: "Table 7-10",
    default_stream: { ch4: 78.8, co2: 1.4 },
    equipment: [
      { id: "compressor", label: "Compressor", factor: 4.480, unit: "kg CH₄/hr/compressor", co2_factor: 0.079 },
      { id: "separator", label: "Separator", factor: 0.420, unit: "kg CH₄/hr/separator", co2_factor: 0.0074 },
      { id: "dehydrator", label: "Dehydrator", factor: 0.380, unit: "kg CH₄/hr/dehydrator", co2_factor: 0.0067 },
      { id: "header", label: "Gathering Header", factor: 0.180, unit: "kg CH₄/hr/header", co2_factor: 0.0032 },
    ],
  },
  oil_production: {
    label: "Onshore Crude Oil Production (Table 7-29)",
    api_table: "Table 7-29",
    default_stream: { ch4: 65.6, co2: 1.4 },
    equipment: [
      { id: "wellhead", label: "Wellhead", factor: 0.012, unit: "kg CH₄/hr/wellhead", co2_factor: 0.00021 },
      { id: "separator", label: "Separator", factor: 0.024, unit: "kg CH₄/hr/separator", co2_factor: 0.00042 },
      { id: "heater_treater", label: "Heater-Treater", factor: 0.015, unit: "kg CH₄/hr/heater", co2_factor: 0.00027 },
      { id: "header", label: "Header", factor: 0.008, unit: "kg CH₄/hr/header", co2_factor: 0.00014 },
    ],
  },
};

const TIER2B_COMPONENTS_DATA = {
  gas_gathering: {
    label: "Onshore Gas Production & Gathering (Table 7-11)",
    api_table: "Table 7-11",
    services: {
      gas: {
        label: "Gas / Vapor Service",
        default_stream: { ch4: 78.8, co2: 1.4 },
        components: [
          { id: "valve", label: "Valves", factor: 0.0270, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.0035, unit: "kg TOC/hr/component" },
          { id: "flange", label: "Flanges", factor: 0.0039, unit: "kg TOC/hr/component" },
          { id: "open_ended_line", label: "Open-Ended Lines", factor: 0.0140, unit: "kg TOC/hr/component" },
          { id: "other", label: "Other Components", factor: 0.0360, unit: "kg TOC/hr/component" },
        ],
      },
      light_oil: {
        label: "Light Oil Service (< 20° API)",
        default_stream: { ch4: 65.6, co2: 1.4 },
        components: [
          { id: "valve", label: "Valves", factor: 0.0025, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.00021, unit: "kg TOC/hr/component" },
          { id: "pump_seal", label: "Pump Seals", factor: 0.0130, unit: "kg TOC/hr/component" },
          { id: "other", label: "Other Components", factor: 0.0075, unit: "kg TOC/hr/component" },
        ],
      },
      heavy_oil: {
        label: "Heavy Oil Service (≥ 20° API)",
        default_stream: { ch4: 18.0, co2: 1.0 },
        components: [
          { id: "valve", label: "Valves", factor: 0.0000084, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.0000075, unit: "kg TOC/hr/component" },
          { id: "flange", label: "Flanges", factor: 0.00000039, unit: "kg TOC/hr/component" },
          { id: "other", label: "Other Components", factor: 0.000032, unit: "kg TOC/hr/component" },
        ],
      },
      water_oil: {
        label: "Water / Oil Service",
        default_stream: { ch4: 60.0, co2: 1.4 },
        components: [
          { id: "valve", label: "Valves", factor: 0.000098, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.00011, unit: "kg TOC/hr/component" },
          { id: "other", label: "Other Components", factor: 0.00014, unit: "kg TOC/hr/component" },
        ],
      },
    },
  },
  crude_production: {
    label: "Onshore Crude Production (Table 7-30)",
    api_table: "Table 7-30",
    services: {
      gas: {
        label: "Gas Service",
        default_stream: { ch4: 78.8, co2: 1.4 },
        components: [
          { id: "valve", label: "Valves", factor: 0.0059, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.00082, unit: "kg TOC/hr/component" },
          { id: "flange", label: "Flanges", factor: 0.00039, unit: "kg TOC/hr/component" },
          { id: "open_ended_line", label: "Open-Ended Lines", factor: 0.0020, unit: "kg TOC/hr/component" },
        ],
      },
      light_oil: {
        label: "Light Oil Service",
        default_stream: { ch4: 65.6, co2: 1.4 },
        components: [
          { id: "valve", label: "Valves", factor: 0.0012, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.00011, unit: "kg TOC/hr/component" },
          { id: "pump_seal", label: "Pump Seals", factor: 0.0075, unit: "kg TOC/hr/component" },
        ],
      },
      heavy_oil: {
        label: "Heavy Oil Service",
        default_stream: { ch4: 18.0, co2: 1.0 },
        components: [
          { id: "valve", label: "Valves", factor: 0.0000084, unit: "kg TOC/hr/component" },
          { id: "connector", label: "Connectors", factor: 0.0000075, unit: "kg TOC/hr/component" },
        ],
      },
    },
  },
};

const TIER3_METHODS = [
  { id: "method21", label: "Method 21 Screening Ranges", sub: "Tables 7-15, 7-16 (<10k vs ≥10k ppmv)" },
  { id: "correlation", label: "EPA / API Correlation Equations", sub: "Tables 7-17, 7-18 (Continuous Leak Rate)" },
  { id: "ogi", label: "OGI Leaker Survey", sub: "Tables 7-19, 7-20 / W-1E (Leakers vs Non-Leakers)" },
  { id: "measurement", label: "Direct High-Flow Measurement", sub: "Metered Rate / Bagging / High-Flow Sampler" },
];

const OGI_LEAKER_FACTORS = [
  { id: "valve", label: "Valves", factor: 0.160, unit: "kg CH₄/hr/leaker", co2_factor: 0.0028 },
  { id: "connector", label: "Connectors", factor: 0.048, unit: "kg CH₄/hr/leaker", co2_factor: 0.00085 },
  { id: "prv", label: "Pressure Relief Valves (PRV)", factor: 0.440, unit: "kg CH₄/hr/leaker", co2_factor: 0.0078 },
  { id: "open_ended_line", label: "Open-Ended Lines", factor: 0.110, unit: "kg CH₄/hr/leaker", co2_factor: 0.0019 },
  { id: "compressor_seal", label: "Compressor Seals", factor: 0.220, unit: "kg CH₄/hr/leaker", co2_factor: 0.0039 },
  { id: "other", label: "Other Components", factor: 0.120, unit: "kg CH₄/hr/leaker", co2_factor: 0.0021 },
];

const METHOD21_FACTORS = {
  valve_gas: {
    label: "Gas Valves (Table 7-15)",
    leaker: { factor: 0.0451, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.00048, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
  connector_gas: {
    label: "Gas Connectors (Table 7-15)",
    leaker: { factor: 0.0152, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.00008, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
  flange_gas: {
    label: "Gas Flanges (Table 7-15)",
    leaker: { factor: 0.0850, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.00006, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
  prv_gas: {
    label: "Gas Relief Valves (Table 7-15)",
    leaker: { factor: 1.6900, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.0447, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
};

// ============================================================================
// MAIN COMPONENT: FugitivesForm
// ============================================================================

const FugitivesForm = ({ data = {}, onChange, sourceType = "default", setSourceType }) => {
  // 1. Synchronize Tier Mode
  // Tier 1 = default, Tier 2 = custom (equipment/component), Tier 3 = specific (measurement/screening/OGI)
  const activeTier = useMemo(() => {
    if (data.fugitive_tier) return data.fugitive_tier;
    if (sourceType === "specific") return "tier3";
    if (sourceType === "custom") return "tier2";
    return "tier1";
  }, [data.fugitive_tier, sourceType]);

  const setTier = (tier) => {
    onChange("fugitive_tier", tier);
    if (setSourceType) {
      if (tier === "tier1") setSourceType("default");
      else if (tier === "tier2") setSourceType("custom");
      else if (tier === "tier3") setSourceType("specific");
    }
  };

  // Sub-Method within Tier
  // Tier 2: equipment vs component
  const tier2SubMethod = data.fugitive_method === "equipment" ? "equipment" : "component";
  // Tier 3: method21, correlation, ogi, measurement
  const tier3Method = data.fugitive_method && ["method21", "correlation", "ogi", "measurement"].includes(data.fugitive_method)
    ? data.fugitive_method
    : "ogi";

  // Tier 1 State
  const selectedFacilityId = data.facility_type || "gas_production";
  const facilityCount = parseFloat(data.facility_count || data.amount || 1);
  const tier1DurationUnit = data.time_unit || (selectedFacilityId === "gathering_station" ? "hours" : "days");
  const tier1DurationValue = parseFloat(data.operating_days || data.operating_hours || (selectedFacilityId === "gathering_station" ? 8760 : 365));

  // Tier 2A State (Equipment)
  const tier2aSegment = data.equipment_segment || "gas_production";
  const tier2aEquipId = data.equipment_type || "wellhead";
  const tier2aCount = parseFloat(data.equipment_count || data.amount || 1);
  const tier2aHours = parseFloat(data.operating_hours || 8760);

  // Tier 2B State (Component)
  const tier2bSegment = data.component_segment || "gas_gathering";
  const tier2bService = data.service_type || "gas";
  const tier2bCompId = data.component_type || "valve";
  const tier2bCount = parseFloat(data.component_count || data.amount || 100);
  const tier2bHours = parseFloat(data.operating_hours || 8760);

  // Gas Stream Composition ($x_{CH4}$, $x_{CO2}$)
  const isCustomStream = data.use_custom_stream || false;
  const currentDefaultStream = useMemo(() => {
    if (activeTier === "tier2" && tier2SubMethod === "equipment") {
      return TIER2A_EQUIPMENT_DATA[tier2aSegment]?.default_stream || { ch4: 78.8, co2: 1.4 };
    }
    if (activeTier === "tier2" && tier2SubMethod === "component") {
      return TIER2B_COMPONENTS_DATA[tier2bSegment]?.services[tier2bService]?.default_stream || { ch4: 78.8, co2: 1.4 };
    }
    return { ch4: 78.8, co2: 1.4 };
  }, [activeTier, tier2SubMethod, tier2aSegment, tier2bSegment, tier2bService]);

  const ch4MolePct = parseFloat(data.ch4_mole_pct !== undefined ? data.ch4_mole_pct : currentDefaultStream.ch4);
  const co2MolePct = parseFloat(data.co2_mole_pct !== undefined ? data.co2_mole_pct : currentDefaultStream.co2);

  // Tier 3 OGI State
  const ogiCompId = data.component_type || "valve";
  const ogiLeakers = parseFloat(data.leakers_count || 1);
  const ogiNonLeakers = parseFloat(data.non_leakers_count || 0);
  const ogiHours = parseFloat(data.operating_hours || 8760);

  // Tier 3 Method 21 State
  const m21Key = data.m21_type || "valve_gas";
  const m21Ppm = parseFloat(data.screening_ppm || data.fugitive_ppm || 500);
  const m21Count = parseFloat(data.amount || data.screening_count || 1);
  const m21Hours = parseFloat(data.operating_hours || 8760);

  // Tier 3 Direct Measurement State
  const directRate = parseFloat(data.measured_rate || 0.5);
  const directRateUnit = data.rate_unit || "kg/hr";
  const directHours = parseFloat(data.operating_hours || 8760);

  // Duration unit options
  const durationUnitOptions = [
    { value: "hours", label: "Hours" },
    { value: "days", label: "Days (24h/day)" },
    { value: "months", label: "Months (30.4d/mo)" },
    { value: "year", label: "Years (8,760h/yr)" },
  ];

  // Helper to convert time value to normalized hours
  const getNormalizedHours = (val, unit) => {
    const v = parseFloat(val) || 0;
    if (unit === "days") return v * 24;
    if (unit === "months") return v * (8760 / 12);
    if (unit === "year" || unit === "years") return v * 8760;
    return v;
  };

  // Helper to convert flow rate to kg/hr
  const convertFlowToKgHr = (rate, unit) => {
    const r = parseFloat(rate) || 0;
    const u = (unit || "kg/hr").toLowerCase();
    if (u === "kg/hr") return r;
    if (u === "scf/hr" || u === "scfh") return r * 0.0192;
    if (u === "m3/hr" || u === "m3h") return r * 0.6785;
    if (u === "lb/hr" || u === "lb/h") return r * 0.45359237;
    if (u === "tonnes/yr" || u === "tonnes/year") return (r * 1000) / 8760;
    if (u === "kg/day") return r / 24;
    return r;
  };

  // ==========================================================================
  // REAL-TIME CLIENT-SIDE ESTIMATION ENGINE
  // ==========================================================================
  const estimate = useMemo(() => {
    let ch4_kg = 0;
    let co2_kg = 0;
    let citation = "";
    let methodology = "";
    let intermediateSteps = [];

    const GWP_CH4 = 28.0; // IPCC AR5 100-yr

    if (activeTier === "tier1") {
      const fac = TIER1_FACILITIES.find((f) => f.id === selectedFacilityId) || TIER1_FACILITIES[0];
      citation = `API Compendium (2021) ${fac.api_table}`;
      methodology = `Tier 1: Facility-Level Average (${fac.label})`;

      if (fac.id === "gathering_station") {
        const normHours = getNormalizedHours(tier1DurationValue, tier1DurationUnit);
        ch4_kg = facilityCount * fac.factor_ch4 * normHours;
        co2_kg = facilityCount * fac.factor_co2 * normHours;
        intermediateSteps.push(`Facility Count: ${facilityCount} stations`);
        intermediateSteps.push(`Duration: ${tier1DurationValue} ${tier1DurationUnit} (${normHours.toFixed(1)} hrs)`);
        intermediateSteps.push(`Factor: ${fac.factor_ch4} kg CH₄/hr, ${fac.factor_co2} kg CO₂/hr`);
      } else {
        const normDays = tier1DurationUnit === "hours" ? tier1DurationValue / 24 : tier1DurationValue;
        ch4_kg = facilityCount * fac.factor_ch4 * normDays;
        co2_kg = facilityCount * fac.factor_co2 * normDays;
        intermediateSteps.push(`Facility Count: ${facilityCount} facilities`);
        intermediateSteps.push(`Duration: ${tier1DurationValue} ${tier1DurationUnit} (${normDays.toFixed(1)} days)`);
        intermediateSteps.push(`Factor: ${fac.factor_ch4} kg CH₄/day, ${fac.factor_co2} kg CO₂/day`);
      }
    } else if (activeTier === "tier2" && tier2SubMethod === "equipment") {
      const seg = TIER2A_EQUIPMENT_DATA[tier2aSegment];
      const eq = seg.equipment.find((e) => e.id === tier2aEquipId) || seg.equipment[0];
      citation = `API Compendium (2021) ${seg.api_table}`;
      methodology = `Tier 2A: Equipment-Level (${seg.label} - ${eq.label})`;

      const normHours = tier2aHours;
      ch4_kg = tier2aCount * eq.factor * normHours;
      co2_kg = tier2aCount * (eq.co2_factor || eq.factor * (co2MolePct / Math.max(0.1, ch4MolePct))) * normHours;

      intermediateSteps.push(`Equipment: ${eq.label} (Count = ${tier2aCount})`);
      intermediateSteps.push(`Operating Hours: ${normHours} hrs`);
      intermediateSteps.push(`Factor: ${eq.factor} kg CH₄/hr/equipment`);
      intermediateSteps.push(`Stream: ${ch4MolePct}% CH₄, ${co2MolePct}% CO₂`);
    } else if (activeTier === "tier2" && tier2SubMethod === "component") {
      const seg = TIER2B_COMPONENTS_DATA[tier2bSegment];
      const srv = seg.services[tier2bService] || seg.services.gas;
      const comp = srv.components.find((c) => c.id === tier2bCompId) || srv.components[0];
      citation = `API Compendium (2021) ${seg.api_table}`;
      methodology = `Tier 2B: Component-Level (${seg.label} - ${srv.label} - ${comp.label})`;

      const normHours = tier2bHours;
      const totalTocKg = tier2bCount * comp.factor * normHours;
      const ch4Frac = ch4MolePct / 100.0;
      const co2Frac = co2MolePct / 100.0;

      ch4_kg = totalTocKg * ch4Frac;
      co2_kg = totalTocKg * co2Frac;

      intermediateSteps.push(`Component: ${comp.label} (${srv.label}, Count = ${tier2bCount})`);
      intermediateSteps.push(`TOC Factor: ${comp.factor} kg TOC/hr/component`);
      intermediateSteps.push(`Operating Hours: ${normHours} hrs (Total TOC = ${totalTocKg.toFixed(2)} kg)`);
      intermediateSteps.push(`Gas Stream Speciation: CH₄ = ${(ch4Frac * 100).toFixed(1)}%, CO₂ = ${(co2Frac * 100).toFixed(2)}%`);
    } else if (activeTier === "tier3" && tier3Method === "ogi") {
      const eq = OGI_LEAKER_FACTORS.find((o) => o.id === ogiCompId) || OGI_LEAKER_FACTORS[0];
      citation = "API Compendium Table 7-19 / EPA Subpart W Table W-1E";
      methodology = `Tier 3C: Optical Gas Imaging (OGI) Survey (${eq.label})`;

      const normHours = ogiHours;
      ch4_kg = ogiLeakers * eq.factor * normHours;
      co2_kg = ogiLeakers * (eq.co2_factor || eq.factor * 0.017) * normHours;

      intermediateSteps.push(`Detected Leakers: ${ogiLeakers} ${eq.label}`);
      intermediateSteps.push(`Operating Duration: ${normHours} hrs`);
      intermediateSteps.push(`Leaker Factor: ${eq.factor} kg CH₄/hr/leaker`);
      if (ogiNonLeakers > 0) {
        intermediateSteps.push(`Non-Leaker Population: ${ogiNonLeakers} components (zero leaker rate)`);
      }
    } else if (activeTier === "tier3" && tier3Method === "method21") {
      const mData = METHOD21_FACTORS[m21Key] || METHOD21_FACTORS.valve_gas;
      citation = "API Compendium Table 7-15 / EPA 453/R-95-017";
      const isLeaker = m21Ppm >= 10000;
      const targetFactor = isLeaker ? mData.leaker : mData.non_leaker;
      methodology = `Tier 3A: Method 21 (${mData.label} - ${targetFactor.label})`;

      const normHours = m21Hours;
      const totalToc = m21Count * targetFactor.factor * normHours;
      const ch4Frac = ch4MolePct / 100.0;
      const co2Frac = co2MolePct / 100.0;

      ch4_kg = totalToc * ch4Frac;
      co2_kg = totalToc * co2Frac;

      intermediateSteps.push(`Screening PPM: ${m21Ppm} ppmv (${isLeaker ? "≥ 10,000 ppmv Leaker" : "< 10,000 ppmv Non-Leaker"})`);
      intermediateSteps.push(`Component Count: ${m21Count} sources`);
      intermediateSteps.push(`TOC Factor: ${targetFactor.factor} kg TOC/hr`);
      intermediateSteps.push(`Duration: ${normHours} hrs`);
    } else if (activeTier === "tier3" && tier3Method === "measurement") {
      citation = "API Compendium Section 7.3.4 (Direct Measurement)";
      methodology = `Tier 3D: Direct Measurement (${directRateUnit})`;

      const normHours = directHours;
      const flowKgHr = convertFlowToKgHr(directRate, directRateUnit, ch4MolePct / 100.0);
      const ch4Frac = ch4MolePct / 100.0;
      const co2Frac = co2MolePct / 100.0;

      ch4_kg = flowKgHr * ch4Frac * normHours;
      co2_kg = flowKgHr * co2Frac * normHours;

      intermediateSteps.push(`Measured Rate: ${directRate} ${directRateUnit} (${flowKgHr.toFixed(3)} kg stream/hr)`);
      intermediateSteps.push(`Operating Hours: ${normHours} hrs`);
      intermediateSteps.push(`Gas Stream Speciation: CH₄ = ${(ch4Frac * 100).toFixed(1)}%, CO₂ = ${(co2Frac * 100).toFixed(2)}%`);
    }

    const ch4_tonnes = ch4_kg / 1000.0;
    const co2_tonnes = co2_kg / 1000.0;
    const co2e_tonnes = co2_tonnes + ch4_tonnes * GWP_CH4;

    return {
      ch4_kg,
      ch4_tonnes,
      co2_kg,
      co2_tonnes,
      co2e_tonnes,
      citation,
      methodology,
      intermediateSteps,
    };
  }, [
    activeTier,
    tier2SubMethod,
    tier3Method,
    selectedFacilityId,
    facilityCount,
    tier1DurationUnit,
    tier1DurationValue,
    tier2aSegment,
    tier2aEquipId,
    tier2aCount,
    tier2aHours,
    tier2bSegment,
    tier2bService,
    tier2bCompId,
    tier2bCount,
    tier2bHours,
    ch4MolePct,
    co2MolePct,
    ogiCompId,
    ogiLeakers,
    ogiNonLeakers,
    ogiHours,
    m21Key,
    m21Ppm,
    m21Count,
    m21Hours,
    directRate,
    directRateUnit,
    directHours,
  ]);

  return (
    <div className="fugitives-form-v2" style={{ fontFamily: "inherit" }}>
      {/* HEADER WITH ONSHORE BADGE */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          paddingBottom: "12px",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <div>
          <h4 style={{ margin: 0, color: "#111827", fontSize: "1.1rem", fontWeight: 700 }}>
            Onshore Equipment Leaks / Fugitives
          </h4>
          <span style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            API GHG Compendium (2021) Chapter 7 — Strictly Onshore Exploration, Production & Gathering
          </span>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <span
            style={{
              padding: "4px 8px",
              background: "#dbeafe",
              color: "#1e40af",
              borderRadius: "4px",
              fontSize: "0.75rem",
              fontWeight: 600,
            }}
          >
            API 2021 Ch. 7
          </span>
          <span
            style={{
              padding: "4px 8px",
              background: "#e0e7ff",
              color: "#4338ca",
              borderRadius: "4px",
              fontSize: "0.75rem",
              fontWeight: 600,
            }}
          >
            Onshore Only
          </span>
        </div>
      </div>

      {/* METHODOLOGY TIER SELECTOR */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#374151", marginBottom: "8px" }}>
          API Chapter 7 Calculation Tier
        </label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: "10px",
          }}
        >
          <button
            type="button"
            onClick={() => setTier("tier1")}
            style={{
              padding: "12px",
              borderRadius: "8px",
              border: activeTier === "tier1" ? "2px solid #2563eb" : "1px solid #d1d5db",
              background: activeTier === "tier1" ? "#eff6ff" : "#ffffff",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontWeight: 700, color: activeTier === "tier1" ? "#1e40af" : "#111827", fontSize: "0.9rem" }}>
                Tier 1: Facility-Level
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: activeTier === "tier1" ? "#bfdbfe" : "#f3f4f6",
                  color: "#1e3a8a",
                  fontWeight: 600,
                }}
              >
                Tables 7-1, 7-2
              </span>
            </div>
            <p style={{ margin: 0, fontSize: "0.75rem", color: "#6b7280", lineHeight: "1.3" }}>
              Whole facility or gathering station average emission rates. Ideal for high-level screening.
            </p>
          </button>

          <button
            type="button"
            onClick={() => setTier("tier2")}
            style={{
              padding: "12px",
              borderRadius: "8px",
              border: activeTier === "tier2" ? "2px solid #2563eb" : "1px solid #d1d5db",
              background: activeTier === "tier2" ? "#eff6ff" : "#ffffff",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontWeight: 700, color: activeTier === "tier2" ? "#1e40af" : "#111827", fontSize: "0.9rem" }}>
                Tier 2: Population
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: activeTier === "tier2" ? "#bfdbfe" : "#f3f4f6",
                  color: "#1e3a8a",
                  fontWeight: 600,
                }}
              >
                Tables 7-9, 7-11
              </span>
            </div>
            <p style={{ margin: 0, fontSize: "0.75rem", color: "#6b7280", lineHeight: "1.3" }}>
              Equipment or component count with service stream speciation (Gas, Light/Heavy Oil, Water/Oil).
            </p>
          </button>

          <button
            type="button"
            onClick={() => setTier("tier3")}
            style={{
              padding: "12px",
              borderRadius: "8px",
              border: activeTier === "tier3" ? "2px solid #2563eb" : "1px solid #d1d5db",
              background: activeTier === "tier3" ? "#eff6ff" : "#ffffff",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontWeight: 700, color: activeTier === "tier3" ? "#1e40af" : "#111827", fontSize: "0.9rem" }}>
                Tier 3: Detection / Meas.
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: activeTier === "tier3" ? "#bfdbfe" : "#f3f4f6",
                  color: "#1e3a8a",
                  fontWeight: 600,
                }}
              >
                Tables 7-15, 7-19
              </span>
            </div>
            <p style={{ margin: 0, fontSize: "0.75rem", color: "#6b7280", lineHeight: "1.3" }}>
              Optical Gas Imaging (OGI), Method 21 screening ranges, correlation equations, or direct measurement.
            </p>
          </button>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* TIER 1 INPUTS: FACILITY-LEVEL (TABLES 7-1, 7-2)                      */}
      {/* ==================================================================== */}
      {activeTier === "tier1" && (
        <div style={{ background: "#f9fafb", padding: "16px", borderRadius: "8px", border: "1px solid #e5e7eb", marginBottom: "20px" }}>
          <h5 style={{ margin: "0 0 12px 0", fontSize: "0.95rem", color: "#1f2937", fontWeight: 600 }}>
            Tier 1: Facility-Level Average Inputs
          </h5>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1.5fr", gap: "12px" }}>
            <div className="input-group">
              <label>Facility Type (API Table Citation)</label>
              <CustomDropdown
                options={TIER1_FACILITIES.map((f) => ({
                  value: f.id,
                  label: f.label,
                  subLabel: f.sub,
                }))}
                value={selectedFacilityId}
                onChange={(val) => {
                  onChange("facility_type", val);
                  const found = TIER1_FACILITIES.find((x) => x.id === val);
                  if (found) {
                    onChange("fuel", found.label);
                    onChange("unit", found.default_unit);
                    onChange("time_unit", found.id === "gathering_station" ? "hours" : "days");
                  }
                }}
              />
            </div>

            <div className="input-group">
              <label>Facility Count</label>
              <input
                type="number"
                min="1"
                step="1"
                className="mole-input"
                value={facilityCount}
                onChange={(e) => {
                  onChange("facility_count", e.target.value);
                  onChange("amount", e.target.value);
                }}
                placeholder="e.g. 1"
              />
            </div>

            <div className="input-group">
              <label>Operating Duration</label>
              <div style={{ display: "flex", gap: "6px" }}>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  style={{ flex: 1 }}
                  value={tier1DurationValue}
                  onChange={(e) => {
                    if (tier1DurationUnit === "days") onChange("operating_days", e.target.value);
                    else onChange("operating_hours", e.target.value);
                  }}
                  placeholder="365"
                />
                <div style={{ width: "130px" }}>
                  <CustomDropdown
                    options={durationUnitOptions}
                    value={tier1DurationUnit}
                    onChange={(val) => onChange("time_unit", val)}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TIER 2 INPUTS: EQUIPMENT OR COMPONENT POPULATION                     */}
      {/* ==================================================================== */}
      {activeTier === "tier2" && (
        <div style={{ background: "#f9fafb", padding: "16px", borderRadius: "8px", border: "1px solid #e5e7eb", marginBottom: "20px" }}>
          {/* Sub-method switch: Equipment vs Component */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            <button
              type="button"
              onClick={() => onChange("fugitive_method", "equipment")}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "6px",
                border: "none",
                background: tier2SubMethod === "equipment" ? "#2563eb" : "#e5e7eb",
                color: tier2SubMethod === "equipment" ? "#ffffff" : "#4b5563",
                fontWeight: 600,
                fontSize: "0.85rem",
                cursor: "pointer",
              }}
            >
              Tier 2A: Equipment-Level (Tables 7-9, 7-10, 7-29)
            </button>
            <button
              type="button"
              onClick={() => onChange("fugitive_method", "component")}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "6px",
                border: "none",
                background: tier2SubMethod === "component" ? "#2563eb" : "#e5e7eb",
                color: tier2SubMethod === "component" ? "#ffffff" : "#4b5563",
                fontWeight: 600,
                fontSize: "0.85rem",
                cursor: "pointer",
              }}
            >
              Tier 2B: Component-Level (Tables 7-11, 7-30)
            </button>
          </div>

          {/* Tier 2A: Equipment Count Form */}
          {tier2SubMethod === "equipment" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.2fr 0.8fr 1.2fr", gap: "12px" }}>
              <div className="input-group">
                <label>Industry Segment / Table</label>
                <CustomDropdown
                  options={Object.keys(TIER2A_EQUIPMENT_DATA).map((k) => ({
                    value: k,
                    label: TIER2A_EQUIPMENT_DATA[k].label,
                  }))}
                  value={tier2aSegment}
                  onChange={(val) => {
                    onChange("equipment_segment", val);
                    const defaultEq = TIER2A_EQUIPMENT_DATA[val]?.equipment[0]?.id;
                    if (defaultEq) onChange("equipment_type", defaultEq);
                  }}
                />
              </div>

              <div className="input-group">
                <label>Equipment Type</label>
                <CustomDropdown
                  options={TIER2A_EQUIPMENT_DATA[tier2aSegment]?.equipment.map((e) => ({
                    value: e.id,
                    label: e.label,
                    subLabel: `${e.factor} ${e.unit}`,
                  })) || []}
                  value={tier2aEquipId}
                  onChange={(val) => onChange("equipment_type", val)}
                />
              </div>

              <div className="input-group">
                <label>Equipment Count</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  className="mole-input"
                  value={tier2aCount}
                  onChange={(e) => {
                    onChange("equipment_count", e.target.value);
                    onChange("amount", e.target.value);
                    onChange("unit", "equipment");
                  }}
                  placeholder="1"
                />
              </div>

              <div className="input-group">
                <label>Operating Hours</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={tier2aHours}
                  onChange={(e) => onChange("operating_hours", e.target.value)}
                  placeholder="8760"
                />
              </div>
            </div>
          )}

          {/* Tier 2B: Component Count Form */}
          {tier2SubMethod === "component" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 0.8fr 1fr", gap: "10px" }}>
              <div className="input-group">
                <label>Segment / Table</label>
                <CustomDropdown
                  options={Object.keys(TIER2B_COMPONENTS_DATA).map((k) => ({
                    value: k,
                    label: TIER2B_COMPONENTS_DATA[k].label,
                  }))}
                  value={tier2bSegment}
                  onChange={(val) => {
                    onChange("component_segment", val);
                    onChange("service_type", "gas");
                  }}
                />
              </div>

              <div className="input-group">
                <label>Service Stream</label>
                <CustomDropdown
                  options={Object.keys(TIER2B_COMPONENTS_DATA[tier2bSegment]?.services || {}).map((s) => ({
                    value: s,
                    label: TIER2B_COMPONENTS_DATA[tier2bSegment].services[s].label,
                  }))}
                  value={tier2bService}
                  onChange={(val) => {
                    onChange("service_type", val);
                    const def = TIER2B_COMPONENTS_DATA[tier2bSegment]?.services[val]?.default_stream;
                    if (def && !isCustomStream) {
                      onChange("ch4_mole_pct", def.ch4);
                      onChange("co2_mole_pct", def.co2);
                    }
                  }}
                />
              </div>

              <div className="input-group">
                <label>Component Type</label>
                <CustomDropdown
                  options={TIER2B_COMPONENTS_DATA[tier2bSegment]?.services[tier2bService]?.components.map((c) => ({
                    value: c.id,
                    label: c.label,
                    subLabel: `${c.factor} ${c.unit}`,
                  })) || []}
                  value={tier2bCompId}
                  onChange={(val) => onChange("component_type", val)}
                />
              </div>

              <div className="input-group">
                <label>Component Count</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  className="mole-input"
                  value={tier2bCount}
                  onChange={(e) => {
                    onChange("component_count", e.target.value);
                    onChange("amount", e.target.value);
                    onChange("unit", "sources");
                  }}
                  placeholder="100"
                />
              </div>

              <div className="input-group">
                <label>Operating Hours</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={tier2bHours}
                  onChange={(e) => onChange("operating_hours", e.target.value)}
                  placeholder="8760"
                />
              </div>
            </div>
          )}

          {/* Gas Stream Composition Editor for Tier 2 */}
          <div
            style={{
              marginTop: "12px",
              paddingTop: "12px",
              borderTop: "1px solid #e5e7eb",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                id="custom-stream-check"
                checked={isCustomStream}
                onChange={(e) => {
                  onChange("use_custom_stream", e.target.checked);
                  if (!e.target.checked) {
                    onChange("ch4_mole_pct", currentDefaultStream.ch4);
                    onChange("co2_mole_pct", currentDefaultStream.co2);
                  }
                }}
              />
              <label htmlFor="custom-stream-check" style={{ fontSize: "0.82rem", color: "#374151", cursor: "pointer", fontWeight: 500 }}>
                Override default gas stream composition (Defaults: {currentDefaultStream.ch4}% CH₄, {currentDefaultStream.co2}% CO₂)
              </label>
            </div>

            {isCustomStream && (
              <div style={{ display: "flex", gap: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <span style={{ fontSize: "0.75rem", color: "#4b5563", fontWeight: 600 }}>CH₄:</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    style={{ width: "70px", padding: "4px 6px", borderRadius: "4px", border: "1px solid #d1d5db" }}
                    value={ch4MolePct}
                    onChange={(e) => onChange("ch4_mole_pct", e.target.value)}
                  />
                  <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>%</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <span style={{ fontSize: "0.75rem", color: "#4b5563", fontWeight: 600 }}>CO₂:</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    style={{ width: "70px", padding: "4px 6px", borderRadius: "4px", border: "1px solid #d1d5db" }}
                    value={co2MolePct}
                    onChange={(e) => onChange("co2_mole_pct", e.target.value)}
                  />
                  <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>%</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TIER 3 INPUTS: DETECTION & MEASUREMENT                               */}
      {/* ==================================================================== */}
      {activeTier === "tier3" && (
        <div style={{ background: "#f9fafb", padding: "16px", borderRadius: "8px", border: "1px solid #e5e7eb", marginBottom: "20px" }}>
          {/* Tier 3 sub-method navigation */}
          <div style={{ display: "flex", gap: "6px", marginBottom: "14px" }}>
            {TIER3_METHODS.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => onChange("fugitive_method", m.id)}
                style={{
                  flex: 1,
                  padding: "8px 10px",
                  borderRadius: "6px",
                  border: "none",
                  background: tier3Method === m.id ? "#2563eb" : "#e5e7eb",
                  color: tier3Method === m.id ? "#ffffff" : "#4b5563",
                  fontWeight: 600,
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Tier 3C: OGI Leaker Survey */}
          {tier3Method === "ogi" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr", gap: "12px" }}>
              <div className="input-group">
                <label>Component Leaker Type (Table 7-19 / W-1E)</label>
                <CustomDropdown
                  options={OGI_LEAKER_FACTORS.map((f) => ({
                    value: f.id,
                    label: f.label,
                    subLabel: `${f.factor} ${f.unit}`,
                  }))}
                  value={ogiCompId}
                  onChange={(val) => onChange("component_type", val)}
                />
              </div>

              <div className="input-group">
                <label>Detected Leakers Count</label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  className="mole-input"
                  value={ogiLeakers}
                  onChange={(e) => {
                    onChange("leakers_count", e.target.value);
                    onChange("amount", e.target.value);
                    onChange("unit", "leakers");
                  }}
                  placeholder="1"
                />
              </div>

              <div className="input-group">
                <label>Non-Leaker Population (Optional)</label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  className="mole-input"
                  value={ogiNonLeakers}
                  onChange={(e) => onChange("non_leakers_count", e.target.value)}
                  placeholder="0"
                />
              </div>

              <div className="input-group">
                <label>Survey Period / Hours</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={ogiHours}
                  onChange={(e) => onChange("operating_hours", e.target.value)}
                  placeholder="8760"
                />
              </div>
            </div>
          )}

          {/* Tier 3A: Method 21 Screening Ranges */}
          {tier3Method === "method21" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr", gap: "12px" }}>
              <div className="input-group">
                <label>Component Category (Table 7-15)</label>
                <CustomDropdown
                  options={Object.keys(METHOD21_FACTORS).map((k) => ({
                    value: k,
                    label: METHOD21_FACTORS[k].label,
                  }))}
                  value={m21Key}
                  onChange={(val) => onChange("m21_type", val)}
                />
              </div>

              <div className="input-group">
                <label>Screening Value (ppmv)</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={m21Ppm}
                  onChange={(e) => {
                    onChange("screening_ppm", e.target.value);
                    onChange("fugitive_ppm", e.target.value);
                  }}
                  placeholder="e.g. 15000"
                />
                <span style={{ fontSize: "0.72rem", color: m21Ppm >= 10000 ? "#dc2626" : "#059669", fontWeight: 600 }}>
                  {m21Ppm >= 10000 ? "≥ 10,000 ppmv (Leaker Factor Applied)" : "< 10,000 ppmv (Non-Leaker Factor Applied)"}
                </span>
              </div>

              <div className="input-group">
                <label>Component Count</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  className="mole-input"
                  value={m21Count}
                  onChange={(e) => {
                    onChange("amount", e.target.value);
                    onChange("unit", "sources");
                  }}
                  placeholder="1"
                />
              </div>

              <div className="input-group">
                <label>Operating Hours</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={m21Hours}
                  onChange={(e) => onChange("operating_hours", e.target.value)}
                  placeholder="8760"
                />
              </div>
            </div>
          )}

          {/* Tier 3B: Correlation Equations */}
          {tier3Method === "correlation" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr", gap: "12px" }}>
              <div className="input-group">
                <label>Correlation Curve (Table 7-17)</label>
                <CustomDropdown
                  options={[
                    { value: "gas_valve", label: "Gas Valves: Rate = 1.87e-6 × (PPM)^0.873" },
                    { value: "gas_connector", label: "Gas Connectors: Rate = 3.05e-6 × (PPM)^0.885" },
                    { value: "gas_flange", label: "Gas Flanges: Rate = 4.61e-6 × (PPM)^0.790" },
                    { value: "light_oil_valve", label: "Light Oil Valves: Rate = 6.41e-6 × (PPM)^0.797" },
                  ]}
                  value={data.correlation_type || "gas_valve"}
                  onChange={(val) => onChange("correlation_type", val)}
                />
              </div>

              <div className="input-group">
                <label>Measured PPMv</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.screening_ppm || 500}
                  onChange={(e) => {
                    onChange("screening_ppm", e.target.value);
                    onChange("fugitive_ppm", e.target.value);
                  }}
                  placeholder="e.g. 2500"
                />
              </div>

              <div className="input-group">
                <label>Source Count</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  className="mole-input"
                  value={data.amount || 1}
                  onChange={(e) => onChange("amount", e.target.value)}
                  placeholder="1"
                />
              </div>

              <div className="input-group">
                <label>Operating Hours</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.operating_hours || 8760}
                  onChange={(e) => onChange("operating_hours", e.target.value)}
                  placeholder="8760"
                />
              </div>
            </div>
          )}

          {/* Tier 3D: Direct Measurement */}
          {tier3Method === "measurement" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 1fr", gap: "12px" }}>
              <div className="input-group">
                <label>Direct Metered Leak Rate</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={directRate}
                  onChange={(e) => {
                    onChange("measured_rate", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  placeholder="0.5"
                />
              </div>

              <div className="input-group">
                <label>Flow Rate Unit</label>
                <CustomDropdown
                  options={[
                    { value: "kg/hr", label: "kg/hr" },
                    { value: "scf/hr", label: "scf/hr" },
                    { value: "m3/hr", label: "m³/hr" },
                    { value: "lb/hr", label: "lb/hr" },
                    { value: "tonnes/yr", label: "tonnes/yr" },
                  ]}
                  value={directRateUnit}
                  onChange={(val) => {
                    onChange("rate_unit", val);
                    onChange("unit", val);
                  }}
                />
              </div>

              <div className="input-group">
                <label>Operating Duration (hrs)</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={directHours}
                  onChange={(e) => onChange("operating_hours", e.target.value)}
                  placeholder="8760"
                />
              </div>

              <div className="input-group">
                <label>Stream CH₄ Mole %</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  className="mole-input"
                  value={ch4MolePct}
                  onChange={(e) => onChange("ch4_mole_pct", e.target.value)}
                  placeholder="78.8"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* REAL-TIME ESTIMATION PREVIEW & AUDIT BANNER                         */}
      {/* ==================================================================== */}
      <div
        style={{
          background: "#f0fdf4",
          border: "1px solid #bbf7d0",
          borderRadius: "8px",
          padding: "16px",
          marginTop: "16px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
          <div>
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "#166534",
              }}
            >
              Estimated Emissions Preview (Real-Time API Calculation)
            </span>
            <h5 style={{ margin: "4px 0 0 0", color: "#14532d", fontSize: "1.05rem", fontWeight: 700 }}>
              {estimate.co2e_tonnes.toFixed(3)} t CO₂e
            </h5>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{ fontSize: "0.75rem", color: "#166534", fontWeight: 600 }}>
              Citation: {estimate.citation}
            </span>
            <div style={{ fontSize: "0.7rem", color: "#4ade80" }}>
              IPCC AR5 GWP: CH₄ = 28.0 | CO₂ = 1.0
            </div>
          </div>
        </div>

        {/* Breakdown Pills */}
        <div style={{ display: "flex", gap: "16px", marginBottom: "12px", flexWrap: "wrap" }}>
          <div style={{ background: "#ffffff", padding: "6px 12px", borderRadius: "6px", border: "1px solid #dcfce7" }}>
            <span style={{ fontSize: "0.7rem", color: "#6b7280", display: "block" }}>Methane (CH₄)</span>
            <span style={{ fontSize: "0.9rem", fontWeight: 700, color: "#166534" }}>
              {estimate.ch4_tonnes.toFixed(4)} tonnes{" "}
              <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#4b5563" }}>
                ({estimate.ch4_kg.toFixed(1)} kg)
              </span>
            </span>
          </div>

          <div style={{ background: "#ffffff", padding: "6px 12px", borderRadius: "6px", border: "1px solid #dcfce7" }}>
            <span style={{ fontSize: "0.7rem", color: "#6b7280", display: "block" }}>Carbon Dioxide (CO₂)</span>
            <span style={{ fontSize: "0.9rem", fontWeight: 700, color: "#166534" }}>
              {estimate.co2_tonnes.toFixed(4)} tonnes{" "}
              <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "#4b5563" }}>
                ({estimate.co2_kg.toFixed(1)} kg)
              </span>
            </span>
          </div>

          <div style={{ background: "#ffffff", padding: "6px 12px", borderRadius: "6px", border: "1px solid #dcfce7" }}>
            <span style={{ fontSize: "0.7rem", color: "#6b7280", display: "block" }}>Methodology</span>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#1e3a8a" }}>
              {estimate.methodology}
            </span>
          </div>
        </div>

        {/* Calculation Audit Trace */}
        <div style={{ background: "rgba(255, 255, 255, 0.7)", padding: "8px 12px", borderRadius: "6px", fontSize: "0.75rem", color: "#374151" }}>
          <strong style={{ color: "#166534" }}>Calculation Audit Trail:</strong>
          <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
            {estimate.intermediateSteps.map((step, idx) => (
              <li key={idx} style={{ marginBottom: "2px" }}>
                {step}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default FugitivesForm;
