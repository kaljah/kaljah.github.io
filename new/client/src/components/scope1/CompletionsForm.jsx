import React, { useEffect } from "react";
import CustomDropdown from "../CustomDropdown";

/**
 * CompletionsForm — Complete Onshore Well Completion Emissions UI
 * Primary Reference: API GHG Compendium 2021 §6.2.3 (Tables 6-5, 6-6, Equations 6-4, 6-5, 6-7, 6-12)
 *
 * Fully supports all three Neocarbon calculation tiers:
 *   - Tier 1: API Tabulated Default Factors (Tables 6-5 & 6-6)
 *             * Gas vs Oil wells
 *             * With Hydraulic Fracturing (HF) vs Without HF
 *             * Vented vs REC vs Flared
 *             * Footnote c site-specific gas composition scaling (CH4%, CO2%)
 *   - Tier 2: Engineering Operational Data Calculations
 *             * API Eq. 6-7: Flowback rate × vent duration before separation (V = V_Pi × T)
 *             * API Eq. 6-12: Liquid flowback volume × GOR minus gas to sales
 *             * Flowback Rate × Duration with explicit rate unit selector (Mcf/hr, Mcf/day, etc.)
 *   - Tier 3: Direct Measurement & Composition
 *             * API Eq. 6-4: Net metered gas flowback with injected N2 deduction (V_gas = V_t - EnF)
 *             * API Eq. 6-5: Initial unmetered flowback calculation Vi = (Ti × (V_gas / Tm)) / 2
 *             * Fate partitioning: Vented, Flared (with flare efficiency), REC, or Custom Split %
 */

// Tier 1 selection -> factor sent to the server (Tables 6-5 / 6-6 are applied there, with the
// flared case derived from the whole-gas factor); no values are kept on the client
const TIER1_FACTOR_MAP = {
  // Hydraulic Fracturing (API Table 6-5)
  "gas_hf_uncontrolled": {
    code: "CompGasHF_Uncontrolled",
    name: "Gas Well Completion - Hydraulic Fracturing (Uncontrolled / Vented)",
  },
  "gas_hf_rec": {
    code: "CompGasHF_REC",
    name: "Gas Well Completion - Hydraulic Fracturing (REC with Venting)",
  },
  "gas_hf_flared": {
    code: "CompGasHF_Uncontrolled",
    name: "Gas Well Completion - Hydraulic Fracturing (Flared)",
  },
  "oil_hf_uncontrolled": {
    code: "CompOilHF_Uncontrolled",
    name: "Oil Well Completion - Hydraulic Fracturing (Uncontrolled / Vented)",
  },
  "oil_hf_rec": {
    code: "CompOilHF_REC",
    name: "Oil Well Completion - Hydraulic Fracturing (REC with Venting)",
  },
  "oil_hf_flared": {
    code: "CompOilHF_Uncontrolled",
    name: "Oil Well Completion - Hydraulic Fracturing (Flared)",
  },
  // Without Hydraulic Fracturing (API Table 6-6)
  "gas_nohf_vented": {
    code: "CompGasNoHF_Vented",
    name: "Gas Well Completion - Without Hydraulic Fracturing (Vented)",
  },
  "gas_nohf_flared": {
    code: "CompGasNoHF_Vented",
    name: "Gas Well Completion - Without Hydraulic Fracturing (Flared)",
  },
  "oil_nohf_vented": {
    code: "CompOilNoHF_Vented",
    name: "Oil Well Completion - Without Hydraulic Fracturing (Vented)",
  },
  "oil_nohf_flared": {
    code: "CompOilNoHF_Vented",
    name: "Oil Well Completion - Without Hydraulic Fracturing (Flared)",
  },
};

const CompletionsForm = ({ data, onChange, sourceType }) => {
  // One tier selector: the page-level "Calculation Methodology" control (sourceType) drives the
  // tier; data.tier is kept in sync below for the payload
  const currentTier = sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1";

  const isTier1 = currentTier === "tier1" || currentTier === "1";
  const isTier2 = currentTier === "tier2" || currentTier === "2" || currentTier === "custom";
  const isTier3 = !isTier1 && !isTier2;

  // Tier 1 configuration state
  const wellType = data.well_type || "gas";
  const fracturing = data.fracturing === false || data.fracturing === "without_hf" || data.fracturing === "no_hf" ? "no_hf" : "hf";
  const disposition = data.comp_disposition || data.disposition || (fracturing === "hf" ? "uncontrolled" : "vented");

  // Lookup active Tier 1 factor
  const factorKey = `${wellType}_${fracturing}_${disposition}`;
  const activeT1Factor = TIER1_FACTOR_MAP[factorKey] || TIER1_FACTOR_MAP["gas_hf_uncontrolled"];

  // Tier 2 Active engineering method
  const activeMethod = String(
    data.calc_method || data.comp_method || "rate_duration"
  ).toLowerCase();

  // Tier 3 Active disposition
  const tier3Disposition = String(
    data.comp_disposition || data.disposition || "vented"
  ).toLowerCase();

  // Synchronize tier and default parameters
  useEffect(() => {
    if (isTier1) {
      if (data.unit !== "events") onChange("unit", "events");
      if (data.tier !== "tier1") onChange("tier", "tier1");
      if (!data.calc_method || data.calc_method.startsWith("api_equation")) {
        onChange("calc_method", "api_table_6_5");
      }
      if (activeT1Factor && data.fuel !== activeT1Factor.name) {
        onChange("fuel", activeT1Factor.name);
        onChange("factor_code", activeT1Factor.code);
      }
      const eventsCount = data.events || data.amount || "";  // never an invented count
      if (data.amount !== eventsCount) onChange("amount", eventsCount);
    } else if (isTier2) {
      if (data.unit !== "events") onChange("unit", "events");
      if (data.tier !== "tier2") onChange("tier", "tier2");
      if (!data.calc_method || data.calc_method.startsWith("api_table")) {
        onChange("calc_method", "rate_duration");
      }
      if (!data.comp_rate_unit) onChange("comp_rate_unit", "Mcf/hr");
      const eventsCount = data.events || data.amount || "";  // never an invented count
      if (data.amount !== eventsCount) onChange("amount", eventsCount);
    } else {
      if (data.tier !== "tier3") onChange("tier", "tier3");
      if (!data.volume_unit) onChange("volume_unit", "Mcf");
      if (!data.comp_injected_n2_unit) onChange("comp_injected_n2_unit", "scf");
      if (!data.comp_disposition) onChange("comp_disposition", "vented");
    }
    const cm = String(data.calc_method || "");
    const family = { tier1: (m) => m.startsWith("api_table"), tier2: (m) => ["rate_duration", "gor", "api_equation_6_7"].includes(m), tier3: (m) => m === "metered" };
    const dflt = { tier1: "api_table_6_5", tier2: "rate_duration", tier3: "metered" };
    if (!family[currentTier](cm)) onChange("calc_method", dflt[currentTier]);
  }, [currentTier, factorKey]);

  return (
    <div className="completions-form" style={{ marginTop: "15px" }}>
      {/* HEADER & TIER SELECTOR */}

      {/* ========================================================================= */}
      {/* TIER 1: API DEFAULT EMISSION FACTORS (TABLES 6-5 & 6-6) */}
      {/* ========================================================================= */}
      {isTier1 && (
        <div>

          <div className="form-grid-3" style={{ marginBottom: "16px" }}>
            <div className="input-group">
              <label>
                Well type
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <select
                className="mole-input"
                value={wellType}
                onChange={(e) => {
                  onChange("well_type", e.target.value);
                }}
              >
                <option value="gas">Gas Well</option>
                <option value="oil">Oil Well</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Fracturing
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <select
                className="mole-input"
                value={fracturing}
                onChange={(e) => {
                  const val = e.target.value;
                  onChange("fracturing", val === "hf");
                  if (val === "no_hf" && disposition === "rec") {
                    onChange("comp_disposition", "vented");
                    onChange("disposition", "vented");
                  }
                }}
              >
                <option value="hf">With Hydraulic Fracturing</option>
                <option value="no_hf">Without Hydraulic Fracturing</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Disposition
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <select
                className="mole-input"
                value={disposition}
                onChange={(e) => {
                  onChange("comp_disposition", e.target.value);
                  onChange("disposition", e.target.value);
                  if (e.target.value === "flared") {
                    onChange("comp_flare_eff", data.comp_flare_eff || 98);
                  }
                }}
              >
                {fracturing === "hf" ? (
                  <>
                    <option value="uncontrolled">Uncontrolled Venting</option>
                    <option value="rec">Reduced Emissions Completion (REC)</option>
                    <option value="flared">Flared Completion</option>
                  </>
                ) : (
                  <>
                    <option value="vented">Vented (Uncontrolled)</option>
                    <option value="flared">Flared Completion</option>
                  </>
                )}
              </select>
            </div>
          </div>

          {/* ACTIVE FACTOR BADGE */}

          <div className="form-grid-3">
            <div className="input-group">
              <label>
                Completions
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="1"
                step="1"
                className="mole-input"
                value={data.amount || data.events || "1"}
                onChange={(e) => {
                  onChange("amount", e.target.value);
                  onChange("events", e.target.value);
                }}
                placeholder="1"
                required
              />
            </div>

            <div className="input-group">
              <label>
                CH₄ (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ""}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="78.8"
              />
            </div>

            <div className="input-group">
              <label>
                CO₂ (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="mole-input"
                value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : ""}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="0.44"
              />
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TIER 2: ENGINEERING OPERATIONAL DATA CALCULATIONS */}
      {/* ========================================================================= */}
      {isTier2 && (
        <div>

          <div className="input-group" style={{ marginBottom: "16px" }}>
            <label>
              Model
              <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
            </label>
            <CustomDropdown
              options={[
                {
                  value: "rate_duration",
                  label: "Rate × duration",
                },
                {
                  value: "gor",
                  label: "Liquid Flowback × GOR",
                },
                {
                  value: "api_equation_6_7",
                  label: "Initial Production Rate × Vent Duration",
                },
              ]}
              value={activeMethod}
              onChange={(val) => onChange("calc_method", val)}
            />
          </div>

          {/* Model 1: Rate × Duration */}
          {activeMethod === "rate_duration" && (
            <div className="form-grid-3" style={{ marginBottom: "16px" }}>
              <div className="input-group">
                <label>
                  Flowback rate
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.comp_rate || ""}
                  onChange={(e) => onChange("comp_rate", e.target.value)}
                  placeholder="e.g. 50"
                  required
                />
              </div>

              <div className="input-group">
                <label>
                  Flowback Rate Unit
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <select
                  className="mole-input"
                  value={data.comp_rate_unit || "Mcf/hr"}
                  onChange={(e) => onChange("comp_rate_unit", e.target.value)}
                >
                  <option value="Mcf/hr">Mcf / hr (thousand scf / hr)</option>
                  <option value="Mcf/day">Mcf / day (thousand scf / day)</option>
                  <option value="scf/hr">scf / hr</option>
                  <option value="scf/day">scf / day</option>
                  <option value="m3/day">m³ / day</option>
                  <option value="m3/hr">m³ / hr</option>
                </select>
              </div>

              <div className="input-group">
                <label>
                  Duration (h)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  className="mole-input"
                  value={data.comp_duration || ""}
                  onChange={(e) => onChange("comp_duration", e.target.value)}
                  placeholder="e.g. 24"
                  required
                />
              </div>
            </div>
          )}

          {/* Model 2: Liquid × GOR (API Eq. 6-12) */}
          {activeMethod === "gor" && (
            <div className="form-grid-3" style={{ marginBottom: "16px" }}>
              <div className="input-group">
                <label>
                  Total Liquid Flowback (bbl)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.comp_liquid_bbl || ""}
                  onChange={(e) => onChange("comp_liquid_bbl", e.target.value)}
                  placeholder="e.g. 5000"
                  required
                />
              </div>

              <div className="input-group">
                <label>
                  Flowback GOR (scf/bbl)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.comp_gor || ""}
                  onChange={(e) => onChange("comp_gor", e.target.value)}
                  placeholder="e.g. 1500"
                  required
                />
              </div>

              <div className="input-group">
                <label>
                  Gas Produced to Sales (Mcf)
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.comp_gas_produced_mcf || ""}
                  onChange={(e) => onChange("comp_gas_produced_mcf", e.target.value)}
                  placeholder="0"
                />
              </div>
            </div>
          )}

          {/* Model 3: API Eq. 6-7 (V_cc = V_Pi × T) */}
          {activeMethod === "api_equation_6_7" && (
            <div className="form-grid-3" style={{ marginBottom: "16px" }}>
              <div className="input-group">
                <label>
                  Production / Well Test Rate (V_Pi)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  value={data.comp_daily_prod_rate || data.comp_rate || ""}
                  onChange={(e) => {
                    onChange("comp_daily_prod_rate", e.target.value);
                    onChange("comp_rate", e.target.value);
                  }}
                  placeholder="e.g. 250"
                  required
                />
              </div>

              <div className="input-group">
                <label>
                  Production Rate Unit
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <select
                  className="mole-input"
                  value={data.comp_prod_rate_unit || "Mcf/day"}
                  onChange={(e) => onChange("comp_prod_rate_unit", e.target.value)}
                >
                  <option value="Mcf/day">Mcf / day (thousand scf / day)</option>
                  <option value="Mcf/hr">Mcf / hr</option>
                  <option value="m3/day">m³ / day</option>
                  <option value="m3/hr">m³ / hr</option>
                </select>
              </div>

              <div className="input-group">
                <label>
                  Vent Duration Before Separation (hrs)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  className="mole-input"
                  value={data.comp_duration || data.vent_duration_hours || ""}
                  onChange={(e) => {
                    onChange("comp_duration", e.target.value);
                    onChange("vent_duration_hours", e.target.value);
                  }}
                  placeholder="e.g. 12"
                  required
                />
              </div>
            </div>
          )}

          {/* Gas Properties & Control for Tier 2 */}
          <div className="form-grid-4">
            <div className="input-group">
              <label>
                CH₄ (%)
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ""}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="e.g. 85"
                required
              />
            </div>

            <div className="input-group">
              <label>CO₂ (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.co2_content || ""}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="e.g. 1.5"
              />
            </div>

            <div className="input-group">
              <label>Flowback Disposition</label>
              <select
                className="mole-input"
                value={data.comp_disposition || "vented"}
                onChange={(e) => {
                  onChange("comp_disposition", e.target.value);
                  onChange("disposition", e.target.value);
                }}
              >
                <option value="vented">Vented directly to atmosphere</option>
                <option value="flared">Routed to Flare</option>
                <option value="rec">Recovered / REC (Zero Venting)</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Flare efficiency (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.comp_flare_eff || "98"}
                onChange={(e) => onChange("comp_flare_eff", e.target.value)}
                placeholder="98"
                disabled={data.comp_disposition !== "flared"}
              />
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TIER 3: DIRECT MEASUREMENT & FLOWBACK PARTITIONING */}
      {/* ========================================================================= */}
      {isTier3 && (
        <div>

          {/* Section 1: Metered Gas & Injected N2 Deduction */}
          <div className="form-grid-4" style={{ marginBottom: "16px" }}>
            <div className="input-group">
              <label>
                Metered volume
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="0"
                step="any"
                className="mole-input"
                value={data.comp_volume || data.flowback_volume || data.amount || ""}
                onChange={(e) => {
                  onChange("comp_volume", e.target.value);
                  onChange("flowback_volume", e.target.value);
                  onChange("amount", e.target.value);
                }}
                placeholder="e.g. 500"
                required
              />
            </div>

            <div className="input-group">
              <label>
                Volume Unit
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <select
                className="mole-input"
                value={data.volume_unit || "Mcf"}
                onChange={(e) => {
                  onChange("volume_unit", e.target.value);
                  onChange("unit", e.target.value);
                }}
              >
                <option value="Mcf">Mcf (thousand scf)</option>
                <option value="scf">scf</option>
                <option value="m3">m³</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Injected N₂
                <span
                  style={{ marginLeft: "4px", fontSize: "0.7rem", color: "#6b7280", cursor: "help" }}
                  title="Non-combustible gases such as nitrogen are deducted from total flowback volume. Injected CO2 is NOT deducted per API §6.2.3.1."
                >
                  ⓘ
                </span>
              </label>
              <input
                type="number"
                min="0"
                step="any"
                className="mole-input"
                value={data.comp_injected_n2 || ""}
                onChange={(e) => onChange("comp_injected_n2", e.target.value)}
                placeholder="0"
              />
            </div>

            <div className="input-group">
              <label>Injected N₂ Unit</label>
              <select
                className="mole-input"
                value={data.comp_injected_n2_unit || "scf"}
                onChange={(e) => onChange("comp_injected_n2_unit", e.target.value)}
              >
                <option value="scf">scf</option>
                <option value="Mcf">Mcf</option>
                <option value="m3">m³</option>
              </select>
            </div>
          </div>

          {/* Section 2: Initial Unmetered Flowback (API Eq. 6-5) */}
          <div
            style={{
              background: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: "6px",
              padding: "12px",
              marginBottom: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <label style={{ fontWeight: 600, fontSize: "0.85rem", color: "#374151", margin: 0 }}>
                Unmetered flowback
              </label>
            </div>
            <div className="form-grid-2">
              <div className="input-group">
                <label>
                  Unmetered time (h)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  className="mole-input"
                  value={data.comp_initial_flowback_hours || ""}
                  onChange={(e) => onChange("comp_initial_flowback_hours", e.target.value)}
                  placeholder="e.g. 4"
                />
              </div>

              <div className="input-group">
                <label>
                  Metered time (h)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  className="mole-input"
                  value={data.comp_duration || ""}
                  onChange={(e) => onChange("comp_duration", e.target.value)}
                  placeholder="e.g. 24"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Gas Composition */}
          <div className="form-grid-2" style={{ marginBottom: "16px" }}>
            <div className="input-group">
              <label>
                CH₄ (%)
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ""}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="e.g. 85.5"
                required
              />
            </div>

            <div className="input-group">
              <label>CO₂ (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.co2_content || ""}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="e.g. 1.2"
              />
            </div>

            <div className="input-group">
              <label>C₂+ (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                className="mole-input"
                value={data.comp_c2plus_content || ""}
                onChange={(e) => onChange("comp_c2plus_content", e.target.value)}
                placeholder="e.g. 5"
              />
            </div>
          </div>

          {/* Section 4: Gas Disposition / Fate Split */}
          <div className="input-group" style={{ marginBottom: "16px" }}>
            <label>
              Gas disposition
              <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
            </label>
            <CustomDropdown
              options={[
                { value: "vented", label: "100% Vented to Atmosphere" },
                { value: "flared", label: "100% Routed to Flare" },
                { value: "rec", label: "100% Recovered / Reduced Emissions Completion (REC)" },
                { value: "split", label: "Custom Disposition Split (% Vented / % Flared / % REC)" },
              ]}
              value={tier3Disposition}
              onChange={(val) => {
                onChange("comp_disposition", val);
                onChange("disposition", val);
              }}
            />
          </div>

          {tier3Disposition === "split" && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "6px",
                padding: "12px",
                marginBottom: "16px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontWeight: 600, fontSize: "0.85rem", color: "#166534" }}>
                  Custom Split Allocation (must sum to 100%)
                </span>
                {(() => {
                  const fV = parseFloat(data.comp_frac_vented || 0);
                  const fF = parseFloat(data.comp_frac_flared || 0);
                  const fR = parseFloat(data.comp_frac_recovered || 0);
                  const sumP = Math.round((fV > 1 ? fV : fV * 100) + (fF > 1 ? fF : fF * 100) + (fR > 1 ? fR : fR * 100));
                  return (
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: "0.85rem",
                        color: sumP === 100 ? "#16a34a" : "#dc2626",
                      }}
                    >
                      Total: {sumP}% {sumP === 100 ? "✓" : "⚠ (must equal 100%)"}
                    </span>
                  );
                })()}
              </div>

              <div className="form-grid-3">
                <div className="input-group">
                  <label>Vented (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    className="mole-input"
                    value={data.comp_frac_vented || ""}
                    onChange={(e) => {
                      onChange("comp_frac_vented", e.target.value);
                      onChange("frac_vented", e.target.value);
                    }}
                    placeholder="e.g. 20"
                  />
                </div>

                <div className="input-group">
                  <label>Flared (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    className="mole-input"
                    value={data.comp_frac_flared || ""}
                    onChange={(e) => {
                      onChange("comp_frac_flared", e.target.value);
                      onChange("frac_flared", e.target.value);
                    }}
                    placeholder="e.g. 50"
                  />
                </div>

                <div className="input-group">
                  <label>Recovered / REC (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    className="mole-input"
                    value={data.comp_frac_recovered || ""}
                    onChange={(e) => {
                      onChange("comp_frac_recovered", e.target.value);
                      onChange("frac_recovered", e.target.value);
                    }}
                    placeholder="e.g. 30"
                  />
                </div>
              </div>
            </div>
          )}

          {(tier3Disposition === "flared" || (tier3Disposition === "split" && parseFloat(data.comp_frac_flared || 0) > 0)) && (
            <div className="form-grid-2" style={{ marginBottom: "16px" }}>
              <div className="input-group">
                <label>
                  Flare efficiency (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  className="mole-input"
                  value={data.comp_flare_eff || "98"}
                  onChange={(e) => onChange("comp_flare_eff", e.target.value)}
                  placeholder="98"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CompletionsForm;
