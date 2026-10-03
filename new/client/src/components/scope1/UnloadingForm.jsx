import React, { useEffect } from "react";
import { Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../CustomDropdown";
import { Segmented } from "./ui";

/**
 * UnloadingForm — Complete Liquids Unloading UI Pipeline
 * Reference: API GHG Compendium 2021 Section 6.3.4
 * Supports:
 *   - Tier 1: API Table 6-11 Per-Well Default Factor (Plunger vs Non-Plunger)
 *   - Tier 2: API Table 6-10 Event-Based Factor (Frequency Bins & Regional Basins)
 *   - Tier 3: Engineering Models:
 *       * API Eq. 6-10 (EPA Subpart W W-8 / W-9 Integrated Formula)
 *       * API Eq. 6-11 (Automated Plunger Lift Vent Rate Formula)
 *       * API Eq. 6-3 (Volume-Based Wellbore Decompression Geometry)
 */
const UnloadingForm = ({ data, onChange, sourceType }) => {
  // Determine active tier: defaults to tier from data, or derives from sourceType
  // One tier selector: the page-level "Calculation Methodology" control (sourceType) drives the
  // tier; data.tier is kept in sync below for the payload
  const currentTier = sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1";

  const isTier1 = currentTier === "tier1" || currentTier === "1";
  const isTier2 = currentTier === "tier2" || currentTier === "2" || currentTier === "custom";
  const isTier3 = !isTier1 && !isTier2;

  // Active engineering method for Tier 3
  const activeMethod = String(
    data.calc_method || data.method || "api_equation_6_10"
  ).toLowerCase();

  // Selected unloading type (plunger vs non-plunger)
  const unloadingType = String(
    data.unloading_type || data.unload_type || "plunger"
  ).toLowerCase();

  // Region for Tier 2
  const selectedRegion = String(data.region || "Average");

  // Synchronize unit & amount based on active tier
  useEffect(() => {
    if (isTier1) {
      if (data.unit !== "wells") onChange("unit", "wells");
      if (data.tier !== "tier1") onChange("tier", "tier1");
      if (!data.calc_method || data.calc_method.startsWith("api_equation")) {
        onChange("calc_method", "api_table_6_11");
      }
      const wellCount = data.well_count || data.wells || data.amount || "";  // never an invented count
      if (data.amount !== wellCount) onChange("amount", wellCount);
    } else if (isTier2) {
      if (data.unit !== "events") onChange("unit", "events");
      if (data.tier !== "tier2") onChange("tier", "tier2");
      if (!data.calc_method || data.calc_method.startsWith("api_equation")) {
        onChange("calc_method", "api_table_6_10");
      }
      const eventsCount = data.events || data.unload_events || data.unload_freq || data.amount || "";  // never an invented count
      if (data.amount !== eventsCount) onChange("amount", eventsCount);
    } else {
      if (data.unit !== "events") onChange("unit", "events");
      if (data.tier !== "tier3") onChange("tier", "tier3");
      const eventsCount = data.unload_events || data.unload_freq || data.events || data.amount || "";  // never an invented count
      if (data.amount !== eventsCount) onChange("amount", eventsCount);
    }
    const cm = String(data.calc_method || "");
    const family = { tier1: (m) => m === "api_table_6_11", tier2: (m) => m === "api_table_6_10", tier3: (m) => m.startsWith("api_equation") };
    const dflt = { tier1: "api_table_6_11", tier2: "api_table_6_10", tier3: "api_equation_6_10" };
    if (!family[currentTier](cm)) onChange("calc_method", dflt[currentTier]);
  }, [currentTier]);

  return (
    <div className="unloading-form mt-[15px]!">
      {/* HEADER & TIER BADGE */}

      {/* ========================================================================= */}
      {/* TIER 1: PER-WELL DEFAULT FACTOR (API TABLE 6-11) */}
      {/* ========================================================================= */}
      {isTier1 && (
        <div>

          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Lift type
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <NativeSelect
                className="mole-input"
                value={unloadingType}
                onChange={(e) => {
                  onChange("unloading_type", e.target.value);
                  onChange("unload_type", e.target.value);
                }}
              >
                <option value="plunger">Plunger lift</option>
                <option value="non_plunger">Non-plunger</option>
              </NativeSelect>
            </div>

            <div className="input-group">
              <label>
                Wells
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <Input
                type="number"
                min="1"
                step="1"
               
                value={data.well_count || data.wells || data.amount || ""}
                onChange={(e) => {
                  onChange("well_count", e.target.value);
                  onChange("wells", e.target.value);
                  onChange("amount", e.target.value);
                  onChange("quantity", e.target.value);
                }}
                placeholder="e.g. 5"
                required
              />
            </div>

            <div className="input-group">
              <label>
                CH₄ (mol %)
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                max="100"
               
                value={data.ch4_content ?? ""}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="e.g. 81.6"
              />
            </div>

            <div className="input-group">
              <label>
                CO₂ (mol %)
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                max="100"
               
                value={data.co2_content ?? ""}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="0.0"
              />
            </div>

            <div className="input-group">
              <label>
                Control efficiency (%)
              </label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
               
                value={data.control_efficiency ?? ""}
                onChange={(e) => {
                  onChange("control_efficiency", e.target.value);
                  onChange("unload_flare_eff", e.target.value);
                }}
                placeholder="0"
              />
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TIER 2: EVENT-BASED EMISSION FACTORS (API TABLE 6-10) */}
      {/* ========================================================================= */}
      {isTier2 && (
        <div>

          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Lift type
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <NativeSelect
                className="mole-input"
                value={unloadingType}
                onChange={(e) => {
                  onChange("unloading_type", e.target.value);
                  onChange("unload_type", e.target.value);
                }}
              >
                <option value="plunger">Plunger Lift</option>
                <option value="non_plunger">Non-Plunger Lift</option>
              </NativeSelect>
            </div>

            <div className="input-group">
              <label>
                Events
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <Input
                type="number"
                min="0"
                step="1"
               
                value={data.events || data.unload_events || data.unload_freq || data.amount || ""}
                onChange={(e) => {
                  onChange("events", e.target.value);
                  onChange("unload_events", e.target.value);
                  onChange("unload_freq", e.target.value);
                  onChange("amount", e.target.value);
                  onChange("quantity", e.target.value);
                }}
                placeholder="e.g. 15"
                required
              />
            </div>

            <div className="input-group">
              <label>Region / Basin</label>
              <NativeSelect
                className="mole-input"
                value={selectedRegion}
                onChange={(e) => onChange("region", e.target.value)}
              >
                <option value="Average">National Average</option>
                <option value="appalachia">Appalachia Basin</option>
                <option value="gulf_coast">Gulf Coast Basin</option>
                <option value="midcontinent">Midcontinent Basin</option>
                <option value="rocky_mountain">Rocky Mountain Basin</option>
              </NativeSelect>
            </div>

            <div className="input-group">
              <label>
                Wells
              </label>
              <Input
                type="number"
                min="1"
                step="1"
               
                value={data.well_count || data.wells || 1}
                onChange={(e) => {
                  onChange("well_count", e.target.value);
                  onChange("wells", e.target.value);
                }}
                placeholder="1"
              />
            </div>

            <div className="input-group">
              <label>
                CH₄ (mol %)
              </label>
              <Input
                type="number"
                step="0.01"
                min="0"
                max="100"
               
                value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ""}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="e.g. 85.3"
              />
            </div>

            <div className="input-group">
              <label>CO₂ (mol %)</label>
              <Input
                type="number"
                step="0.01"
                min="0"
                max="100"
               
                value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : ""}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="e.g. 1.5"
              />
            </div>

            <div className="input-group">
              <label>Control efficiency (%)</label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
               
                value={data.control_efficiency ?? ""}
                onChange={(e) => {
                  onChange("control_efficiency", e.target.value);
                  onChange("unload_flare_eff", e.target.value);
                }}
                placeholder="0"
              />
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TIER 3: ENGINEERING / SITE-SPECIFIC MODELS */}
      {/* ========================================================================= */}
      {isTier3 && (
        <div>
          {/* METHOD SELECTION TABS */}
          <div className="mb-[16px]!">
            <Segmented
              ariaLabel="Engineering method"
              value={activeMethod}
              onChange={(v) => onChange("calc_method", v)}
              options={[
                { value: "api_equation_6_10", label: "Wellbore + flow" },
                { value: "api_equation_6_11", label: "Automated plunger" },
                { value: "api_equation_6_3", label: "Well decompression" },
              ]}
            />
          </div>

          {/* METHOD 1: API EQUATION 6-10 (EPA SUBPART W) */}
          {activeMethod === "api_equation_6_10" && (
            <div>

              <div className="form-grid-2">
                <div className="input-group">
                  <label>
                    Lift type
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <NativeSelect
                    className="mole-input"
                    value={unloadingType}
                    onChange={(e) => {
                      onChange("unloading_type", e.target.value);
                      onChange("unload_type", e.target.value);
                    }}
                  >
                    <option value="plunger">Plunger lift</option>
                    <option value="non_plunger">Non-plunger</option>
                  </NativeSelect>
                </div>

                <div className="input-group">
                  <label>
                    Events per year
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="1"
                   
                    value={data.unload_events || data.unload_freq || data.events || data.amount || ""}
                    onChange={(e) => {
                      onChange("unload_events", e.target.value);
                      onChange("unload_freq", e.target.value);
                      onChange("events", e.target.value);
                      onChange("amount", e.target.value);
                      onChange("quantity", e.target.value);
                    }}
                    placeholder="e.g. 12"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Tubing diameter (in)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.001"
                    min="0.1"
                   
                    value={data.unload_diam || data.diameter || ""}
                    onChange={(e) => {
                      onChange("unload_diam", e.target.value);
                      onChange("diameter", e.target.value);
                    }}
                    placeholder="e.g. 10.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Well Depth (ft)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="1"
                    min="1"
                   
                    value={data.unload_depth || data.well_depth || ""}
                    onChange={(e) => {
                      onChange("unload_depth", e.target.value);
                      onChange("well_depth", e.target.value);
                    }}
                    placeholder="e.g. 12000"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Shut-in pressure (psig)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                   
                    value={data.unload_press || data.pressure || ""}
                    onChange={(e) => {
                      onChange("unload_press", e.target.value);
                      onChange("pressure", e.target.value);
                    }}
                    placeholder="e.g. 250"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Sales flow rate (scf/hr)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="1"
                    min="0"
                   
                    value={data.sfr !== undefined && data.sfr !== null ? data.sfr : ""}
                    onChange={(e) => onChange("sfr", e.target.value)}
                    placeholder="e.g. 35000"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Venting time (h/event)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                   
                    value={data.hours_open !== undefined && data.hours_open !== null ? data.hours_open : ""}
                    onChange={(e) => onChange("hours_open", e.target.value)}
                    placeholder="e.g. 1.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    CH₄ (mol %)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                   
                    value={data.ch4_content ?? ""}
                    onChange={(e) => onChange("ch4_content", e.target.value)}
                    placeholder="e.g. 80.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>CO₂ (mol %)</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                   
                    value={data.co2_content ?? ""}
                    onChange={(e) => onChange("co2_content", e.target.value)}
                    placeholder="e.g. 3.0"
                  />
                </div>

                <div className="input-group">
                  <label>Control efficiency (%)</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                   
                    value={data.control_efficiency ?? ""}
                    onChange={(e) => {
                      onChange("control_efficiency", e.target.value);
                      onChange("unload_flare_eff", e.target.value);
                    }}
                    placeholder="0"
                  />
                </div>
              </div>
            </div>
          )}

          {/* METHOD 2: API EQUATION 6-11 (AUTOMATED PLUNGER LIFT) */}
          {activeMethod === "api_equation_6_11" && (
            <div>

              <div className="form-grid-2">
                <div className="input-group">
                  <label>
                    Shut-In Pressure Pshut (psia)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="14.7"
                   
                    value={data.p_shut !== undefined && data.p_shut !== null ? data.p_shut : ""}
                    onChange={(e) => onChange("p_shut", e.target.value)}
                    placeholder="e.g. 150"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Flow-Line Pressure Pline (psia)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="14.7"
                   
                    value={data.p_line !== undefined && data.p_line !== null ? data.p_line : ""}
                    onChange={(e) => onChange("p_line", e.target.value)}
                    placeholder="e.g. 100"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Separator Pressure Psep (psia)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                   
                    value={data.p_sep !== undefined && data.p_sep !== null ? data.p_sep : ""}
                    onChange={(e) => onChange("p_sep", e.target.value)}
                    placeholder="e.g. 50"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Gas Production Rate SFRp (scf/hr)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="1"
                    min="0"
                   
                    value={data.sfr_p !== undefined && data.sfr_p !== null ? data.sfr_p : ""}
                    onChange={(e) => onChange("sfr_p", e.target.value)}
                    placeholder="e.g. 12000"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Venting Time Tp (hours/event)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0"
                   
                    value={data.t_p !== undefined && data.t_p !== null ? data.t_p : ""}
                    onChange={(e) => onChange("t_p", e.target.value)}
                    placeholder="e.g. 0.5"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Events per year
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    min="1"
                    step="1"
                   
                    value={data.unload_events || data.events || data.amount || ""}
                    onChange={(e) => {
                      onChange("unload_events", e.target.value);
                      onChange("events", e.target.value);
                      onChange("amount", e.target.value);
                      onChange("quantity", e.target.value);
                    }}
                    placeholder="e.g. 50"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    CH₄ (mol %)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                   
                    value={data.ch4_content ?? ""}
                    onChange={(e) => onChange("ch4_content", e.target.value)}
                    placeholder="e.g. 85.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>CO₂ (mol %)</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                   
                    value={data.co2_content ?? ""}
                    onChange={(e) => onChange("co2_content", e.target.value)}
                    placeholder="e.g. 1.0"
                  />
                </div>

                <div className="input-group">
                  <label>Control efficiency (%)</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                   
                    value={data.control_efficiency ?? ""}
                    onChange={(e) => {
                      onChange("control_efficiency", e.target.value);
                      onChange("unload_flare_eff", e.target.value);
                    }}
                    placeholder="0"
                  />
                </div>
              </div>
            </div>
          )}

          {/* METHOD 3: API EQUATION 6-3 (VOLUME-BASED WELLBORE DECOMPRESSION) */}
          {activeMethod === "api_equation_6_3" && (
            <div>

              <div className="form-grid-2">
                <div className="input-group">
                  <label>
                    Frequency (events/yr)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="1"
                   
                    value={data.unload_freq || data.unload_events || data.events || data.amount || ""}
                    onChange={(e) => {
                      onChange("unload_freq", e.target.value);
                      onChange("unload_events", e.target.value);
                      onChange("events", e.target.value);
                      onChange("amount", e.target.value);
                      onChange("quantity", e.target.value);
                    }}
                    placeholder="e.g. 12"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Tubing diameter (in)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.001"
                    min="0.1"
                   
                    value={data.unload_diam || data.diameter || ""}
                    onChange={(e) => {
                      onChange("unload_diam", e.target.value);
                      onChange("diameter", e.target.value);
                    }}
                    placeholder="e.g. 2.5"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Well Depth (ft)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="1"
                    min="1"
                   
                    value={data.unload_depth || data.well_depth || ""}
                    onChange={(e) => {
                      onChange("unload_depth", e.target.value);
                      onChange("well_depth", e.target.value);
                    }}
                    placeholder="e.g. 5000"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Surface Pressure (psig)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                   
                    value={data.unload_press || data.pressure || ""}
                    onChange={(e) => {
                      onChange("unload_press", e.target.value);
                      onChange("pressure", e.target.value);
                    }}
                    placeholder="e.g. 150"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    CH₄ (mol %)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                   
                    value={data.ch4_content ?? ""}
                    onChange={(e) => onChange("ch4_content", e.target.value)}
                    placeholder="e.g. 85.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>CO₂ (mol %)</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                   
                    value={data.co2_content ?? ""}
                    onChange={(e) => onChange("co2_content", e.target.value)}
                    placeholder="e.g. 1"
                  />
                </div>

                <div className="input-group">
                  <label>Well Temperature (°F)</label>
                  <Input
                    type="number"
                    step="0.1"
                   
                    value={data.unload_temp ?? ""}
                    onChange={(e) => onChange("unload_temp", e.target.value)}
                    placeholder="60"
                  />
                </div>

                <div className="input-group">
                  <label>Control efficiency (%)</label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                   
                    value={data.control_efficiency ?? ""}
                    onChange={(e) => {
                      onChange("control_efficiency", e.target.value);
                      onChange("unload_flare_eff", e.target.value);
                    }}
                    placeholder="0"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UnloadingForm;
