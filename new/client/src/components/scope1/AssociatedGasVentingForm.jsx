import React, { useEffect } from "react";
import { Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../CustomDropdown";
import { Segmented } from "./ui";
import { formatNumber } from "../../utils/formatters";
import { Info, AlertTriangle, ShieldCheck, Activity, Flame, Wind } from "lucide-react";
import { TABLE_6_8_BASINS } from "./agvBasins";

/**
 * AssociatedGasVentingForm — Complete UI Pipeline for Associated Gas Venting
 * Reference: API GHG Compendium 2021 Section 6.3.1 (Equations 6-8, 6-9, Exhibits 6-5 & 6-6, Table 6-8)
 *
 * Supported Tiers:
 * - Tier 1: API Table 6-8 Default Factors (Crude throughput × Regional Basin EF, with Footnote b site composition adjustment)
 * - Tier 2: Engineering GOR Mass Balance (API Eq. 6-8 & 6-9: Oil × GOR × Duration, partitioning Recovered & Flared gas)
 * - Tier 3: Direct / Site-Specific Measurement (API Eq. 6-8: Measured vent flow rate × duration or total measured volume)
 */


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

const AssociatedGasVentingForm = ({ data = {}, onChange, sourceType, periodDays }) => {
  // One tier selector: the page-level "Calculation Methodology" control (sourceType) drives the
  // tier; data.tier is kept in sync below for the payload
  const currentTier = sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1";

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
      const oilAmt = data.oil_production !== undefined ? data.oil_production : data.amount || "";  // the operator enters the oil production
      if (data.amount !== oilAmt) onChange("amount", oilAmt);
      if (!data.oil_unit) onChange("oil_unit", data.unit || "bbl");
      if (data.unit !== (data.oil_unit || "bbl")) onChange("unit", data.oil_unit || "bbl");
    } else if (isTier2) {
      if (data.tier !== "tier2") onChange("tier", "tier2");
      if (data.calc_method !== "api_equation_6_8_6_9") onChange("calc_method", "api_equation_6_8_6_9");
      const oilAmt = data.oil_production !== undefined ? data.oil_production : data.amount || "";  // the operator enters the oil production
      if (data.amount !== oilAmt) onChange("amount", oilAmt);
      if (!data.oil_unit) onChange("oil_unit", "bbl/day");
      if (!data.gor_unit) onChange("gor_unit", "scf/bbl");
    } else if (isTier3) {
      if (data.tier !== "tier3") onChange("tier", "tier3");
      if (data.calc_method !== "api_equation_6_8_direct") onChange("calc_method", "api_equation_6_8_direct");
      if (!data.vent_rate_unit) onChange("vent_rate_unit", "scfh");
      if (!data.vent_volume_unit) onChange("vent_volume_unit", "scf");
    }
  }, [currentTier]);

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
  const monthDays = periodDays || 365; // the record's month
  const durationDays = parseFloat(data.venting_duration !== undefined ? data.venting_duration : monthDays);
  const totalPeriodDays = parseFloat(data.period_duration !== undefined ? data.period_duration : monthDays);

  const totalOilBbl = isRate ? oilBblRate * durationDays : oilBblRate;
  const totalProducedGasScf = totalOilBbl * gorScfBbl;

  const gasVolUnit = data.gas_volume_unit || "scf";
  const recoveredScf = toScf(data.recovered_gas_volume || 0, gasVolUnit);
  const flaredScf = toScf(data.flared_gas_volume || 0, gasVolUnit);

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

  return (
    <div className="associated-gas-venting-form mt-[15px]!">
      {/* HEADER & TIER SELECTOR */}

      {/* TIER 1 VIEW: Table 6-8 Regional Basins */}
      {isTier1 && (
        <div>
          <div className="form-grid-2">
            <div className="input-group">
              <label>
                Basin
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <CustomDropdown
                options={TABLE_6_8_BASINS.map((b) => ({
                  value: b.value,
                  label: b.label,
                  
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
                Oil production
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div className="flex! gap-[8px]!">
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input flex-1!"
                 
                  placeholder="e.g. 5000"
                  value={data.oil_production !== undefined ? data.oil_production : data.amount || ""}
                  onChange={(e) => {
                    onChange("oil_production", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  required
                />
                <NativeSelect
                  className="mole-input w-[130px]!"
                 
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
                </NativeSelect>
              </div>
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
              <span>Gas composition</span>
            </div>

            <div className="form-grid-2 mb-[0px]!">
              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.8rem" }}>CH₄ (mol %)</label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                 
                  placeholder={`Default: ${selectedBasin.ch4_mol_basis}%`}
                  value={data.ch4_content !== undefined ? data.ch4_content : ""}
                  onChange={(e) => onChange("ch4_content", e.target.value)}
                />
              </div>
              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.8rem" }}>CO₂ (mol %)</label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                 
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
                Oil production
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div className="flex! gap-[8px]!">
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input flex-1!"
                 
                  placeholder="e.g. 500"
                  value={data.oil_production !== undefined ? data.oil_production : data.amount || ""}
                  onChange={(e) => {
                    onChange("oil_production", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  required
                />
                <NativeSelect
                  className="mole-input w-[150px]!"
                 
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
                </NativeSelect>
              </div>
            </div>

            <div className="input-group">
              <label>
                GOR
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div className="flex! gap-[8px]!">
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input flex-1!"
                 
                  placeholder="e.g. 800"
                  value={data.gor !== undefined ? data.gor : ""}
                  onChange={(e) => onChange("gor", e.target.value)}
                  required
                />
                <NativeSelect
                  className="mole-input w-[120px]!"
                 
                  value={data.gor_unit || "scf/bbl"}
                  onChange={(e) => onChange("gor_unit", e.target.value)}
                >
                  {GOR_UNITS.map((u) => (
                    <option key={u.value} value={u.value}>
                      {u.label}
                    </option>
                  ))}
                </NativeSelect>
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
              <div className="flex! gap-[8px]!">
                <input
                  type="number"
                  min="0"
                  max="366"
                  step="any"
                  className="mole-input flex-1!"
                 
                  placeholder={`e.g. ${monthDays}`}
                  value={data.venting_duration !== undefined ? data.venting_duration : String(monthDays)}
                  onChange={(e) => onChange("venting_duration", e.target.value)}
                  required
                />
                <NativeSelect
                  className="mole-input w-[100px]!"
                 
                  value={data.duration_unit || "days"}
                  onChange={(e) => onChange("duration_unit", e.target.value)}
                >
                  <option value="days">days</option>
                  <option value="hours">hours</option>
                </NativeSelect>
              </div>
            </div>

            <div className="input-group">
              <label>Period (days)</label>
              <Input
                type="number"
                min="1"
                max="366"
                step="any"
               
                placeholder={`Default: ${monthDays}`}
                value={data.period_duration !== undefined ? data.period_duration : String(monthDays)}
                onChange={(e) => onChange("period_duration", e.target.value)}
              />
            </div>
          </div>

          {/* Gas Composition */}
          <div className="form-grid-2">
            <div className="input-group">
              <label>CH₄ (mol %)</label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.01"
               
                placeholder="Default: 70.0%"
                value={data.ch4_content !== undefined ? data.ch4_content : "70.0"}
                onChange={(e) => onChange("ch4_content", e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>CO₂ (mol %)</label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.01"
               
                placeholder="Default: 10.0%"
                value={data.co2_content !== undefined ? data.co2_content : "10.0"}
                onChange={(e) => onChange("co2_content", e.target.value)}
              />
            </div>
          </div>

          {/* Gas Volume Unit Selector for Partitioning */}
          <div className="mb-[10px]! flex! justify-end!">
            <div className="flex! items-center! gap-[6px]!">
              <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Unit</span>
              <NativeSelect
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
              </NativeSelect>
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
              className="flex! items-center! justify-between! mb-[12px]!"
            >
              <div className="flex! items-center! gap-[6px]!">
                <Flame size={16} style={{ color: "#ea580c" }} />
                <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "#1e293b" }}>
                  Gas disposition
                </span>
              </div>
            </div>

            <div className="form-grid-3 mb-[12px]!">
              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.78rem" }}>
                  Produced
                </label>
                <input
                  type="text"
                  className="mole-input readonly"
                  disabled
                  value={`${formatNumber(totalProducedGasScf, 1)} scf`}
                />
              </div>

              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.78rem" }}>
                  Recovered ({gasVolUnit})
                </label>
                <Input
                  type="number"
                  min="0"
                  step="any"
                 
                  placeholder="e.g. 0"
                  value={data.recovered_gas_volume !== undefined ? data.recovered_gas_volume : ""}
                  onChange={(e) => onChange("recovered_gas_volume", e.target.value)}
                />
              </div>

              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.78rem" }}>
                  Flared ({gasVolUnit})
                </label>
                <Input
                  type="number"
                  min="0"
                  step="any"
                 
                  placeholder="e.g. 0"
                  value={data.flared_gas_volume !== undefined ? data.flared_gas_volume : ""}
                  onChange={(e) => onChange("flared_gas_volume", e.target.value)}
                />
              </div>
            </div>

            {/* Net Vented Stream Result */}

          </div>
        </div>
      )}

      {/* TIER 3 VIEW: Direct / Site-Specific Measurement (API Eq. 6-8) */}
      {isTier3 && (
        <div>
          {/* Measurement Mode Tabs */}
          <div className="mb-[16px]!">
            <Segmented
              ariaLabel="Measurement mode"
              value={tier3Mode}
              onChange={(v) => onChange("tier3_mode", v)}
              options={[
                { value: "rate", label: "Rate × duration" },
                { value: "volume", label: "Total volume" },
              ]}
            />
          </div>

          {tier3Mode === "rate" ? (
            <div className="form-grid-2">
              <div className="input-group">
                <label>
                  Vent rate
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <div className="flex! gap-[8px]!">
                  <input
                    type="number"
                    min="0"
                    step="any"
                    className="mole-input flex-1!"
                   
                    placeholder="e.g. 150"
                    value={data.vent_rate !== undefined ? data.vent_rate : ""}
                    onChange={(e) => {
                      onChange("vent_rate", e.target.value);
                      onChange("amount", e.target.value);
                    }}
                    required
                  />
                  <NativeSelect
                    className="mole-input w-[130px]!"
                   
                    value={data.vent_rate_unit || "scfh"}
                    onChange={(e) => onChange("vent_rate_unit", e.target.value)}
                  >
                    {VENT_RATE_UNITS.map((u) => (
                      <option key={u.value} value={u.value}>
                        {u.label}
                      </option>
                    ))}
                  </NativeSelect>
                </div>
              </div>

              <div className="input-group">
                <label>
                  Venting time (h)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <Input
                  type="number"
                  min="0"
                  step="any"
                 
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
              <div className="flex! gap-[8px]!">
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="mole-input flex-1!"
                 
                  placeholder="e.g. 25000"
                  value={data.vent_volume !== undefined ? data.vent_volume : data.amount || ""}
                  onChange={(e) => {
                    onChange("vent_volume", e.target.value);
                    onChange("amount", e.target.value);
                  }}
                  required
                />
                <NativeSelect
                  className="mole-input w-[140px]!"
                 
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
                </NativeSelect>
              </div>
            </div>
          )}

          {/* Tier 3 Measured Gas Composition */}
          <div className="form-grid-2">
            <div className="input-group">
              <label>
                CH₄ (mol %)
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.01"
               
                placeholder="e.g. 85.0"
                value={data.ch4_content !== undefined ? data.ch4_content : "85.0"}
                onChange={(e) => onChange("ch4_content", e.target.value)}
                required
              />
            </div>

            <div className="input-group">
              <label>CO₂ (mol %)</label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.01"
               
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
    </div>
  );
};

export default AssociatedGasVentingForm;
