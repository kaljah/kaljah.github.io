import React, { useEffect } from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { FieldGrid, Segmented } from "./ui";
import { t } from "../../i18n";

// ============================================================================
// API GHG COMPENDIUM (2021) CHAPTER 7 — ONSHORE REFERENCE TABLES & DATA
// ============================================================================

// BUG-110 / RC-17: Tier 1 facility-level factors are API Compendium 2021 Table 7-8 — per unit of
// PRODUCTION (the server's calculations/fugitive_onshore.py TABLE_7_8), not per facility-day.
// Factors in tonnes CH4 per unit; gas factors are on a 78.8 mol % CH4 basis.
const TIER1_FACILITIES = [
  {
    id: "oil_production",
    label: t("Onshore Oil Production"),
    sub: t("0.5173 lb CH₄ per bbl oil produced"),
    units: [
      { value: "bbl", label: t("bbl oil"), t_per_unit: 2.346e-4 },
      { value: "m3", label: t("m³ oil"), t_per_unit: 1.476e-3 },
    ],
  },
  {
    id: "gas_production",
    label: t("Onshore Gas Production"),
    sub: t("57.33 lb CH₄ per 10⁶ scf gas produced"),
    units: [
      { value: "MMscf", label: t("MMscf gas"), t_per_unit: 2.601e-2 },
      { value: "Mcf", label: t("Mcf gas"), t_per_unit: 2.601e-5 },
      { value: "scf", label: t("scf gas"), t_per_unit: 2.601e-8 },
      { value: "m3", label: t("m³ gas"), t_per_unit: 9.184e-7 },
    ],
  },
];

// RC-17 / BUG-110: equipment-level factors are the server catalog entries (API Compendium 2021
// Table 7-9 crude, Table 7-10 gas; verified against the Compendium text). `fuel` is the catalog key
// the server applies, so the preview and the saved record use the same factor. CH4 only.
const TIER2A_EQUIPMENT_DATA: Record<string, { label: string; default_stream: { ch4: number; co2: number }; equipment: Array<{ id: string; label: string; fuel: string; factor: number; unit: string }> }> = {
  gas_production: {
    label: t("Onshore Natural Gas Production"),
    default_stream: { ch4: 78.8, co2: 0 },
    equipment: [
      { id: "wellhead", label: t("Gas Wellhead"), fuel: "Wellhead - Gas", factor: 0.018, unit: "kg CH₄/hr/well" },
      { id: "separator", label: t("Separator"), fuel: "Separator - Gas Production", factor: 0.0442, unit: "kg CH₄/hr/separator" },
      { id: "heater", label: t("Gas Heater"), fuel: "Heater - Gas Production", factor: 0.046, unit: "kg CH₄/hr/heater" },
      { id: "dehydrator", label: t("Dehydrator"), fuel: "Gas Dehydrator Unit - Fugitive Leaks", factor: 0.0713, unit: "kg CH₄/hr/dehydrator" },
      { id: "meter", label: t("Meter / Piping"), fuel: "Meter / Piping Run - Gas Production", factor: 0.0352, unit: "kg CH₄/hr/meter" },
      { id: "compressor_small", label: t("Small Reciprocating Compressor"), fuel: "Compressor - Gas Production Small Recip", factor: 0.212, unit: "kg CH₄/hr/compressor" },
      { id: "compressor_large", label: t("Large Reciprocating Compressor"), fuel: "Compressor - Gas Production Large Recip", factor: 12.2, unit: "kg CH₄/hr/compressor" },
    ],
  },
  oil_production: {
    label: t("Onshore Crude Oil Production"),
    default_stream: { ch4: 78.8, co2: 0 },
    equipment: [
      { id: "wellhead_light", label: t("Wellhead - light crude"), fuel: "Wellhead - Oil (Light Crude)", factor: 0.0156, unit: "kg CH₄/hr/well" },
      { id: "wellhead_heavy", label: t("Wellhead - heavy crude"), fuel: "Wellhead - Oil (Heavy Crude)", factor: 0.000663, unit: "kg CH₄/hr/well" },
      { id: "separator_light", label: t("Separator - light crude"), fuel: "Separator - Light Crude", factor: 0.041, unit: "kg CH₄/hr/separator" },
      { id: "separator_heavy", label: t("Separator - heavy crude"), fuel: "Separator - Heavy Crude", factor: 0.000679, unit: "kg CH₄/hr/separator" },
      { id: "heater_light", label: t("Heater-treater - light crude"), fuel: "Heater-Treater - Light Crude", factor: 0.0477, unit: "kg CH₄/hr/heater" },
      { id: "header_light", label: t("Header - light crude"), fuel: "Header - Light Crude", factor: 0.162, unit: "kg CH₄/hr/header" },
      { id: "header_heavy", label: t("Header - heavy crude"), fuel: "Header - Heavy Crude", factor: 0.000472, unit: "kg CH₄/hr/header" },
      { id: "tank_light", label: t("Tank - light crude"), fuel: "Storage Tank Fugitive - Light Crude", factor: 0.0275, unit: "kg CH₄/hr/tank" },
      { id: "compressor_small", label: t("Small compressor - light crude"), fuel: "Compressor - Small Reciprocating", factor: 0.0369, unit: "kg CH₄/hr/compressor" },
      { id: "compressor_large", label: t("Large compressor - light crude"), fuel: "Compressor - Large Reciprocating", factor: 13.1, unit: "kg CH₄/hr/compressor" },
    ],
  },
};

// Tier 2B components / services of API Compendium Table 7-12 (factors on the server)
const T2B_SERVICES = [
  { value: "gas", label: t("Gas") },
  { value: "light_oil", label: t("Light oil") },
  { value: "heavy_oil", label: t("Heavy oil") },
  { value: "water_oil", label: t("Water / oil") },
];
const T2B_COMPONENTS = [
  { value: "valve", label: t("Valves") },
  { value: "connector", label: t("Connectors") },
  { value: "flange", label: t("Flanges") },
  { value: "open_ended_line", label: t("Open-ended lines") },
  { value: "pump_seal", label: t("Pump seals") },
  { value: "other", label: t("Other components") },
];

const TIER3_METHODS = [
  { id: "method21", label: t("Screening Ranges") },
  { id: "correlation", label: t("Leak-Rate Correlation") },
  { id: "ogi", label: t("Leaker Survey (OGI)") },
  { id: "measurement", label: t("Direct Measurement") },
];
// fields each Tier 3 method writes; switching method clears the others (Tier 3 test #20)
const TIER3_FIELDS = [
  "m21_component", "m21_service", "m21_below_count", "m21_above_count", "ch4_wt_fraction",
  "correlation_type", "corr_zero_count", "corr_screened_count", "screening_ppm", "fugitive_ppm",
  "corr_pegged_10k_count", "corr_pegged_100k_count", "ogi_component", "ogi_service", "leakers_count",
  "measured_rate", "rate_unit", "ch4_content", "co2_content", "operating_hours", "amount", "unit",
];
const M21_COMPONENTS = [
  { value: "valve", label: t("Valves") },
  { value: "pump_seal", label: t("Pump seals") },
  { value: "connector", label: t("Connectors") },
  { value: "flange", label: t("Flanges") },
  { value: "open_ended_line", label: t("Open-ended lines") },
  { value: "other", label: t("Other components") },
];
const M21_SERVICES = [
  { value: "gas", label: t("Gas"), ch4: "92.0" },
  { value: "light_oil", label: t("Light oil"), ch4: "61.3" },
  { value: "heavy_oil", label: t("Heavy oil"), ch4: "94.2" },
  { value: "water_oil", label: t("Water / oil"), ch4: "" },
];
const OGI_COMPONENTS = [
  { value: "valve", label: t("Valves") },
  { value: "flange", label: t("Flanges") },
  { value: "connector", label: t("Connectors") },
  { value: "open_ended_line", label: t("Open-ended lines") },
  { value: "prv", label: t("Pressure relief valves") },
  { value: "pump_seal", label: t("Pump seals") },
  { value: "other", label: t("Other components") },
];
const OGI_SERVICES = [
  { value: "gas", label: t("Gas") },
  { value: "light_crude", label: t("Light crude") },
  { value: "heavy_crude", label: t("Heavy crude") },
];
const RATE_UNITS = [
  { value: "scf/hr", label: t("scf/h (whole gas)") },
  { value: "m3/hr", label: t("m³/h (whole gas)") },
  { value: "kg/hr", label: t("kg CH₄/h") },
  { value: "lb/hr", label: t("lb CH₄/h") },
];

interface NumProps {
  label: React.ReactNode;
  field: string;
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  placeholder?: string;
}

const Num: React.FC<NumProps> = ({ label, field, data, onChange, placeholder }) => (
  <Field className="input-group" label={<>{label}</>}>
    <Input
      type="number"
      min="0"
      step="any"
      value={data[field] ?? ""}
      onChange={(e) => onChange(field, e.target.value)}
      placeholder={placeholder}
    />
  </Field>
);

interface PickProps {
  label: React.ReactNode;
  field: string;
  options: Array<{ value: string; label: string; [key: string]: any }>;
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

const Pick: React.FC<PickProps> = ({ label, field, options, data, onChange }) => (
  <div className="input-group">
    <label>{label}</label>
    <CustomDropdown
      options={options.map(({ value, label: l }) => ({ value, label: l }))}
      value={data[field] || ""}
      onChange={(v) => onChange(field, v)}
      placeholder={t("Select")}
    />
  </div>
);

export interface FugitivesFormProps {
  data?: Record<string, any>;
  onChange: (field: string, val: any) => void;
  sourceType?: string;
}

// ============================================================================
// MAIN COMPONENT: FugitivesForm
// ============================================================================

export const FugitivesForm: React.FC<FugitivesFormProps> = ({
  data = {},
  onChange,
  sourceType = "default",
}) => {
  // One tier selector: the page-level Calculation Methodology control (sourceType) drives the tier;
  // data.fugitive_tier is kept in sync for the payload
  const activeTier = sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1";
  useEffect(() => {
    if (data.fugitive_tier !== activeTier) onChange("fugitive_tier", activeTier);
    if (activeTier === "tier3" && !["method21", "correlation", "ogi", "measurement"].includes(data.fugitive_method))
      onChange("fugitive_method", "ogi");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTier, data.fugitive_method]);

  // Sub-Method within Tier
  // Tier 2: equipment vs component
  const tier2SubMethod = data.fugitive_method === "equipment" ? "equipment" : "component";
  // Tier 3: method21, correlation, ogi, measurement
  const tier3Method =
    data.fugitive_method && ["method21", "correlation", "ogi", "measurement"].includes(data.fugitive_method)
      ? data.fugitive_method
      : "ogi";

  // Tier 1 State
  const selectedFacilityId = TIER1_FACILITIES.some((f) => f.id === data.facility_type)
    ? data.facility_type
    : TIER1_FACILITIES[1].id;
  const tier1Fac = TIER1_FACILITIES.find((f) => f.id === selectedFacilityId)!;
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

  useEffect(() => {
    if (activeTier !== "tier2" || tier2SubMethod !== "equipment") return;
    const eqSel = TIER2A_EQUIPMENT_DATA[tier2aSegment].equipment.find((e) => e.id === tier2aEquipId);
    if (eqSel && data.fuel !== eqSel.fuel) onChange("fuel", eqSel.fuel);
    if (data.equipment_type !== tier2aEquipId) onChange("equipment_type", tier2aEquipId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTier, tier2SubMethod, tier2aSegment, tier2aEquipId, data.fuel]);

  return (
    <div className="fugitives-form-v2 [font-family:inherit]!">
      {/* TIER 1 INPUTS: FACILITY-LEVEL (TABLES 7-1, 7-2) */}
      {activeTier === "tier1" && (
        <div className="[margin-bottom:12px]">
          <div className="grid gap-[12px] [grid-template-columns:2fr_1fr_1.5fr] max-[600px]:[grid-template-columns:1fr]">
            <div className="input-group">
              <label>{t("Facility Type")}</label>
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

            <Field className="input-group" label={t("Production Volume")}>
              <Input
                type="number"
                min="0"
                step="any"
                value={data.amount ?? ""}
                onChange={(e) => onChange("amount", e.target.value)}
                placeholder="e.g. 120000"
              />
            </Field>

            <div className="input-group">
              <label>{t("Production Unit")}</label>
              <CustomDropdown
                options={tier1Fac.units.map((u) => ({ value: u.value, label: u.label }))}
                value={tier1Unit}
                onChange={(val) => onChange("unit", val)}
              />
            </div>
          </div>
        </div>
      )}

      {/* TIER 2 INPUTS: EQUIPMENT OR COMPONENT POPULATION */}
      {activeTier === "tier2" && (
        <div className="[margin-bottom:12px]">
          <div className="mb-[16px]!">
            <Segmented
              ariaLabel={t("Tier 2 method")}
              value={tier2SubMethod}
              onChange={(v) => {
                if (v === tier2SubMethod) return;
                [
                  "equipment_count",
                  "component_count",
                  "component_type",
                  "service_type",
                  "ch4_mole_pct",
                  "co2_mole_pct",
                  "operating_hours",
                  "amount",
                  "unit",
                ].forEach((k) => onChange(k, undefined));
                onChange("fugitive_method", v);
              }}
              options={[
                { value: "equipment", label: t("Equipment count") },
                { value: "component", label: t("Component count") },
              ]}
            />
          </div>

          {/* Tier 2A: Equipment Count Form */}
          {tier2SubMethod === "equipment" && (
            <div className="grid gap-[12px] [grid-template-columns:1.2fr_1.2fr_0.8fr_1.2fr] max-[600px]:[grid-template-columns:1fr]">
              <div className="input-group">
                <label>{t("Industry Segment / Table")}</label>
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
                <label>{t("Equipment Type")}</label>
                <CustomDropdown
                  options={
                    TIER2A_EQUIPMENT_DATA[tier2aSegment]?.equipment.map((e) => ({
                      value: e.id,
                      label: e.label,
                    })) || []
                  }
                  value={tier2aEquipId}
                  onChange={(val) => onChange("equipment_type", val)}
                />
              </div>

              <Num
                label={t("Equipment count")}
                field="equipment_count"
                data={data}
                onChange={(k, v) => {
                  onChange(k, v);
                  onChange("amount", v);
                  onChange("unit", "equipment");
                }}
                placeholder="e.g. 4"
              />
              <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} placeholder={t("whole month")} />
            </div>
          )}

          {/* Tier 2B: component count x Table 7-12 */}
          {tier2SubMethod === "component" && (
            <FieldGrid min={160}>
              <Pick label={t("Component")} field="component_type" options={T2B_COMPONENTS} data={data} onChange={onChange} />
              <Pick label={t("Service")} field="service_type" options={T2B_SERVICES} data={data} onChange={onChange} />
              <Num
                label={t("Component count")}
                field="component_count"
                data={data}
                onChange={(k, v) => {
                  onChange(k, v);
                  onChange("amount", v);
                  onChange("unit", "components");
                }}
                placeholder="e.g. 100"
              />
              <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} placeholder={t("whole month")} />
              <Num label={t("CH₄ (mol %)")} field="ch4_mole_pct" data={data} onChange={onChange} placeholder={t("81.6 (table basis)")} />
              <Num label={t("CO₂ (mol %)")} field="co2_mole_pct" data={data} onChange={onChange} placeholder="0" />
            </FieldGrid>
          )}
        </div>
      )}

      {/* TIER 3 INPUTS: DETECTION & MEASUREMENT */}
      {activeTier === "tier3" && (
        <div className="[margin-bottom:12px]">
          <div className="mb-[16px]!">
            <Segmented
              ariaLabel={t("Tier 3 method")}
              value={tier3Method}
              onChange={(v) => {
                if (v === tier3Method) return;
                TIER3_FIELDS.forEach((k) => onChange(k, undefined));
                onChange("fugitive_method", v);
              }}
              options={TIER3_METHODS.map((m) => ({ value: m.id, label: m.label }))}
            />
          </div>

          {tier3Method === "method21" && (
            <FieldGrid min={170}>
              <Pick label={t("Component")} field="m21_component" options={M21_COMPONENTS} data={data} onChange={onChange} />
              <Pick label={t("Service")} field="m21_service" options={M21_SERVICES} data={data} onChange={onChange} />
              <Num label={t("Count < 10,000 ppmv")} field="m21_below_count" data={data} onChange={onChange} placeholder="0" />
              <Num label={t("Count ≥ 10,000 ppmv")} field="m21_above_count" data={data} onChange={onChange} placeholder="0" />
              <Num
                label={t("CH₄ in TOC (wt %)")}
                field="ch4_wt_fraction"
                data={data}
                onChange={onChange}
                placeholder={(M21_SERVICES.find((x) => x.value === data.m21_service) || {}).ch4 || t("required")}
              />
              <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} placeholder={t("whole month")} />
            </FieldGrid>
          )}

          {tier3Method === "correlation" && (
            <FieldGrid min={160}>
              <Pick label={t("Component")} field="correlation_type" options={M21_COMPONENTS} data={data} onChange={onChange} />
              <Num label={t("Non-detect count")} field="corr_zero_count" data={data} onChange={onChange} placeholder="0" />
              <Num label={t("Screened count")} field="corr_screened_count" data={data} onChange={onChange} placeholder="0" />
              <Num
                label={t("Screening value (ppmv)")}
                field="screening_ppm"
                data={data}
                onChange={(k, v) => {
                  onChange(k, v);
                  onChange("fugitive_ppm", v);
                }}
                placeholder="e.g. 2500"
              />
              <Num label={t("Pegged ≥ 10,000 ppmv")} field="corr_pegged_10k_count" data={data} onChange={onChange} placeholder="0" />
              <Num label={t("Pegged ≥ 100,000 ppmv")} field="corr_pegged_100k_count" data={data} onChange={onChange} placeholder="0" />
              <Num label={t("CH₄ in TOC (wt %)")} field="ch4_wt_fraction" data={data} onChange={onChange} placeholder="56.4" />
              <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} placeholder={t("whole month")} />
            </FieldGrid>
          )}

          {tier3Method === "ogi" && (
            <FieldGrid min={170}>
              <Pick label={t("Component")} field="ogi_component" options={OGI_COMPONENTS} data={data} onChange={onChange} />
              <Pick label={t("Service")} field="ogi_service" options={OGI_SERVICES} data={data} onChange={onChange} />
              <Num label={t("Leakers found")} field="leakers_count" data={data} onChange={onChange} placeholder="e.g. 2" />
              <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} placeholder={t("whole month")} />
              <Num label={t("CH₄ (mol %)")} field="ch4_content" data={data} onChange={onChange} placeholder="81.6" />
              <Num label={t("CO₂ (mol %)")} field="co2_content" data={data} onChange={onChange} placeholder="0" />
            </FieldGrid>
          )}

          {tier3Method === "measurement" && (
            <FieldGrid min={170}>
              <Num label={t("Measured leak rate")} field="measured_rate" data={data} onChange={onChange} placeholder="e.g. 0.5" />
              <Pick label={t("Rate unit")} field="rate_unit" options={RATE_UNITS} data={data} onChange={onChange} />
              <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} placeholder={t("whole month")} />
              <Num label={t("CH₄ (mol %)")} field="ch4_content" data={data} onChange={onChange} placeholder="e.g. 78.8" />
              <Num label={t("CO₂ (mol %)")} field="co2_content" data={data} onChange={onChange} placeholder="0" />
            </FieldGrid>
          )}
        </div>
      )}
    </div>
  );
};

export default FugitivesForm;
