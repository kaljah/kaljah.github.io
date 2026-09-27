import React, { useEffect, useMemo } from "react";
import CustomDropdown from "../CustomDropdown";
import { Segmented } from "./ui";

// ============================================================================
// API GHG COMPENDIUM (2021) CHAPTER 7 — ONSHORE REFERENCE TABLES & DATA
// ============================================================================

// BUG-110 / RC-17: Tier 1 facility-level factors are API Compendium 2021 Table 7-8 — per unit of
// PRODUCTION (the server's calculations/fugitive_onshore.py TABLE_7_8), not per facility-day.
// Factors in tonnes CH4 per unit; gas factors are on a 78.8 mol % CH4 basis.
const TIER1_FACILITIES = [
  {
    id: "oil_production",
    label: "Onshore Oil Production",
    sub: "0.5173 lb CH₄ per bbl oil produced",
    units: [
      { value: "bbl", label: "bbl oil", t_per_unit: 2.346e-4 },
      { value: "m3", label: "m³ oil", t_per_unit: 1.476e-3 },
    ],
  },
  {
    id: "gas_production",
    label: "Onshore Gas Production",
    sub: "57.33 lb CH₄ per 10⁶ scf gas produced",
    units: [
      { value: "MMscf", label: "MMscf gas", t_per_unit: 2.601e-2 },
      { value: "Mcf", label: "Mcf gas", t_per_unit: 2.601e-5 },
      { value: "scf", label: "scf gas", t_per_unit: 2.601e-8 },
      { value: "m3", label: "m³ gas", t_per_unit: 9.184e-7 },
    ],
  },
];

// RC-17 / BUG-110: equipment-level factors are the server catalog entries (API Compendium 2021
// Table 7-9 crude, Table 7-10 gas; verified against the Compendium text). `fuel` is the catalog key
// the server applies, so the preview and the saved record use the same factor. CH4 only.
const TIER2A_EQUIPMENT_DATA = {
  gas_production: {
    label: "Onshore Natural Gas Production",
    default_stream: { ch4: 78.8, co2: 0 },
    equipment: [
      { id: "wellhead", label: "Gas Wellhead", fuel: "Wellhead - Gas", factor: 0.018, unit: "kg CH₄/hr/well" },
      { id: "separator", label: "Separator", fuel: "Separator - Gas Production", factor: 0.0442, unit: "kg CH₄/hr/separator" },
      { id: "heater", label: "Gas Heater", fuel: "Heater - Gas Production", factor: 0.046, unit: "kg CH₄/hr/heater" },
      { id: "dehydrator", label: "Dehydrator", fuel: "Gas Dehydrator Unit - Fugitive Leaks", factor: 0.0713, unit: "kg CH₄/hr/dehydrator" },
      { id: "meter", label: "Meter / Piping", fuel: "Meter / Piping Run - Gas Production", factor: 0.0352, unit: "kg CH₄/hr/meter" },
      { id: "compressor_small", label: "Small Reciprocating Compressor", fuel: "Compressor - Gas Production Small Recip", factor: 0.212, unit: "kg CH₄/hr/compressor" },
      { id: "compressor_large", label: "Large Reciprocating Compressor", fuel: "Compressor - Gas Production Large Recip", factor: 12.2, unit: "kg CH₄/hr/compressor" },
    ],
  },
  oil_production: {
    label: "Onshore Crude Oil Production",
    default_stream: { ch4: 78.8, co2: 0 },
    equipment: [
      { id: "wellhead_light", label: "Wellhead - light crude", fuel: "Wellhead - Oil (Light Crude)", factor: 0.0156, unit: "kg CH₄/hr/well" },
      { id: "wellhead_heavy", label: "Wellhead - heavy crude", fuel: "Wellhead - Oil (Heavy Crude)", factor: 0.000663, unit: "kg CH₄/hr/well" },
      { id: "separator_light", label: "Separator - light crude", fuel: "Separator - Light Crude", factor: 0.041, unit: "kg CH₄/hr/separator" },
      { id: "separator_heavy", label: "Separator - heavy crude", fuel: "Separator - Heavy Crude", factor: 0.000679, unit: "kg CH₄/hr/separator" },
      { id: "heater_light", label: "Heater-treater - light crude", fuel: "Heater-Treater - Light Crude", factor: 0.0477, unit: "kg CH₄/hr/heater" },
      { id: "header_light", label: "Header - light crude", fuel: "Header - Light Crude", factor: 0.162, unit: "kg CH₄/hr/header" },
      { id: "header_heavy", label: "Header - heavy crude", fuel: "Header - Heavy Crude", factor: 0.000472, unit: "kg CH₄/hr/header" },
      { id: "tank_light", label: "Tank - light crude", fuel: "Storage Tank Fugitive - Light Crude", factor: 0.0275, unit: "kg CH₄/hr/tank" },
      { id: "compressor_small", label: "Small compressor - light crude", fuel: "Compressor - Small Reciprocating", factor: 0.0369, unit: "kg CH₄/hr/compressor" },
      { id: "compressor_large", label: "Large compressor - light crude", fuel: "Compressor - Large Reciprocating", factor: 13.1, unit: "kg CH₄/hr/compressor" },
    ],
  },
};

const TIER2B_COMPONENTS_DATA = {
  gas_gathering: {
    label: "Onshore Gas Production & Gathering",
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
    label: "Onshore Crude Production",
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
  { id: "method21", label: "Method 21 Screening Ranges", sub: "<10k vs ≥10k ppmv" },
  { id: "correlation", label: "Leak-Rate Correlation", sub: "Continuous leak rate" },
  { id: "ogi", label: "OGI Leaker Survey", sub: "Leakers vs non-leakers" },
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
    label: "Gas Valves",
    leaker: { factor: 0.0451, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.00048, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
  connector_gas: {
    label: "Gas Connectors",
    leaker: { factor: 0.0152, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.00008, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
  flange_gas: {
    label: "Gas Flanges",
    leaker: { factor: 0.0850, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.00006, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
  prv_gas: {
    label: "Gas Relief Valves",
    leaker: { factor: 1.6900, unit: "kg TOC/hr/source", label: "≥ 10,000 ppmv (Leaker)" },
    non_leaker: { factor: 0.0447, unit: "kg TOC/hr/source", label: "< 10,000 ppmv (Non-Leaker)" },
  },
};

// ============================================================================
// MAIN COMPONENT: FugitivesForm
// ============================================================================

const FugitivesForm = ({ data = {}, onChange, sourceType = "default" }) => {
  // One tier selector: the page-level Calculation Methodology control (sourceType) drives the tier;
  // data.fugitive_tier is kept in sync for the payload
  const activeTier = sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1";
  useEffect(() => {
    if (data.fugitive_tier !== activeTier) onChange("fugitive_tier", activeTier);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTier]);

  // Sub-Method within Tier
  // Tier 2: equipment vs component
  const tier2SubMethod = data.fugitive_method === "equipment" ? "equipment" : "component";
  // Tier 3: method21, correlation, ogi, measurement
  const tier3Method = data.fugitive_method && ["method21", "correlation", "ogi", "measurement"].includes(data.fugitive_method)
    ? data.fugitive_method
    : "ogi";

  // Tier 1 State
  const selectedFacilityId = TIER1_FACILITIES.some((f) => f.id === data.facility_type)
    ? data.facility_type
    : TIER1_FACILITIES[1].id;
  const tier1Fac = TIER1_FACILITIES.find((f) => f.id === selectedFacilityId);
  const tier1Unit = tier1Fac.units.some((u) => u.value === data.unit) ? data.unit : tier1Fac.units[0].value;

  // BUG-110: the displayed Tier 1 defaults are written into the form state, so what the preview
  // shows is what is submitted
  useEffect(() => {
    if (activeTier !== "tier1") return;
    if (data.facility_type !== selectedFacilityId) {
      onChange("fugitive_tier", "tier1");
      onChange("facility_type", selectedFacilityId);
      onChange("fuel", tier1Fac.label);
    }
    if (data.unit !== tier1Unit) onChange("unit", tier1Unit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTier, data.facility_type, data.unit]);

  // Tier 2A State (Equipment)
  const tier2aSegment = TIER2A_EQUIPMENT_DATA[data.equipment_segment] ? data.equipment_segment : "gas_production";
  const tier2aEquipId = TIER2A_EQUIPMENT_DATA[tier2aSegment].equipment.some((e) => e.id === data.equipment_type)
    ? data.equipment_type
    : TIER2A_EQUIPMENT_DATA[tier2aSegment].equipment[0].id;
  const tier2aCount = parseFloat(data.equipment_count || data.amount || 1);
  const tier2aHours = parseFloat(data.operating_hours || 8760);

  useEffect(() => {
    if (activeTier !== "tier2" || tier2SubMethod !== "equipment") return;
    const eqSel = TIER2A_EQUIPMENT_DATA[tier2aSegment].equipment.find((e) => e.id === tier2aEquipId);
    if (eqSel && data.fuel !== eqSel.fuel) onChange("fuel", eqSel.fuel);
    if (data.equipment_type !== tier2aEquipId) onChange("equipment_type", tier2aEquipId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTier, tier2SubMethod, tier2aSegment, tier2aEquipId, data.fuel]);

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



  // ==========================================================================
  // REAL-TIME CLIENT-SIDE ESTIMATION ENGINE
  // ==========================================================================

  return (
    <div className="fugitives-form-v2" style={{ fontFamily: "inherit" }}>
      {/* HEADER WITH ONSHORE BADGE */}

      {/* METHODOLOGY TIER SELECTOR */}

      {/* ==================================================================== */}
      {/* TIER 1 INPUTS: FACILITY-LEVEL (TABLES 7-1, 7-2)                      */}
      {/* ==================================================================== */}
      {activeTier === "tier1" && (
        <div className="s1-block">
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1.5fr", gap: "12px" }}>
            <div className="input-group">
              <label>Facility Type</label>
              <CustomDropdown
                options={TIER1_FACILITIES.map((f) => ({ value: f.id, label: f.label, subLabel: f.sub }))}
                value={selectedFacilityId}
                onChange={(val) => {
                  const found = TIER1_FACILITIES.find((x) => x.id === val);
                  onChange("facility_type", val);
                  if (found) {
                    onChange("fuel", found.label);
                    onChange("unit", found.units[0].value);
                  }
                }}
              />
            </div>

            <div className="input-group">
              <label>Production Volume</label>
              <input
                type="number"
                min="0"
                step="any"
                className="mole-input"
                value={data.amount ?? ""}
                onChange={(e) => onChange("amount", e.target.value)}
                placeholder="e.g. 120000"
              />
            </div>

            <div className="input-group">
              <label>Production Unit</label>
              <CustomDropdown
                options={tier1Fac.units.map((u) => ({ value: u.value, label: u.label }))}
                value={tier1Unit}
                onChange={(val) => onChange("unit", val)}
              />
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TIER 2 INPUTS: EQUIPMENT OR COMPONENT POPULATION                     */}
      {/* ==================================================================== */}
      {activeTier === "tier2" && (
        <div className="s1-block">
          <div style={{ marginBottom: "16px" }}>
            <Segmented
              ariaLabel="Tier 2 method"
              value={tier2SubMethod}
              onChange={(v) => onChange("fugitive_method", v)}
              options={[
                { value: "equipment", label: "Equipment count" },
                { value: "component", label: "Component count" },
              ]}
            />
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
        <div className="s1-block">
          <div style={{ marginBottom: "16px" }}>
            <Segmented
              ariaLabel="Tier 3 method"
              value={tier3Method}
              onChange={(v) => onChange("fugitive_method", v)}
              options={TIER3_METHODS.map((m) => ({ value: m.id, label: m.label }))}
            />
          </div>

          {/* Tier 3C: OGI Leaker Survey */}
          {tier3Method === "ogi" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr", gap: "12px" }}>
              <div className="input-group">
                <label>Component Leaker Type</label>
                <CustomDropdown
                  options={OGI_LEAKER_FACTORS.map((f) => ({
                    value: f.id,
                    label: f.label,
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
                <label>Component Category</label>
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
                <label>Correlation Curve</label>
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
    </div>
  );
};

export default FugitivesForm;
