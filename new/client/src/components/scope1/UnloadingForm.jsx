import React, { useEffect } from "react";
import CustomDropdown from "../CustomDropdown";

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
  const currentTier = String(
    data.tier ||
      (sourceType === "specific"
        ? "tier3"
        : sourceType === "custom"
        ? "tier2"
        : "tier1")
  ).toLowerCase();

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
      const wellCount = data.well_count || data.wells || data.amount || 1;
      if (data.amount !== wellCount) onChange("amount", wellCount);
    } else if (isTier2) {
      if (data.unit !== "events") onChange("unit", "events");
      if (data.tier !== "tier2") onChange("tier", "tier2");
      if (!data.calc_method || data.calc_method.startsWith("api_equation")) {
        onChange("calc_method", "api_table_6_10");
      }
      const eventsCount = data.events || data.unload_events || data.unload_freq || data.amount || 10;
      if (data.amount !== eventsCount) onChange("amount", eventsCount);
    } else {
      if (data.unit !== "events") onChange("unit", "events");
      if (data.tier !== "tier3") onChange("tier", "tier3");
      const eventsCount = data.unload_events || data.unload_freq || data.events || data.amount || 12;
      if (data.amount !== eventsCount) onChange("amount", eventsCount);
    }
  }, [currentTier]);

  const handleTierSwitch = (newTier) => {
    onChange("tier", newTier);
    if (newTier === "tier1") {
      onChange("calc_method", "api_table_6_11");
      onChange("unit", "wells");
      onChange("amount", data.well_count || 1);
    } else if (newTier === "tier2") {
      onChange("calc_method", "api_table_6_10");
      onChange("unit", "events");
      onChange("amount", data.events || 10);
    } else {
      onChange("calc_method", "api_equation_6_10");
      onChange("unit", "events");
      onChange("amount", data.unload_events || 12);
    }
  };

  return (
    <div className="unloading-form" style={{ marginTop: "15px" }}>
      {/* HEADER & TIER BADGE */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          borderBottom: "1px solid var(--border-color, #e5e7eb)",
          paddingBottom: "10px",
        }}
      >
        <div>
          <h4 style={{ color: "var(--accent-color, #2563eb)", margin: 0 }}>
            Liquids Unloading Emissions
          </h4>
          <small style={{ color: "var(--text-muted, #6b7280)", fontSize: "0.8rem" }}>
            API GHG Compendium 2021 §6.3.4 (Tables 6-10, 6-11, Equations 6-10, 6-11, 6-3)
          </small>
        </div>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            className={`btn-tier ${isTier1 ? "active" : ""}`}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              background: isTier1 ? "var(--accent-color, #2563eb)" : "rgba(107, 114, 128, 0.1)",
              color: isTier1 ? "#fff" : "var(--text-primary, #374151)",
              border: "1px solid var(--border-color, #d1d5db)",
            }}
            onClick={() => handleTierSwitch("tier1")}
          >
            Tier 1: Per-Well
          </button>
          <button
            type="button"
            className={`btn-tier ${isTier2 ? "active" : ""}`}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              background: isTier2 ? "var(--accent-color, #2563eb)" : "rgba(107, 114, 128, 0.1)",
              color: isTier2 ? "#fff" : "var(--text-primary, #374151)",
              border: "1px solid var(--border-color, #d1d5db)",
            }}
            onClick={() => handleTierSwitch("tier2")}
          >
            Tier 2: Event-Based
          </button>
          <button
            type="button"
            className={`btn-tier ${isTier3 ? "active" : ""}`}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              background: isTier3 ? "var(--accent-color, #2563eb)" : "rgba(107, 114, 128, 0.1)",
              color: isTier3 ? "#fff" : "var(--text-primary, #374151)",
              border: "1px solid var(--border-color, #d1d5db)",
            }}
            onClick={() => handleTierSwitch("tier3")}
          >
            Tier 3: Engineering
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TIER 1: PER-WELL DEFAULT FACTOR (API TABLE 6-11) */}
      {/* ========================================================================= */}
      {isTier1 && (
        <div>
          <div
            style={{
              background: "rgba(59, 130, 246, 0.08)",
              border: "1px solid rgba(59, 130, 246, 0.25)",
              borderRadius: "6px",
              padding: "10px 14px",
              marginBottom: "16px",
              fontSize: "0.85rem",
              color: "var(--text-primary, #1e3a8a)",
            }}
          >
            <strong>API Table 6-11 Methodology:</strong> Used when unloading event counts are not monitored.
            Emissions are calculated per well-year using standard gas volume (113,466 scf for plunger; 178,531 scf for non-plunger)
            at 81.6 mol% CH₄ baseline with site gas composition adjustment.
          </div>

          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Unloading Lift Technology
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <select
                className="mole-input"
                value={unloadingType}
                onChange={(e) => {
                  onChange("unloading_type", e.target.value);
                  onChange("unload_type", e.target.value);
                }}
              >
                <option value="plunger">Plunger Lift (1,774 kg CH₄ / well-yr)</option>
                <option value="non_plunger">Non-Plunger Lift (2,792 kg CH₄ / well-yr)</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Number of Wells (well-years)
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="1"
                step="1"
                className="mole-input"
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
                Gas CH₄ Content (mol %)
                <small style={{ color: "#6b7280", marginLeft: "4px" }}>(Default: 81.6%)</small>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="mole-input"
                value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : 81.6}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="81.6"
              />
            </div>

            <div className="input-group">
              <label>
                Gas CO₂ Content (mol %)
                <small style={{ color: "#6b7280", marginLeft: "4px" }}>(Default: 0%)</small>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="mole-input"
                value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : 0}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="0.0"
              />
            </div>

            <div className="input-group">
              <label>
                Control / Flare Efficiency (%)
                <small style={{ color: "#6b7280", marginLeft: "4px" }}>(0% if directly vented)</small>
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                className="mole-input"
                value={data.control_efficiency !== undefined && data.control_efficiency !== null ? data.control_efficiency : 0}
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
          <div
            style={{
              background: "rgba(16, 185, 129, 0.08)",
              border: "1px solid rgba(16, 185, 129, 0.25)",
              borderRadius: "6px",
              padding: "10px 14px",
              marginBottom: "16px",
              fontSize: "0.85rem",
              color: "var(--text-primary, #065f46)",
            }}
          >
            <strong>API Table 6-10 Methodology:</strong> Event-based vented emissions for wells with monitored unloading event frequency.
            Supports national average frequency bins and regional basin factors (Appalachia, Gulf Coast, Midcontinent, Rocky Mountain).
          </div>

          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Unloading Lift Technology
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <select
                className="mole-input"
                value={unloadingType}
                onChange={(e) => {
                  onChange("unloading_type", e.target.value);
                  onChange("unload_type", e.target.value);
                }}
              >
                <option value="plunger">Plunger Lift</option>
                <option value="non_plunger">Non-Plunger Lift</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Total Unloading Events
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="0"
                step="1"
                className="mole-input"
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
              <select
                className="mole-input"
                value={selectedRegion}
                onChange={(e) => onChange("region", e.target.value)}
              >
                <option value="Average">National Average</option>
                <option value="appalachia">Appalachia Basin</option>
                <option value="gulf_coast">Gulf Coast Basin</option>
                <option value="midcontinent">Midcontinent Basin</option>
                <option value="rocky_mountain">Rocky Mountain Basin</option>
              </select>
            </div>

            <div className="input-group">
              <label>
                Number of Associated Wells
                <small style={{ color: "#6b7280", marginLeft: "4px" }}>(Default: 1)</small>
              </label>
              <input
                type="number"
                min="1"
                step="1"
                className="mole-input"
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
                Gas CH₄ Content (mol %)
                <small style={{ color: "#6b7280", marginLeft: "4px" }}>(Leave blank for table default)</small>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="mole-input"
                value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ""}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                placeholder="e.g. 85.3"
              />
            </div>

            <div className="input-group">
              <label>Gas CO₂ Content (mol %)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="mole-input"
                value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : ""}
                onChange={(e) => onChange("co2_content", e.target.value)}
                placeholder="e.g. 1.5"
              />
            </div>

            <div className="input-group">
              <label>Control / Flare Efficiency (%)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                className="mole-input"
                value={data.control_efficiency !== undefined && data.control_efficiency !== null ? data.control_efficiency : 0}
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
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", marginBottom: "6px", fontWeight: 600 }}>
              Engineering Calculation Methodology:
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
              <button
                type="button"
                style={{
                  padding: "8px 10px",
                  borderRadius: "6px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "center",
                  background: activeMethod === "api_equation_6_10" ? "var(--accent-color, #2563eb)" : "rgba(107, 114, 128, 0.08)",
                  color: activeMethod === "api_equation_6_10" ? "#fff" : "var(--text-primary, #374151)",
                  border: `1px solid ${activeMethod === "api_equation_6_10" ? "var(--accent-color, #2563eb)" : "var(--border-color, #d1d5db)"}`,
                }}
                onClick={() => onChange("calc_method", "api_equation_6_10")}
              >
                API Eq. 6-10 (Subpart W)
              </button>

              <button
                type="button"
                style={{
                  padding: "8px 10px",
                  borderRadius: "6px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "center",
                  background: activeMethod === "api_equation_6_11" ? "var(--accent-color, #2563eb)" : "rgba(107, 114, 128, 0.08)",
                  color: activeMethod === "api_equation_6_11" ? "#fff" : "var(--text-primary, #374151)",
                  border: `1px solid ${activeMethod === "api_equation_6_11" ? "var(--accent-color, #2563eb)" : "var(--border-color, #d1d5db)"}`,
                }}
                onClick={() => onChange("calc_method", "api_equation_6_11")}
              >
                API Eq. 6-11 (Auto Plunger)
              </button>

              <button
                type="button"
                style={{
                  padding: "8px 10px",
                  borderRadius: "6px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "center",
                  background: activeMethod === "api_equation_6_3" ? "var(--accent-color, #2563eb)" : "rgba(107, 114, 128, 0.08)",
                  color: activeMethod === "api_equation_6_3" ? "#fff" : "var(--text-primary, #374151)",
                  border: `1px solid ${activeMethod === "api_equation_6_3" ? "var(--accent-color, #2563eb)" : "var(--border-color, #d1d5db)"}`,
                }}
                onClick={() => onChange("calc_method", "api_equation_6_3")}
              >
                API Eq. 6-3 (Well Decomp.)
              </button>
            </div>
          </div>

          {/* METHOD 1: API EQUATION 6-10 (EPA SUBPART W) */}
          {activeMethod === "api_equation_6_10" && (
            <div>
              <div
                style={{
                  background: "rgba(99, 102, 241, 0.08)",
                  border: "1px solid rgba(99, 102, 241, 0.25)",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  marginBottom: "16px",
                  fontSize: "0.85rem",
                  color: "var(--text-primary, #312e81)",
                }}
              >
                <strong>API Equation 6-10 / EPA Subpart W:</strong>
                <br />
                <code>VR = [Events × 0.37×10⁻³ × D² × Depth × P] + [SFR × (HR - X) × Z]</code>
                <br />
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted, #4b5563)" }}>
                  Calculates wellbore blowdown volume plus flowing gas volume during unloading. X = 0.5 hr (plunger) or 1.0 hr (non-plunger).
                </span>
              </div>

              <div className="form-grid-2">
                <div className="input-group">
                  <label>
                    Unloading Technology
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <select
                    className="mole-input"
                    value={unloadingType}
                    onChange={(e) => {
                      onChange("unloading_type", e.target.value);
                      onChange("unload_type", e.target.value);
                    }}
                  >
                    <option value="plunger">Plunger Lift (X = 0.5 hr)</option>
                    <option value="non_plunger">Non-Plunger Lift (X = 1.0 hr)</option>
                  </select>
                </div>

                <div className="input-group">
                  <label>
                    Annual Unloading Events
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="mole-input"
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
                    Casing/Tubing Diameter (in)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.1"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="1"
                    min="1"
                    className="mole-input"
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
                    Shut-In Surface Pressure (psig)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    className="mole-input"
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
                    Sales Flow Rate (SFR) (scf/hr)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    className="mole-input"
                    value={data.sfr !== undefined && data.sfr !== null ? data.sfr : ""}
                    onChange={(e) => onChange("sfr", e.target.value)}
                    placeholder="e.g. 35000"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Venting Duration HR (hours/event)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    className="mole-input"
                    value={data.hours_open !== undefined && data.hours_open !== null ? data.hours_open : ""}
                    onChange={(e) => onChange("hours_open", e.target.value)}
                    placeholder="e.g. 1.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Gas CH₄ Content (mol %)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : 80.0}
                    onChange={(e) => onChange("ch4_content", e.target.value)}
                    placeholder="80.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>Gas CO₂ Content (mol %)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : 3.0}
                    onChange={(e) => onChange("co2_content", e.target.value)}
                    placeholder="3.0"
                  />
                </div>

                <div className="input-group">
                  <label>Control / Flare Efficiency (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.control_efficiency !== undefined && data.control_efficiency !== null ? data.control_efficiency : 0}
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
              <div
                style={{
                  background: "rgba(147, 51, 234, 0.08)",
                  border: "1px solid rgba(147, 51, 234, 0.25)",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  marginBottom: "16px",
                  fontSize: "0.85rem",
                  color: "var(--text-primary, #581c87)",
                }}
              >
                <strong>API Equation 6-11:</strong>
                <br />
                <code>VR = √[(Pshut - Patm) / (Pline - Psep)] × SFRp × Tp</code>
                <br />
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted, #4b5563)" }}>
                  Models vented gas volume per cycle from automated plunger lift well unloadings based on pressure expansion ratios.
                </span>
              </div>

              <div className="form-grid-2">
                <div className="input-group">
                  <label>
                    Shut-In Pressure Pshut (psia)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="14.7"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="0.1"
                    min="14.7"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="1"
                    min="0"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    className="mole-input"
                    value={data.t_p !== undefined && data.t_p !== null ? data.t_p : ""}
                    onChange={(e) => onChange("t_p", e.target.value)}
                    placeholder="e.g. 0.5"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>
                    Annual Unloading Events
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    className="mole-input"
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
                    Gas CH₄ Content (mol %)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : 85.0}
                    onChange={(e) => onChange("ch4_content", e.target.value)}
                    placeholder="85.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>Gas CO₂ Content (mol %)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : 1.0}
                    onChange={(e) => onChange("co2_content", e.target.value)}
                    placeholder="1.0"
                  />
                </div>

                <div className="input-group">
                  <label>Control / Flare Efficiency (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.control_efficiency !== undefined && data.control_efficiency !== null ? data.control_efficiency : 0}
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
              <div
                style={{
                  background: "rgba(234, 88, 12, 0.08)",
                  border: "1px solid rgba(234, 88, 12, 0.25)",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  marginBottom: "16px",
                  fontSize: "0.85rem",
                  color: "var(--text-primary, #9a3412)",
                }}
              >
                <strong>API Equation 6-3:</strong>
                <br />
                <code>V_std = (π/4) × D² × Depth × (P_abs / P_std) × (T_std / T_well) × (1 / Z)</code>
                <br />
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted, #4b5563)" }}>
                  Pure geometric wellbore column decompression with compressibility and temperature correction.
                </span>
              </div>

              <div className="form-grid-2">
                <div className="input-group">
                  <label>
                    Frequency (events/yr)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="mole-input"
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
                    Casing/Tubing Diameter (in)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.1"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="1"
                    min="1"
                    className="mole-input"
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
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    className="mole-input"
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
                    Gas CH₄ Content (mol %)
                    <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : 85.0}
                    onChange={(e) => onChange("ch4_content", e.target.value)}
                    placeholder="85.0"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>Gas CO₂ Content (mol %)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.co2_content !== undefined && data.co2_content !== null ? data.co2_content : 0}
                    onChange={(e) => onChange("co2_content", e.target.value)}
                    placeholder="e.g. 1"
                  />
                </div>

                <div className="input-group">
                  <label>Well Operating Temperature (°F)</label>
                  <input
                    type="number"
                    step="0.1"
                    className="mole-input"
                    value={data.unload_temp !== undefined && data.unload_temp !== null ? data.unload_temp : 60}
                    onChange={(e) => onChange("unload_temp", e.target.value)}
                    placeholder="60"
                  />
                </div>

                <div className="input-group">
                  <label>Control / Flare Efficiency (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    className="mole-input"
                    value={data.control_efficiency !== undefined && data.control_efficiency !== null ? data.control_efficiency : 0}
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
