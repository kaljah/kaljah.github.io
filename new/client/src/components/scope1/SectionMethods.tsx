// API Compendium methods that are not "activity x catalog factor": activity-factor tables
// (Section 6), measured / engineered gas volumes, and combustion / waste-gas methods
// (Sections 4 and 5). The server routes on activity_key, vent_method and combustion_method.
import React, { useEffect, useState } from "react";
import { Wind, Droplets, Layers, Info } from "lucide-react";
import { Input, Field } from "../../ui";
import api from "../../api";
import CustomDropdown from "../CustomDropdown";
import { FieldGrid, MoreOptions, Segmented } from "./ui";
import { applyChoice, currentChoice, sectionChoices } from "./methodChoices";
import { t } from "../../i18n";

interface NumProps {
  label: React.ReactNode;
  field: string;
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  placeholder?: string;
  required?: boolean;
}

const Num: React.FC<NumProps> = ({ label, field, data, onChange, placeholder, required }) => (
  <Field
    className="input-group"
    label={
      <>
        {label}
        {required && <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>}
      </>
    }
  >
    <Input
      type="number"
      min="0"
      step="any"
      value={data[field] ?? ""}
      onChange={(e) => onChange(field, e.target.value)}
      placeholder={placeholder}
      required={required}
    />
  </Field>
);

interface NumUnitProps {
  label: React.ReactNode;
  field: string;
  unitField: string;
  units: string[];
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  placeholder?: string;
  required?: boolean;
}

const NumUnit: React.FC<NumUnitProps> = ({
  label,
  field,
  unitField,
  units,
  data,
  onChange,
  placeholder,
  required,
}) => (
  <div className="input-group">
    <label>
      {label}
      {required && <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>}
    </label>
    <div className="grid gap-[8px] [grid-template-columns:1fr_110px] max-[600px]:[grid-template-columns:1fr]">
      <Input
        type="number"
        min="0"
        step="any"
        value={data[field] ?? ""}
        onChange={(e) => {
          onChange(field, e.target.value);
          // the unit shown by default must also be sent
          if (!data[unitField]) onChange(unitField, units[0]);
        }}
        placeholder={placeholder}
        required={required}
      />
      <CustomDropdown
        options={units.map((u) => ({ value: u, label: u }))}
        value={data[unitField] || units[0]}
        onChange={(v) => onChange(unitField, v)}
      />
    </div>
  </div>
);

const GAS_UNITS = ["scf", "Mcf", "MMscf", "m3"];
const LIQ_UNITS = ["bbl", "gal", "m3", "L"];

const GAS_FUELS = ["Fuel Gas", "Natural Gas", "Associated Gas", "Refinery Gas", "Custom Gas"];
const LIQUID_FUELS = ["Diesel (No. 2 Fuel Oil)", "Crude Oil", "Motor Gasoline", "Kerosene / Jet Fuel", "Residual Fuel Oil (No. 6)", "LPG", "Custom Liquid Fuel"];
const SOLID_FUELS = ["Bituminous Coal", "Sub-bituminous Coal", "Anthracite Coal", "Lignite", "Petroleum Coke", "Wood / Biomass", "Custom Solid Fuel"];

interface CompositionProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  c2?: boolean;
  required?: boolean;
}

const Composition: React.FC<CompositionProps> = ({ data, onChange, c2 = false, required = true }) => (
  <FieldGrid min={160}>
    <Num label={t("CH₄ (mol %)")} field="ch4_content" data={data} onChange={onChange} placeholder="e.g. 70" required={required} />
    <Num label={t("CO₂ (mol %)")} field="co2_content" data={data} onChange={onChange} placeholder="e.g. 9" />
    {c2 && <Num label={t("C₂+ (mol %)")} field="c2plus_content" data={data} onChange={onChange} placeholder="e.g. 4" />}
  </FieldGrid>
);

// ---- Tier 1: activity-factor tables ----
const plural = (a?: string) => (a && !a.endsWith("s") ? `${a}s` : a);
const PER_INPUT: Record<string, { label: (a?: string) => string; units?: string[]; extra?: { field: string; label: string; placeholder: string } }> = {
  unit: { label: (a) => t("Number ({{unit}})", { unit: a || t("events") }) },
  unit_day: { label: (a) => t("Number of {{items}}", { items: plural(a) || t("units") }), extra: { field: "activity_days", label: t("Days"), placeholder: t("whole month") } },
  unit_hr: { label: (a) => t("Number of {{items}}", { items: plural(a) || t("units") }), extra: { field: "activity_hours", label: t("Hours"), placeholder: t("whole month") } },
  mmscf: { label: () => t("Gas throughput"), units: GAS_UNITS },
  mm_m3: { label: () => t("Gas throughput"), units: GAS_UNITS },
  mgal: { label: () => t("Liquid loaded"), units: LIQ_UNITS },
  bbl: { label: (a) => (a && a !== "bbl oil" ? t("Volume ({{unit}})", { unit: a.replace("bbl ", "") }) : t("Oil produced")), units: LIQ_UNITS },
};

export interface ActivityFactorFormProps {
  processType: string;
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

export const ActivityFactorForm: React.FC<ActivityFactorFormProps> = ({ processType, data, onChange }) => {
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    api
      .get("/activity-factors", { params: { process: processType } })
      .then((r) => live && setRows(r.data?.factors || []))
      .catch(() => live && setError(t("Could not load the factor list")));
    return () => {
      live = false;
    };
  }, [processType]);

  const row = rows.find((r) => r.key === data.activity_key);
  const spec = row ? PER_INPUT[row.per] : null;

  const pick = (key: string) => {
    onChange("activity_key", key);
    const r = rows.find((x) => x.key === key);
    const p = r && PER_INPUT[r.per];
    onChange("unit", p?.units ? p.units[0] : "count");
  };

  return (
    <div className="[display:grid] [grid-template-columns:1fr] [gap:16px]">
      <div className="input-group">
        <label>
          {t("Source")}<span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
        </label>
        <CustomDropdown
          options={rows.map((r) => ({ value: r.key, label: r.label }))}
          value={data.activity_key || ""}
          onChange={pick}
          placeholder={error || t("Select source")}
        />
      </div>
      {spec && (
        <FieldGrid min={180}>
          {spec.units ? (
            <NumUnit label={spec.label(row?.activity)} field="amount" unitField="unit" units={spec.units} data={data} onChange={onChange} required />
          ) : (
            <Num label={spec.label(row?.activity)} field="amount" data={data} onChange={onChange} required />
          )}
          {spec.extra && (
            <Num label={spec.extra.label} field={spec.extra.field} data={data} onChange={onChange} placeholder={spec.extra.placeholder} />
          )}
        </FieldGrid>
      )}
      {row &&
        (row.toc ? (
          <FieldGrid min={180}>
            <Num label={t("CH₄ in vapour (wt %)")} field="toc_ch4_wt" data={data} onChange={onChange} placeholder="15" />
          </FieldGrid>
        ) : (
          <MoreOptions label={t("Site gas composition")}>
            <Composition data={data} onChange={onChange} required={false} />
          </MoreOptions>
        ))}
    </div>
  );
};

export interface VentedGasFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

// ---- measured / engineered gas volumes ----
export const VentedGasForm: React.FC<VentedGasFormProps> = ({ data, onChange }) => {
  const m = data.vent_method;
  const flared = data.disposition === "flared";
  const canFlare = ["volume", "gor", "rate_days", "actual"].includes(m);
  const noComposition = ["co2_mass", "agr_balance", "thc_mass", "reported_mass"].includes(m);

  return (
    <div className="[display:grid] [grid-template-columns:1fr] [gap:16px]">
      {m === "volume" && (
        <FieldGrid>
          <NumUnit label={t("Gas volume")} field="gas_volume" unitField="gas_volume_unit" units={GAS_UNITS} data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "gor" && (
        <FieldGrid min={160}>
          <Num label={t("GOR (scf/bbl)")} field="gor" data={data} onChange={onChange} required />
          <Num label={t("Oil rate (bbl/day)")} field="oil_rate" data={data} onChange={onChange} required />
          <Num label={t("Vent duration (hours)")} field="vent_hours" data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "rate_days" && (
        <FieldGrid min={180}>
          <NumUnit label={t("Gas rate")} field="gas_rate" unitField="gas_rate_unit" units={["scf/day", "Mcf/day", "MMscf/day", "m3/day"]} data={data} onChange={onChange} required />
          <Num label={t("Days")} field="days" data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "actual" && (
        <FieldGrid min={160}>
          <NumUnit label={t("Actual gas volume")} field="actual_volume" unitField="actual_unit" units={["ft3", "bbl", "gal", "m3"]} data={data} onChange={onChange} required />
          <Num label={t("Temperature (°F)")} field="gas_temp_f" data={data} onChange={onChange} placeholder={t("required")} />
          <Num label={t("Pressure (atm)")} field="gas_pressure_atm" data={data} onChange={onChange} placeholder={t("required")} />
        </FieldGrid>
      )}
      {m === "desiccant" && (
        <FieldGrid min={160}>
          <Num label={t("Vessel height (ft)")} field="vessel_height_ft" data={data} onChange={onChange} required />
          <Num label={t("Vessel diameter (ft)")} field="vessel_diameter_ft" data={data} onChange={onChange} required />
          <Num label={t("Gas pressure (psig)")} field="vessel_pressure_psig" data={data} onChange={onChange} required />
          <Num label={t("Refills per year")} field="refills" data={data} onChange={onChange} required />
          <Num label={t("Gas-filled share (%)")} field="gas_fraction" data={data} onChange={onChange} placeholder={t("required")} />
        </FieldGrid>
      )}
      {m === "co2_mass" && (
        <FieldGrid min={160}>
          <Num label={t("Volume released (m³)")} field="physical_volume_m3" data={data} onChange={onChange} required />
          <Num label={t("CO₂ density (kg/m³)")} field="co2_density" data={data} onChange={onChange} required />
          <Num label={t("CO₂ (wt %)")} field="co2_wt_pct" data={data} onChange={onChange} placeholder={t("required")} />
          <Num label={t("Events")} field="events" data={data} onChange={onChange} placeholder="1" />
        </FieldGrid>
      )}
      {m === "agr_balance" && (
        <FieldGrid min={160}>
          <NumUnit label={t("Sour gas in")} field="sour_gas_volume" unitField="gas_volume_unit" units={GAS_UNITS} data={data} onChange={onChange} required />
          <Num label={t("Sour gas CO₂ (mol %)")} field="sour_co2_content" data={data} onChange={onChange} required />
          <Num label={t("Sweet gas out (same unit)")} field="sweet_gas_volume" data={data} onChange={onChange} required />
          <Num label={t("Sweet gas CO₂ (mol %)")} field="sweet_co2_content" data={data} onChange={onChange} placeholder="0" />
        </FieldGrid>
      )}
      {m === "thc_mass" && (
        <FieldGrid min={170}>
          <NumUnit label={t("Total hydrocarbon loss")} field="thc_loss" unitField="thc_loss_unit" units={["t", "kg", "lb"]} data={data} onChange={onChange} required />
          <Num label={t("CH₄ in vent (wt %)")} field="ch4_wt_pct" data={data} onChange={onChange} required />
          <Num label={t("CO₂ in vent (wt %)")} field="co2_wt_pct" data={data} onChange={onChange} placeholder="0" />
        </FieldGrid>
      )}
      {m === "reported_mass" && (
        <FieldGrid min={170}>
          <NumUnit label={t("CH₄ before control")} field="ch4_mass" unitField="mass_unit" units={["t", "kg", "lb"]} data={data} onChange={onChange} required />
          <Num label={t("CO₂ before control (same unit)")} field="co2_mass" data={data} onChange={onChange} placeholder="0" />
          <Num label={t("Control efficiency (%)")} field="control_efficiency" data={data} onChange={onChange} placeholder="0" />
        </FieldGrid>
      )}
      {!noComposition && <Composition data={data} onChange={onChange} c2={flared} />}
      {canFlare && (
        <FieldGrid min={180}>
          <div className="input-group">
            <label>{t("Gas released")}</label>
            <Segmented
              ariaLabel={t("Gas released")}
              options={[
                { value: "vented", label: t("Vented") },
                { value: "flared", label: t("Flared") },
              ]}
              value={flared ? "flared" : "vented"}
              onChange={(v) => onChange("disposition", v)}
            />
          </div>
          {flared && <Num label={t("Combustion efficiency (%)")} field="combustion_efficiency" data={data} onChange={onChange} placeholder="98" />}
        </FieldGrid>
      )}
    </div>
  );
};

export interface CombustionMethodFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

// ---- combustion and waste-gas methods ----
export const CombustionMethodForm: React.FC<CombustionMethodFormProps> = ({ data, onChange }) => {
  const m = data.combustion_method;
  const [equip, setEquip] = useState<any[]>([]);

  useEffect(() => {
    if (m !== "equipment") return undefined;
    let live = true;
    api
      .get("/equipment-combustion-factors")
      .then((r) => live && setEquip(r.data?.factors || []))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [m]);

  const eqRow = equip.find((e) => e.key === data.equipment_type);
  const energyBy = data.energy_basis || "fuel";

  const fuelState = data.fuel_state || (data.fuel_mass || data.fuel_mass_unit ? "solid" : (data.fuel_volume_unit && ["m3", "scf", "mcf", "mmscf", "nm3", "sm3"].includes(String(data.fuel_volume_unit).toLowerCase()) ? "gas" : "gas"));

  return (
    <div className="[display:grid] [grid-template-columns:1fr] [gap:16px]">
      {m === "carbon_content" && (
        <div className="[display:grid] [grid-template-columns:1fr] [gap:14px]">
          {/* Fuel Physical Form Selector (Gas, Liquid, Solid) */}
          <div className="input-group mb-0!">
            <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1.5">
              {t("Fuel Physical Form")}
            </label>
            <Segmented
              ariaLabel={t("Fuel Physical Form")}
              options={[
                {
                  value: "gas",
                  label: (
                    <span className="inline-flex items-center gap-1.5">
                      <Wind size={13} className="shrink-0 text-sky-600 dark:text-sky-400" aria-hidden="true" />
                      <span>{t("Gas (Natural / Fuel Gas)")}</span>
                    </span>
                  ),
                },
                {
                  value: "liquid",
                  label: (
                    <span className="inline-flex items-center gap-1.5">
                      <Droplets size={13} className="shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
                      <span>{t("Liquid (Diesel / Oil / LPG)")}</span>
                    </span>
                  ),
                },
                {
                  value: "solid",
                  label: (
                    <span className="inline-flex items-center gap-1.5">
                      <Layers size={13} className="shrink-0 text-slate-600 dark:text-slate-400" aria-hidden="true" />
                      <span>{t("Solid (Coal / Coke / Biomass)")}</span>
                    </span>
                  ),
                },
              ]}
              value={fuelState}
              onChange={(val) => {
                onChange("fuel_state", val);
                if (val === "gas") {
                  onChange("fuel_mass", undefined);
                  onChange("fuel_mass_unit", undefined);
                  const defaultName = data.fuel && GAS_FUELS.includes(data.fuel) ? data.fuel : "Fuel Gas";
                  onChange("fuel", defaultName);
                  onChange("fuel_name", defaultName);
                  onChange("fuel_type", defaultName);
                  onChange("fuel_volume_unit", "m3");
                  onChange("unit", "m3");
                  onChange("density_unit", "kg/m3");
                } else if (val === "liquid") {
                  onChange("fuel_mass", undefined);
                  onChange("fuel_mass_unit", undefined);
                  const defaultName = data.fuel && LIQUID_FUELS.includes(data.fuel) ? data.fuel : "Diesel (No. 2 Fuel Oil)";
                  onChange("fuel", defaultName);
                  onChange("fuel_name", defaultName);
                  onChange("fuel_type", defaultName);
                  onChange("fuel_volume_unit", "gal");
                  onChange("unit", "gal");
                  onChange("density_unit", "lb/gal");
                } else if (val === "solid") {
                  onChange("fuel_volume", undefined);
                  onChange("fuel_volume_unit", undefined);
                  onChange("fuel_density", undefined);
                  onChange("density_unit", undefined);
                  const defaultName = data.fuel && SOLID_FUELS.includes(data.fuel) ? data.fuel : "Bituminous Coal";
                  onChange("fuel", defaultName);
                  onChange("fuel_name", defaultName);
                  onChange("fuel_type", defaultName);
                  onChange("fuel_mass_unit", "tonne");
                  onChange("unit", "tonne");
                }
              }}
            />
          </div>

          {/* Fuel Name / Type */}
          <div className="input-group mb-0!">
            <label className="block text-sm font-medium text-text mb-1.5">
              {t("Fuel / Activity Name")}
              <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
            </label>
            <CustomDropdown
              options={
                (fuelState === "solid" ? SOLID_FUELS : fuelState === "liquid" ? LIQUID_FUELS : GAS_FUELS).map((f) => ({
                  value: f,
                  label: f,
                }))
              }
              value={data.fuel || (fuelState === "solid" ? "Bituminous Coal" : fuelState === "liquid" ? "Diesel (No. 2 Fuel Oil)" : "Fuel Gas")}
              onChange={(v) => {
                onChange("fuel", v);
                onChange("fuel_name", v);
                onChange("fuel_type", v);
              }}
            />
          </div>

          {/* Form fields tailored to physical form */}
          {fuelState === "gas" && (
            <FieldGrid min={170}>
              <NumUnit
                label={t("Gas volume burned")}
                field="fuel_volume"
                unitField="fuel_volume_unit"
                units={["m3", "scf", "Mcf", "MMscf", "Nm3", "Sm3"]}
                data={data}
                onChange={(f, v) => {
                  onChange(f, v);
                  if (f === "fuel_volume") {
                    onChange("amount", v);
                    onChange("quantity", v);
                  }
                  if (f === "fuel_volume_unit") {
                    onChange("unit", v);
                  }
                }}
                placeholder="e.g. 24359006.31"
                required
              />
              <NumUnit
                label={t("Gas density")}
                field="fuel_density"
                unitField="density_unit"
                units={["kg/m3", "lb/scf", "g/L"]}
                data={data}
                onChange={onChange}
                placeholder="e.g. 1.0253"
                required
              />
              <Num
                label={t("Carbon content (wt % or fraction)")}
                field="carbon_wt_pct"
                data={data}
                onChange={onChange}
                placeholder="e.g. 77.1% or 0.771"
                required
              />
              <Num
                label={t("Oxidation factor (%)")}
                field="oxidation_pct"
                data={data}
                onChange={onChange}
                placeholder="Default: 100%"
              />
            </FieldGrid>
          )}

          {fuelState === "liquid" && (
            <FieldGrid min={170}>
              <NumUnit
                label={t("Liquid volume burned")}
                field="fuel_volume"
                unitField="fuel_volume_unit"
                units={["gal", "bbl", "m3", "L"]}
                data={data}
                onChange={(f, v) => {
                  onChange(f, v);
                  if (f === "fuel_volume") {
                    onChange("amount", v);
                    onChange("quantity", v);
                  }
                  if (f === "fuel_volume_unit") {
                    onChange("unit", v);
                  }
                }}
                placeholder="e.g. 10000"
                required
              />
              <NumUnit
                label={t("Liquid density")}
                field="fuel_density"
                unitField="density_unit"
                units={["lb/gal", "kg/m3", "kg/L"]}
                data={data}
                onChange={onChange}
                placeholder="e.g. 7.05 lb/gal or 845 kg/m3"
                required
              />
              <Num
                label={t("Carbon content (wt % or fraction)")}
                field="carbon_wt_pct"
                data={data}
                onChange={onChange}
                placeholder="e.g. 86.5% or 0.865"
                required
              />
              <Num
                label={t("Oxidation factor (%)")}
                field="oxidation_pct"
                data={data}
                onChange={onChange}
                placeholder="Default: 100%"
              />
            </FieldGrid>
          )}

          {fuelState === "solid" && (
            <FieldGrid min={170}>
              <NumUnit
                label={t("Solid mass burned")}
                field="fuel_mass"
                unitField="fuel_mass_unit"
                units={["tonne", "kg", "short_ton", "lb"]}
                data={data}
                onChange={(f, v) => {
                  onChange(f, v);
                  if (f === "fuel_mass") {
                    onChange("amount", v);
                    onChange("quantity", v);
                  }
                  if (f === "fuel_mass_unit") {
                    onChange("unit", v);
                  }
                }}
                placeholder="e.g. 100"
                required
              />
              <Num
                label={t("Carbon content (wt % or fraction)")}
                field="carbon_wt_pct"
                data={data}
                onChange={onChange}
                placeholder="e.g. 75.0% or 0.75"
                required
              />
              <Num
                label={t("Oxidation factor (%)")}
                field="oxidation_pct"
                data={data}
                onChange={onChange}
                placeholder="Default: 100%"
              />
            </FieldGrid>
          )}

          {/* Trace gases option */}
          <div className="flex items-center gap-2 mt-0.5">
            <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(data.include_trace)}
                onChange={(e) => onChange("include_trace", e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary size-3.5"
              />
              <span>{t("Estimate trace CH₄ & N₂O emissions (API Table 4-6 fuel factor basis)")}</span>
            </label>
          </div>

          {/* Informational Guidance Banner */}
          <div className="p-2.5 rounded-md bg-blue-50/70 border border-blue-200 text-xs text-blue-900 flex items-start gap-2">
            <Info size={15} className="text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <span className="font-semibold mr-1">{t("Tier 3 Mass Balance:")}</span>
              <span>
                {fuelState === "gas"
                  ? t("Gas fuel carbon mass balance: CO₂ (t) = Volume (m³) × Density (kg/m³) / 1000 × Carbon wt% × 44.01/12.011 × Oxidation. Original activity volume is preserved.")
                  : fuelState === "liquid"
                  ? t("Liquid fuel carbon mass balance (API Exhibit 4.5): CO₂ (t) = Volume (gal) × Density (lb/gal) / 2204.62 × Carbon wt% × 44.01/12.011 × Oxidation.")
                  : t("Solid fuel carbon mass balance (API §4.1): CO₂ (t) = Mass (t) × Carbon wt% × 44.01/12.011 × Oxidation.")}
              </span>
            </div>
          </div>
        </div>
      )}
      {m === "equipment" && (
        <>
          <div className="input-group">
            <label>
              {t("Equipment")}<span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
            </label>
            <CustomDropdown
              options={equip.map((e) => ({ value: e.key, label: e.label }))}
              value={data.equipment_type || ""}
              onChange={(v) => onChange("equipment_type", v)}
              placeholder={t("Select equipment")}
            />
          </div>
          <Segmented
            ariaLabel={t("Energy input")}
            options={[
              { value: "fuel", label: t("Fuel burned") },
              { value: "engine", label: t("Engine hours") },
              { value: "energy", label: t("Energy (MMBtu)") },
            ]}
            value={energyBy}
            onChange={(v) => {
              ["fuel_volume", "engine_hp", "energy_mmbtu"].forEach((k) => onChange(k, undefined));
              onChange("energy_basis", v);
            }}
          />
          <FieldGrid min={170}>
            {energyBy === "fuel" && (
              <>
                <NumUnit
                  label={t("Fuel burned")}
                  field="fuel_volume"
                  unitField="fuel_volume_unit"
                  units={eqRow && eqRow.fuel !== "natural_gas" ? ["gal", "bbl", "m3", "l"] : ["scf", "Mcf", "MMscf", "m3"]}
                  data={data}
                  onChange={onChange}
                  required
                />
                {!eqRow || eqRow.fuel === "natural_gas" ? (
                  <Num label={t("HHV (Btu/scf)")} field="hhv_btu_scf" data={data} onChange={onChange} placeholder="1026" />
                ) : (
                  <Num label={t("HHV (MMBtu/gal)")} field="hhv_mmbtu_gal" data={data} onChange={onChange} placeholder={eqRow.fuel === "diesel" ? "0.138" : "0.125"} />
                )}
              </>
            )}
            {energyBy === "engine" && (
              <>
                <Num label={t("Rating (hp)")} field="engine_hp" data={data} onChange={onChange} required />
                <Num label={t("Load (%)")} field="load_pct" data={data} onChange={onChange} placeholder="100" />
                <Num label={t("Operating hours")} field="operating_hours" data={data} onChange={onChange} required />
              </>
            )}
            {energyBy === "energy" && <Num label={t("Energy input, HHV (MMBtu)")} field="energy_mmbtu" data={data} onChange={onChange} required />}
          </FieldGrid>
          <MoreOptions>
            <FieldGrid min={170}>
              <Num label={t("CO₂ factor (t/MMBtu)")} field="co2_ef_t_mmbtu" data={data} onChange={onChange} placeholder={t("fuel default")} />
              {energyBy === "engine" && <Num label={t("Heat rate (Btu/hp-hr)")} field="heat_rate_btu_hphr" data={data} onChange={onChange} placeholder="7000" />}
            </FieldGrid>
          </MoreOptions>
        </>
      )}
      {m === "vehicle_distance" && (
        <>
          <FieldGrid min={170}>
            <NumUnit label={t("Distance")} field="distance" unitField="distance_unit" units={["mile", "km"]} data={data} onChange={onChange} required />
            <Num label={t("Fuel economy (miles/gal)")} field="fuel_economy_mpg" data={data} onChange={onChange} required />
            <div className="input-group">
              <label>{t("Vehicle")}</label>
              <CustomDropdown
                options={[
                  { value: "hd_diesel_advanced", label: t("Heavy-duty diesel, advanced control") },
                  { value: "diesel", label: t("Other diesel vehicle") },
                  { value: "gasoline", label: t("Gasoline vehicle") },
                ]}
                value={data.vehicle_type || data.vehicle_fuel || ""}
                onChange={(v) => {
                  if (v === "hd_diesel_advanced") {
                    onChange("vehicle_type", v);
                    onChange("vehicle_fuel", "diesel");
                  } else {
                    onChange("vehicle_type", undefined);
                    onChange("vehicle_fuel", v);
                  }
                }}
                placeholder={t("Select vehicle")}
              />
            </div>
          </FieldGrid>
          <MoreOptions>
            <FieldGrid min={170}>
              <Num label={t("CH₄ (t / 1,000 gal)")} field="ch4_t_per_kgal" data={data} onChange={onChange} placeholder={t("default")} />
              <Num label={t("N₂O (t / 1,000 gal)")} field="n2o_t_per_kgal" data={data} onChange={onChange} placeholder={t("default")} />
              <Num label={t("HHV (MMBtu/gal)")} field="hhv_mmbtu_gal" data={data} onChange={onChange} placeholder={t("fuel default")} />
              <Num label={t("CO₂ factor (t/MMBtu)")} field="co2_ef_t_mmbtu" data={data} onChange={onChange} placeholder={t("fuel default")} />
            </FieldGrid>
          </MoreOptions>
        </>
      )}
      {m === "flare_voc" && (
        <>
          <FieldGrid min={170}>
            <NumUnit label={t("VOC emitted")} field="voc_mass" unitField="voc_mass_unit" units={["t", "kg", "lb", "short_ton"]} data={data} onChange={onChange} required />
            <Num label={t("Combustion efficiency (%)")} field="combustion_efficiency" data={data} onChange={onChange} placeholder="98" />
          </FieldGrid>
          <label className="s1-label">{t("Flare gas analysis (wt %)")}</label>
          <FieldGrid min={120}>
            {[
              ["wt_ch4", "CH₄"],
              ["wt_c2h6", "C₂H₆"],
              ["wt_c3h8", "C₃H₈"],
              ["wt_c4h10", "Butanes"],
              ["wt_c5h12", "Pentanes"],
              ["wt_c6plus", "C₆+"],
              ["wt_co2", "CO₂"],
            ].map(([f, l]) => (
              <Num key={f} label={l} field={f} data={data} onChange={onChange} />
            ))}
          </FieldGrid>
        </>
      )}
      {m === "thermal_oxidizer" && (
        <>
          <Segmented
            ariaLabel={t("Oxidizer feed")}
            options={[
              { value: "loading", label: t("Loading losses") },
              { value: "toc", label: t("TOC mass") },
            ]}
            value={data.oxidizer_feed || "loading"}
            onChange={(v) => {
              ["toc_mass", "liquid_loaded"].forEach((k) => onChange(k, undefined));
              onChange("oxidizer_feed", v);
            }}
          />
          <FieldGrid min={170}>
            {(data.oxidizer_feed || "loading") === "loading" ? (
              <>
                <NumUnit label={t("Liquid loaded")} field="liquid_loaded" unitField="liquid_unit" units={LIQ_UNITS} data={data} onChange={onChange} required />
                <Num label={t("Loading loss (lb VOC / 1,000 gal)")} field="loading_loss_lb_kgal" data={data} onChange={onChange} required />
                <Num label={t("VOC share of TOC (%)")} field="voc_fraction_of_toc" data={data} onChange={onChange} placeholder="85" />
              </>
            ) : (
              <NumUnit label={t("TOC to oxidizer")} field="toc_mass" unitField="toc_mass_unit" units={["t", "kg", "lb"]} data={data} onChange={onChange} required />
            )}
            <Num label={t("TOC carbon (wt %)")} field="toc_carbon_wt_pct" data={data} onChange={onChange} required />
            <Num label={t("CH₄ in TOC (wt %)")} field="toc_ch4_wt_pct" data={data} onChange={onChange} required />
            <Num label={t("Destruction efficiency (%)")} field="destruction_efficiency" data={data} onChange={onChange} placeholder="98" />
          </FieldGrid>
        </>
      )}
    </div>
  );
};

export interface SectionMethodPanelProps {
  processType: string;
  sourceType: string;
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  legacy: React.ReactNode;
}

// Method switch + the matching form. `legacy` is the process's existing form.
export const SectionMethodPanel: React.FC<SectionMethodPanelProps> = ({
  processType,
  sourceType,
  data,
  onChange,
  legacy,
}) => {
  const choices = sectionChoices(processType, sourceType);
  if (!choices) return <>{legacy}</>;
  const cur = currentChoice(data);
  const selected = choices.some((c) => c.value === cur) ? cur : choices[0].value;

  let body = legacy;
  if (selected === "activity") body = <ActivityFactorForm processType={processType} data={data} onChange={onChange} />;
  else if (selected.startsWith("vent:")) body = <VentedGasForm data={data} onChange={onChange} />;
  else if (selected.startsWith("comb:")) body = <CombustionMethodForm data={data} onChange={onChange} />;

  return (
    <div className="[display:grid] [grid-template-columns:1fr] [gap:16px]">
      {choices.length > 1 && (
        <Segmented
          ariaLabel={t("Calculation method")}
          options={choices}
          value={selected}
          onChange={(v) => v !== selected && applyChoice(v, onChange, data)}
        />
      )}
      {body}
    </div>
  );
};

export default SectionMethodPanel;
