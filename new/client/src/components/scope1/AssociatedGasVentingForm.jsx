import React, { useEffect } from "react";
import CustomDropdown from "../CustomDropdown";
import { formatNumber } from "../../utils/formatters";
import { Info, AlertTriangle, ShieldCheck, Activity, Flame, Wind } from "lucide-react";

/**
 * AssociatedGasVentingForm — Complete UI Pipeline for Associated Gas Venting
 * Reference: API GHG Compendium 2021 Section 6.3.1 (Equations 6-8, 6-9, Exhibits 6-5 & 6-6, Table 6-8)
 *
 * Supported Tiers:
 * - Tier 1: API Table 6-8 Default Factors (Crude throughput × Regional Basin EF, with Footnote b site composition adjustment)
 * - Tier 2: Engineering GOR Mass Balance (API Eq. 6-8 & 6-9: Oil × GOR × Duration, partitioning Recovered & Flared gas)
 * - Tier 3: Direct / Site-Specific Measurement (API Eq. 6-8: Measured vent flow rate × duration or total measured volume)
 */

export const TABLE_6_8_BASINS = [
  {
    value: "Associated Gas Venting - US Average",
    label: "US Average",
    basinKey: "us_average",
    ef_ch4_kg_bbl: 1.4,
    whole_gas_scf_bbl: 89.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Gulf Coast Basin (Basin 220)",
    label: "Gulf Coast Basin - Basin 220",
    basinKey: "gulf_coast",
    ef_ch4_kg_bbl: 0.7,
    whole_gas_scf_bbl: 47.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Anadarko Basin (Basin 360)",
    label: "Anadarko Basin - Basin 360",
    basinKey: "anadarko",
    ef_ch4_kg_bbl: 9.7,
    whole_gas_scf_bbl: 622.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Williston Basin (Basin 395)",
    label: "Williston Basin - Basin 395",
    basinKey: "williston",
    ef_ch4_kg_bbl: 8.9,
    whole_gas_scf_bbl: 570.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Permian Basin (Basin 430)",
    label: "Permian Basin - Basin 430",
    basinKey: "permian",
    ef_ch4_kg_bbl: 6.5,
    whole_gas_scf_bbl: 419.0,
    ch4_mol_basis: 81.6,
  },
  {
    value: "Associated Gas Venting - Other US Basins",
    label: "Other US Basins",
    basinKey: "other",
    ef_ch4_kg_bbl: 0.4,
    whole_gas_scf_bbl: 26.0,
    ch4_mol_basis: 81.6,
  },
];

const OIL_UNITS = [
  { value: "bbl", label: "Barrels (bbl)" },
  { value: "m3", label: "Cubic meters (m³)" },
  { value: "kbbl", label: "Thousand barrels (kbbl)" },
  { value: "mbbl", label: "Million barrels (mbbl)" },
];

const OIL_RATE_UNITS = [
  { value: "bbl/day", label: "Barrels / day (bpd)" },
  { value: "bbl", label: "Total barrels (bbl)" },
  { value: "m3/day", label: "Cubic meters / day (m³/day)" },
  { value: "m3", label: "Total cubic meters (m³)" },
];

const GOR_UNITS = [
  { value: "scf/bbl", label: "scf / bbl" },
  { value: "m3/m3", label: "m³ / m³ (sm³/sm³)" },
  { value: "sm3/m3", label: "sm³ / m³" },
];

const GAS_VOL_UNITS = [
  { value: "scf", label: "Standard cubic feet (scf)" },
  { value: "m3", label: "Cubic meters (m³)" },
  { value: "Mcf", label: "Thousand scf (Mcf)" },
  { value: "MMscf", label: "Million scf (MMscf)" },
];

const VENT_RATE_UNITS = [
  { value: "scfh", label: "scf / hour (scfh)" },
  { value: "scf/day", label: "scf / day (scfd)" },
  { value: "scfm", label: "scf / minute (scfm)" },
  { value: "m3/hr", label: "m³ / hour (m³/hr)" },
  { value: "m3/day", label: "m³ / day (m³/day)" },
];

const AssociatedGasVentingForm = ({ data = {}, onChange, sourceType, setSourceType }) => {
  // Determine current tier from data.tier or hoisted sourceType
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
  const isTier3 = currentTier === "tier3" || currentTier === "3" || currentTier === "specific";

  // Selected basin for Tier 1
  const selectedBasinValue = data.basin || data.fuel || "Associated Gas Venting - US Average";
  const selectedBasin =
    TABLE_6_8_BASINS.find((b) => b.value === selectedBasinValue) || TABLE_6_8_BASINS[0];

  // Tier 3 measurement mode (rate vs volume)
  const tier3Mode = data.tier3_mode || (data.vent_volume ? "volume" : "rate");

  // Keep top-level fuel, tier, and amount synchronized
  useEffect(() => {
    if (isTier1) {
      if (data.tier !== "tier1") onChange("tier", "tier1");
      if (data.calc_method !== "api_table_6_8") onChange("calc_method", "api_table_6_8");
      if (!data.fuel || !data.fuel.startsWith("Associated Gas Venting")) {
        onChange("fuel", selectedBasin.value);
        onChange("basin", selectedBasin.value);
      }
      const oilAmt = data.oil_production !== undefined ? data.oil_production : data.amount || 1000;
      if (data.amount !== oilAmt) onChange("amount", oilAmt);
      if (!data.oil_unit) onChange("oil_unit", data.unit || "bbl");
      if (data.unit !== (data.oil_unit || "bbl")) onChange("unit", data.oil_unit || "bbl");
    } else if (isTier2) {
      if (data.tier !== "tier2") onChange("tier", "tier2");
      if (data.calc_method !== "api_equation_6_8_6_9") onChange("calc_method", "api_equation_6_8_6_9");
      const oilAmt = data.oil_production !== undefined ? data.oil_production : data.amount || 500;
      if (data.amount !== oilAmt) onChange("amount", oilAmt);
      if (!data.oil_unit) onChange("oil_unit", "bbl/day");
      if (!data.gor_unit) onChange("gor_unit", "scf/bbl");
      if (data.ch4_content === undefined) onChange("ch4_content", 70.0);
      if (data.co2_content === undefined) onChange("co2_content", 10.0);
    } else if (isTier3) {
      if (data.tier !== "tier3") onChange("tier", "tier3");
      if (data.calc_method !== "api_equation_6_8_direct") onChange("calc_method", "api_equation_6_8_direct");
      if (data.ch4_content === undefined) onChange("ch4_content", 85.0);
      if (data.co2_content === undefined) onChange("co2_content", 0.0);
      if (!data.vent_rate_unit) onChange("vent_rate_unit", "scfh");
      if (!data.vent_volume_unit) onChange("vent_volume_unit", "scf");
    }
  }, [currentTier]);

  const handleTierSwitch = (newTier) => {
    onChange("tier", newTier);
    if (setSourceType) {
      if (newTier === "tier1") setSourceType("default");
      else if (newTier === "tier2") setSourceType("custom");
      else setSourceType("specific");
    }
    if (newTier === "tier1") {
      onChange("calc_method", "api_table_6_8");
      onChange("fuel", selectedBasin.value);
      onChange("basin", selectedBasin.value);
    } else if (newTier === "tier2") {
      onChange("calc_method", "api_equation_6_8_6_9");
      if (data.ch4_content === undefined) onChange("ch4_content", 70.0);
      if (data.co2_content === undefined) onChange("co2_content", 10.0);
    } else {
      onChange("calc_method", "api_equation_6_8_direct");
    }
  };

  // Convert gas volume helper for Tier 2 UI preview
  const toScf = (val, unit) => {
    const v = parseFloat(val) || 0;
    const u = String(unit || "scf").toLowerCase();
    if (u === "m3" || u === "sm3") return v * 35.3146667;
    if (u === "mcf") return v * 1000.0;
    if (u === "mmscf") return v * 1000000.0;
    return v;
  };

  // Live Tier 2 Balance Calculation
  const oilVal = parseFloat(data.oil_production !== undefined ? data.oil_production : data.amount || 0);
  const gorVal = parseFloat(data.gor || 0);
  const gorUnit = data.gor_unit || "scf/bbl";
  const gorScfBbl = gorUnit === "m3/m3" || gorUnit === "sm3/m3" ? gorVal * (35.3146667 / 0.1589873) : gorVal;

  const oilUnit = data.oil_unit || "bbl/day";
  const isRate = oilUnit.includes("/day");
  const oilBblRate = oilUnit.includes("m3") ? oilVal * 6.28981 : oilVal;
  const durationDays = parseFloat(data.venting_duration !== undefined ? data.venting_duration : 365);
  const totalPeriodDays = parseFloat(data.period_duration !== undefined ? data.period_duration : 365);

  const totalOilBbl = isRate ? oilBblRate * durationDays : oilBblRate;
  const totalProducedGasScf = totalOilBbl * gorScfBbl;

  const gasVolUnit = data.gas_volume_unit || "scf";
  const recoveredScf = toScf(data.recovered_gas_volume || 0, gasVolUnit);
  const flaredScf = toScf(data.flared_gas_volume || 0, gasVolUnit);
  const netVentedScf = Math.max(0, totalProducedGasScf - recoveredScf - flaredScf);

  // Gas composition validation
  const ch4MolPct = parseFloat(data.ch4_content !== undefined && data.ch4_content !== "" ? data.ch4_content : (isTier1 ? selectedBasin.ch4_mol_basis : isTier2 ? 70.0 : 85.0));
  const co2MolPct = parseFloat(data.co2_content !== undefined && data.co2_content !== "" ? data.co2_content : (isTier1 ? 0.0 : isTier2 ? 10.0 : 0.0));
  const sumMolPct = ch4MolPct + co2MolPct;
  const isCompositionInvalid = ch4MolPct < 0 || co2MolPct < 0 || sumMolPct > 100.01;

  // Mass balance violation
  const isMassBalanceViolated = isTier2 && totalProducedGasScf > 0 && (recoveredScf + flaredScf) > (totalProducedGasScf * 1.0001);

  // Duration warnings
  const isDurationExceeded = isTier2 && durationDays > totalPeriodDays;
  const isDurationMaxExceeded = isTier2 && durationDays > 366;

  // GOR anomaly
  const isGorHighAnomaly = isTier2 && gorScfBbl > 100000;

  // Live Emissions Estimation
  let estCh4Tonnes = 0;
  let estCo2Tonnes = 0;
  let estCo2eTonnes = 0;

  if (isTier1) {
    const bbl = oilUnit === "m3" ? oilVal * 6.28981 : oilUnit === "kbbl" ? oilVal * 1000 : oilVal;
    const baseEf = selectedBasin.ef_ch4_kg_bbl;
    const adjRatio = data.ch4_content ? ch4MolPct / selectedBasin.ch4_mol_basis : 1.0;
    const ch4Kg = bbl * baseEf * adjRatio;
    estCh4Tonnes = ch4Kg / 1000.0;
    if (co2MolPct > 0) {
      estCo2Tonnes = estCh4Tonnes * (co2MolPct / ch4MolPct) * (44.01 / 16.0425);
    }
    estCo2eTonnes = estCh4Tonnes * 28.0 + estCo2Tonnes * 1.0;
  } else if (isTier2) {
    const fCh4 = ch4MolPct / 100.0;
    const fCo2 = co2MolPct / 100.0;
    const lbCh4 = (netVentedScf * fCh4 * 16.0425) / 379.3;
    const lbCo2 = (netVentedScf * fCo2 * 44.01) / 379.3;
    estCh4Tonnes = lbCh4 / 2204.6226;
    estCo2Tonnes = lbCo2 / 2204.6226;
    estCo2eTonnes = estCh4Tonnes * 28.0 + estCo2Tonnes * 1.0;
  } else if (isTier3) {
    let ventScf = 0;
    if (tier3Mode === "volume") {
      const vol = parseFloat(data.vent_volume || 0);
      const u = data.vent_volume_unit || "scf";
      ventScf = toScf(vol, u);
    } else {
      const rate = parseFloat(data.vent_rate || 0);
      const dur = parseFloat(data.venting_duration || 0);
      const uRate = data.vent_rate_unit || "scfh";
      let rateScfh = rate;
      if (uRate === "scf/day") rateScfh = rate / 24.0;
      else if (uRate === "scfm") rateScfh = rate * 60.0;
      else if (uRate === "m3/hr") rateScfh = rate * 35.3146667;
      else if (uRate === "m3/day") rateScfh = (rate * 35.3146667) / 24.0;
      ventScf = rateScfh * dur;
    }
    const fCh4 = ch4MolPct / 100.0;
    const fCo2 = co2MolPct / 100.0;
    const lbCh4 = (ventScf * fCh4 * 16.0425) / 379.3;
    const lbCo2 = (ventScf * fCo2 * 44.01) / 379.3;
    estCh4Tonnes = lbCh4 / 2204.6226;
    estCo2Tonnes = lbCo2 / 2204.6226;
    estCo2eTonnes = estCh4Tonnes * 28.0 + estCo2Tonnes * 1.0;
  }

  return (
    <div className="associated-gas-venting-form" style={{ marginTop: "15px" }}>
      {/* HEADER & TIER SELECTOR */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          borderBottom: "1px solid var(--border-color, #e5e7eb)",
          paddingBottom: "12px",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Wind size={20} style={{ color: "var(--accent-color, #ff6600)" }} />
            <h4 style={{ color: "var(--accent-color, #ff6600)", margin: 0, fontWeight: 700 }}>
              Associated Gas Venting
            </h4>
          </div>
        </div>

        {/* Tier selection tabs */}
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            className={`btn-tier ${isTier1 ? "active" : ""}`}
            onClick={() => handleTierSwitch("tier1")}
            style={{
              padding: "5px 12px",
              borderRadius: "5px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              background: isTier1 ? "var(--accent-color, #ff6600)" : "#f3f4f6",
              color: isTier1 ? "#fff" : "#374151",
              border: isTier1 ? "1px solid #ff6600" : "1px solid #d1d5db",
              transition: "all 0.15s ease",
            }}
          >
            Tier 1: Regional Default
          </button>
          <button
            type="button"
            className={`btn-tier ${isTier2 ? "active" : ""}`}
            onClick={() => handleTierSwitch("tier2")}
            style={{
              padding: "5px 12px",
              borderRadius: "5px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              background: isTier2 ? "var(--accent-color, #ff6600)" : "#f3f4f6",
              color: isTier2 ? "#fff" : "#374151",
              border: isTier2 ? "1px solid #ff6600" : "1px solid #d1d5db",
              transition: "all 0.15s ease",
            }}
          >
            Tier 2: GOR Balance
          </button>
          <button
            type="button"
            className={`btn-tier ${isTier3 ? "active" : ""}`}
            onClick={() => handleTierSwitch("tier3")}
            style={{
              padding: "5px 12px",
              borderRadius: "5px",
              fontSize: "0.78rem",
              fontWeight: 600,
              cursor: "pointer",
              background: isTier3 ? "var(--accent-color, #ff6600)" : "#f3f4f6",
              color: isTier3 ? "#fff" : "#374151",
              border: isTier3 ? "1px solid #ff6600" : "1px solid #d1d5db",
              transition: "all 0.15s ease",
            }}
          >
            Tier 3: Measurement
          </button>
        </div>
      </div>

      {/* TIER 1 VIEW: Table 6-8 Regional Basins */}
      {isTier1 && (
        <div>
          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Regional Basin Factor
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <CustomDropdown
                options={TABLE_6_8_BASINS.map((b) => ({
                  value: b.value,
                  label: b.label,
                  subLabel: `${b.ef_ch4_kg_bbl} kg CH₄/bbl · Whole Gas: ${b.whole_gas_scf_bbl} scf/bbl`,
                }))}
                value={selectedBasinValue}
                onChange={(val) => {
                  onChange("basin", val);
                  onChange("fuel", val);
                  onChange("fuel_type", val);
                }}
              />
            </div>

            <div className="input-group">
              <label>
                Crude Oil Production Throughput
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  style={{ flex: 1 }}
                  placeholder="e.g. 5000"
                  value={data.oil_production !== undefined ? data.oil_production : data.amount || ""}
                  onChange={(e) => {
                    onChange("oil_production", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  required
                />
                <select
                  className="mole-input"
                  style={{ width: "130px" }}
                  value={data.oil_unit || data.unit || "bbl"}
                  onChange={(e) => {
                    onChange("oil_unit", e.target.value);
                    onChange("unit", e.target.value);
                  }}
                >
                  {OIL_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>
                      {u.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Factor Details Badge */}
          <div
            style={{
              padding: "10px 14px",
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              borderRadius: "6px",
              marginBottom: "16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "0.82rem",
            }}
          >
            <div>
              <span style={{ fontWeight: 600, color: "#166534" }}>
                {selectedBasin.label}:
              </span>{" "}
              <span style={{ color: "#15803d" }}>
                <strong>{selectedBasin.ef_ch4_kg_bbl} kg CH₄ / bbl crude</strong> (Whole gas: {selectedBasin.whole_gas_scf_bbl} scf/bbl, Basis: {selectedBasin.ch4_mol_basis}% CH₄)
              </span>
            </div>
          </div>

          {/* Footnote b Gas Composition Adjustment */}
          <div
            style={{
              padding: "14px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginBottom: "10px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "#334155",
              }}
            >
              <Info size={16} style={{ color: "#0284c7" }} />
              <span>Gas Composition Adjustment (Optional)</span>
            </div>
            <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "12px" }}>
              If site-specific gas analysis is available, the methane factor is adjusted by (X_CH₄ / {selectedBasin.ch4_mol_basis}%), and CO₂ emissions are calculated proportionally.
            </div>

            <div className="form-grid-2" style={{ marginBottom: 0 }}>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.8rem" }}>Site CH₄ Content (mol %)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  className="mole-input"
                  placeholder={`Default: ${selectedBasin.ch4_mol_basis}%`}
                  value={data.ch4_content !== undefined ? data.ch4_content : ""}
                  onChange={(e) => onChange("ch4_content", e.target.value)}
                />
              </div>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.8rem" }}>Site CO₂ Content (mol %)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  className="mole-input"
                  placeholder="Default: 0.0%"
                  value={data.co2_content !== undefined ? data.co2_content : ""}
                  onChange={(e) => onChange("co2_content", e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TIER 2 VIEW: Engineering GOR Mass Balance (API Eq. 6-8 & 6-9) */}
      {isTier2 && (
        <div>
          {/* Production Basis & GOR */}
          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Crude Oil Production Basis
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  style={{ flex: 1 }}
                  placeholder="e.g. 500"
                  value={data.oil_production !== undefined ? data.oil_production : data.amount || ""}
                  onChange={(e) => {
                    onChange("oil_production", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  required
                />
                <select
                  className="mole-input"
                  style={{ width: "150px" }}
                  value={data.oil_unit || "bbl/day"}
                  onChange={(e) => {
                    onChange("oil_unit", e.target.value);
                    onChange("unit", e.target.value);
                  }}
                >
                  {OIL_RATE_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>
                      {u.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="input-group">
              <label>
                Gas-to-Oil Ratio (GOR)
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  style={{ flex: 1 }}
                  placeholder="e.g. 800"
                  value={data.gor !== undefined ? data.gor : ""}
                  onChange={(e) => onChange("gor", e.target.value)}
                  required
                />
                <select
                  className="mole-input"
                  style={{ width: "120px" }}
                  value={data.gor_unit || "scf/bbl"}
                  onChange={(e) => onChange("gor_unit", e.target.value)}
                >
                  {GOR_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>
                      {u.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Venting Duration & Operating Days */}
          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Venting Duration
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="number"
                  min="0"
                  max="366"
                  step="any"
                  className="mole-input"
                  style={{ flex: 1 }}
                  placeholder="e.g. 365"
                  value={data.venting_duration !== undefined ? data.venting_duration : "365"}
                  onChange={(e) => onChange("venting_duration", e.target.value)}
                  required
                />
                <select
                  className="mole-input"
                  style={{ width: "100px" }}
                  value={data.duration_unit || "days"}
                  onChange={(e) => onChange("duration_unit", e.target.value)}
                >
                  <option value="days">days</option>
                  <option value="hours">hours</option>
                </select>
              </div>
            </div>

            <div className="input-group">
              <label>Period Operating Duration (days)</label>
              <input
                type="number"
                min="1"
                max="366"
                step="any"
                className="mole-input"
                placeholder="Default: 365"
                value={data.period_duration !== undefined ? data.period_duration : "365"}
                onChange={(e) => onChange("period_duration", e.target.value)}
              />
            </div>
          </div>

          {/* Gas Composition */}
          <div className="form-grid-2">
            <div className="input-group">
              <label>CH₄ Molar Concentration (mol %)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="mole-input"
                placeholder="Default: 70.0%"
                value={data.ch4_content !== undefined ? data.ch4_content : "70.0"}
                onChange={(e) => onChange("ch4_content", e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>CO₂ Molar Concentration (mol %)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="mole-input"
                placeholder="Default: 10.0%"
                value={data.co2_content !== undefined ? data.co2_content : "10.0"}
                onChange={(e) => onChange("co2_content", e.target.value)}
              />
            </div>
          </div>

          {/* Gas Volume Unit Selector for Partitioning */}
          <div style={{ marginBottom: "10px", display: "flex", justifyContent: "flex-end" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Partitioning unit:</span>
              <select
                className="mole-input"
                style={{ width: "110px", padding: "4px 8px", fontSize: "0.8rem" }}
                value={data.gas_volume_unit || "scf"}
                onChange={(e) => onChange("gas_volume_unit", e.target.value)}
              >
                {GAS_VOL_UNITS.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.value}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* DISPOSITION PARTITIONING CARD (Zero Double-Counting) */}
          <div
            style={{
              padding: "16px",
              background: "#f8fafc",
              border: "1px solid #cbd5e1",
              borderRadius: "8px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Flame size={16} style={{ color: "#ea580c" }} />
                <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "#1e293b" }}>
                  Gas Disposition Partitioning &amp; Mass Balance
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "0.72rem",
                  color: "#059669",
                  background: "#ecfdf5",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  border: "1px solid #a7f3d0",
                }}
              >
                <ShieldCheck size={14} />
                <span>Zero Double-Counting Verified</span>
              </div>
            </div>

            <div className="form-grid-3" style={{ marginBottom: "12px" }}>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.78rem" }}>
                  1. Produced Associated Gas
                </label>
                <input
                  type="text"
                  className="mole-input readonly"
                  disabled
                  value={`${formatNumber(totalProducedGasScf, 1)} scf`}
                />
              </div>

              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.78rem" }}>
                  2. Recovered Gas Volume ({gasVolUnit})
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  placeholder="e.g. 0"
                  value={data.recovered_gas_volume !== undefined ? data.recovered_gas_volume : ""}
                  onChange={(e) => onChange("recovered_gas_volume", e.target.value)}
                />
              </div>

              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.78rem" }}>
                  3. Flared Gas Volume ({gasVolUnit})
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  placeholder="e.g. 0"
                  value={data.flared_gas_volume !== undefined ? data.flared_gas_volume : ""}
                  onChange={(e) => onChange("flared_gas_volume", e.target.value)}
                />
              </div>
            </div>

            {/* Net Vented Stream Result */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 12px",
                background: "#eff6ff",
                border: "1px solid #bfdbfe",
                borderRadius: "6px",
                fontSize: "0.82rem",
              }}
            >
              <span style={{ color: "#1e40af", fontWeight: 600 }}>
                Net Atmospheric Vented Gas = Produced ({formatNumber(totalProducedGasScf, 0)} scf) − Recovered ({formatNumber(recoveredScf, 0)} scf) − Flared ({formatNumber(flaredScf, 0)} scf):
              </span>
              <span style={{ fontWeight: 700, color: "#1d4ed8", fontSize: "0.95rem" }}>
                {formatNumber(netVentedScf, 1)} scf ({(netVentedScf / 35.3146667).toFixed(1)} m³)
              </span>
            </div>

            <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "8px" }}>
              💡 Flared gas is partitioned out here so emissions from combustion are accounted for under Section 5 Flaring without double-counting.
            </div>
          </div>
        </div>
      )}

      {/* TIER 3 VIEW: Direct / Site-Specific Measurement (API Eq. 6-8) */}
      {isTier3 && (
        <div>
          {/* Measurement Mode Tabs */}
          <div
            style={{
              display: "flex",
              gap: "8px",
              marginBottom: "16px",
            }}
          >
            <button
              type="button"
              className={`btn-mode ${tier3Mode === "rate" ? "active" : ""}`}
              onClick={() => onChange("tier3_mode", "rate")}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "6px",
                fontSize: "0.82rem",
                fontWeight: 600,
                cursor: "pointer",
                background: tier3Mode === "rate" ? "#eff6ff" : "#f9fafb",
                color: tier3Mode === "rate" ? "#1d4ed8" : "#4b5563",
                border: tier3Mode === "rate" ? "1px solid #93c5fd" : "1px solid #e5e7eb",
              }}
            >
              Mode A: Measured Vent Flow Rate × Duration
            </button>
            <button
              type="button"
              className={`btn-mode ${tier3Mode === "volume" ? "active" : ""}`}
              onClick={() => onChange("tier3_mode", "volume")}
              style={{
                flex: 1,
                padding: "8px 12px",
                borderRadius: "6px",
                fontSize: "0.82rem",
                fontWeight: 600,
                cursor: "pointer",
                background: tier3Mode === "volume" ? "#eff6ff" : "#f9fafb",
                color: tier3Mode === "volume" ? "#1d4ed8" : "#4b5563",
                border: tier3Mode === "volume" ? "1px solid #93c5fd" : "1px solid #e5e7eb",
              }}
            >
              Mode B: Total Measured Vent Volume
            </button>
          </div>

          {tier3Mode === "rate" ? (
            <div className="form-grid-2">
              <div className="input-group">
                <label>
                  Measured Vent Flow Rate
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    className="mole-input"
                    style={{ flex: 1 }}
                    placeholder="e.g. 150"
                    value={data.vent_rate !== undefined ? data.vent_rate : ""}
                    onChange={(e) => {
                      onChange("vent_rate", e.target.value);
                      onChange("amount", e.target.value);
                    }}
                    required
                  />
                  <select
                    className="mole-input"
                    style={{ width: "130px" }}
                    value={data.vent_rate_unit || "scfh"}
                    onChange={(e) => onChange("vent_rate_unit", e.target.value)}
                  >
                    {VENT_RATE_UNITS.map((u) => (
                      <option key={u.value} value={u.value}>
                        {u.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="input-group">
                <label>
                  Venting Duration (hours)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  placeholder="e.g. 72"
                  value={data.venting_duration !== undefined ? data.venting_duration : ""}
                  onChange={(e) => onChange("venting_duration", e.target.value)}
                  required
                />
              </div>
            </div>
          ) : (
            <div className="input-group">
              <label>
                Total Measured Vent Gas Volume
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input"
                  style={{ flex: 1 }}
                  placeholder="e.g. 25000"
                  value={data.vent_volume !== undefined ? data.vent_volume : data.amount || ""}
                  onChange={(e) => {
                    onChange("vent_volume", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  required
                />
                <select
                  className="mole-input"
                  style={{ width: "140px" }}
                  value={data.vent_volume_unit || data.unit || "scf"}
                  onChange={(e) => {
                    onChange("vent_volume_unit", e.target.value);
                    onChange("unit", e.target.value);
                  }}
                >
                  {GAS_VOL_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>
                      {u.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Tier 3 Measured Gas Composition */}
          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Measured CH₄ Molar Fraction (mol %)
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="mole-input"
                placeholder="e.g. 85.0"
                value={data.ch4_content !== undefined ? data.ch4_content : "85.0"}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                required
              />
            </div>

            <div className="input-group">
              <label>Measured CO₂ Molar Fraction (mol %)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="mole-input"
                placeholder="e.g. 2.5"
                value={data.co2_content !== undefined ? data.co2_content : "0.0"}
                onChange={(e) => onChange("co2_content", e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {/* WARNING NOTIFICATIONS & AUDIT FLAGS */}
      {isCompositionInvalid && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 14px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "6px",
            marginBottom: "16px",
            color: "#991b1b",
            fontSize: "0.82rem",
          }}
        >
          <AlertTriangle size={16} />
          <span>
            <strong>Gas Composition Error:</strong> Sum of CH₄ ({ch4MolPct.toFixed(1)}%) and CO₂ ({co2MolPct.toFixed(1)}%) exceeds 100% (got {sumMolPct.toFixed(1)}%).
          </span>
        </div>
      )}

      {isMassBalanceViolated && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 14px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "6px",
            marginBottom: "16px",
            color: "#991b1b",
            fontSize: "0.82rem",
          }}
        >
          <AlertTriangle size={16} />
          <span>
            <strong>Mass Balance Violation:</strong> Recovered gas ({formatNumber(recoveredScf, 0)} scf) + Flared gas ({formatNumber(flaredScf, 0)} scf) exceeds total produced associated gas ({formatNumber(totalProducedGasScf, 0)} scf).
          </span>
        </div>
      )}

      {isDurationExceeded && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 14px",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "6px",
            marginBottom: "16px",
            color: "#92400e",
            fontSize: "0.82rem",
          }}
        >
          <AlertTriangle size={16} />
          <span>
            <strong>Duration Warning:</strong> Venting duration ({durationDays} days) exceeds total operating period duration ({totalPeriodDays} days).
          </span>
        </div>
      )}

      {isDurationMaxExceeded && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 14px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "6px",
            marginBottom: "16px",
            color: "#991b1b",
            fontSize: "0.82rem",
          }}
        >
          <AlertTriangle size={16} />
          <span>
            <strong>Duration Error:</strong> Venting duration ({durationDays} days) exceeds maximum annual days (366 days).
          </span>
        </div>
      )}

      {isGorHighAnomaly && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 14px",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "6px",
            marginBottom: "16px",
            color: "#92400e",
            fontSize: "0.82rem",
          }}
        >
          <AlertTriangle size={16} />
          <span>
            <strong>High GOR Audit Warning:</strong> GOR of {formatNumber(gorScfBbl, 0)} scf/bbl exceeds typical crude oil range (100,000 scf/bbl). Verify if reservoir fluid is gas-condensate.
          </span>
        </div>
      )}

      {/* LIVE CALCULATION PREVIEW CARD */}
      <div
        style={{
          background: "#f8fafc",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
          padding: "16px",
          marginTop: "10px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Activity size={16} style={{ color: "var(--accent-color, #ff6600)" }} />
            <span style={{ fontWeight: 600, fontSize: "0.85rem", color: "#1e293b" }}>
              Real-Time Emission Preview
            </span>
          </div>
          <span
            style={{
              fontSize: "0.72rem",
              padding: "2px 6px",
              borderRadius: "4px",
              background: isTier3 ? "#dbeafe" : isTier2 ? "#dcfce7" : "#ffedd5",
              color: isTier3 ? "#1e40af" : isTier2 ? "#166534" : "#9a3412",
              fontWeight: 600,
            }}
          >
            {isTier3 ? "Tier 3: CEMS / Meter" : isTier2 ? "Tier 2: Engineering GOR" : "Tier 1: Regional Default"}
          </span>
        </div>

        <div className="form-grid-3" style={{ marginBottom: 0 }}>
          <div
            style={{
              padding: "10px 12px",
              background: "white",
              borderRadius: "6px",
              border: "1px solid #e2e8f0",
            }}
          >
            <div style={{ fontSize: "0.72rem", color: "#64748b" }}>CH₄ Emissions</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
              {formatNumber(estCh4Tonnes, 4)} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>tonnes</span>
            </div>
            <div style={{ fontSize: "0.7rem", color: "#94a3b8" }}>
              ±40% default uncertainty
            </div>
          </div>

          <div
            style={{
              padding: "10px 12px",
              background: "white",
              borderRadius: "6px",
              border: "1px solid #e2e8f0",
            }}
          >
            <div style={{ fontSize: "0.72rem", color: "#64748b" }}>CO₂ Emissions</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
              {formatNumber(estCo2Tonnes, 4)} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>tonnes</span>
            </div>
            <div style={{ fontSize: "0.7rem", color: "#94a3b8" }}>
              ±20% default uncertainty
            </div>
          </div>

          <div
            style={{
              padding: "10px 12px",
              background: "white",
              borderRadius: "6px",
              border: "1px solid #e2e8f0",
            }}
          >
            <div style={{ fontSize: "0.72rem", color: "#64748b" }}>Total CO₂ Equivalent</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--accent-color, #ff6600)" }}>
              {formatNumber(estCo2eTonnes, 3)} <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>tCO₂e</span>
            </div>
            <div style={{ fontSize: "0.7rem", color: "#94a3b8" }}>
              IPCC AR5 GWP (CH₄=28, CO₂=1)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssociatedGasVentingForm;
