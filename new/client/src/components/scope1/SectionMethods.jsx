// API Compendium methods that are not "activity x catalog factor": activity-factor tables
// (Section 6), measured / engineered gas volumes, and combustion / waste-gas methods
// (Sections 4 and 5). The server routes on activity_key, vent_method and combustion_method.
import React, { useEffect, useState } from "react";
import { Input, Field } from "../../ui";
import api from "../../api";
import CustomDropdown from "../CustomDropdown";
import { FieldGrid, MoreOptions, Segmented } from "./ui";
import { applyChoice, currentChoice, sectionChoices } from "./methodChoices";

// ---------------------------------------------------------------------------
const Num = ({ label, field, data, onChange, placeholder, required }) => (
  <Field className="input-group" label={<>{label}
      {required && <span className="text-[color:#b91c1c]! ml-[3px]!">*</span>}</>}>
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

const NumUnit = ({ label, field, unitField, units, data, onChange, placeholder, required }) => (
  <div className="input-group">
    <label>
      {label}
      {required && <span className="text-[color:#b91c1c]! ml-[3px]!">*</span>}
    </label>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 110px", gap: "8px" }}>
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

const Composition = ({ data, onChange, c2 = false, required = true }) => (
  <FieldGrid min={160}>
    <Num label="CH₄ (mol %)" field="ch4_content" data={data} onChange={onChange} placeholder="e.g. 70" required={required} />
    <Num label="CO₂ (mol %)" field="co2_content" data={data} onChange={onChange} placeholder="e.g. 9" />
    {c2 && <Num label="C₂+ (mol %)" field="c2plus_content" data={data} onChange={onChange} placeholder="e.g. 4" />}
  </FieldGrid>
);

// ---- Tier 1: activity-factor tables ----
const plural = (a) => (a && !a.endsWith("s") ? `${a}s` : a);
const PER_INPUT = {
  unit: { label: (a) => `Number (${a || "events"})` },
  unit_day: { label: (a) => `Number of ${plural(a) || "units"}`, extra: { field: "activity_days", label: "Days", placeholder: "whole month" } },
  unit_hr: { label: (a) => `Number of ${plural(a) || "units"}`, extra: { field: "activity_hours", label: "Hours", placeholder: "whole month" } },
  mmscf: { label: () => "Gas throughput", units: GAS_UNITS },
  mm_m3: { label: () => "Gas throughput", units: GAS_UNITS },
  mgal: { label: () => "Liquid loaded", units: LIQ_UNITS },
  bbl: { label: (a) => (a && a !== "bbl oil" ? `Volume (${a.replace("bbl ", "")})` : "Oil produced"), units: LIQ_UNITS },
};

export function ActivityFactorForm({ processType, data, onChange }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api
      .get("/activity-factors", { params: { process: processType } })
      .then((r) => live && setRows(r.data?.factors || []))
      .catch(() => live && setError("Could not load the factor list"));
    return () => {
      live = false;
    };
  }, [processType]);

  const row = rows.find((r) => r.key === data.activity_key);
  const spec = row ? PER_INPUT[row.per] : null;

  const pick = (key) => {
    onChange("activity_key", key);
    const r = rows.find((x) => x.key === key);
    const p = r && PER_INPUT[r.per];
    onChange("unit", p?.units ? p.units[0] : "count");
  };

  return (
    <div className="s1-stack">
      <div className="input-group">
        <label>
          Source<span className="text-[color:#b91c1c]! ml-[3px]!">*</span>
        </label>
        <CustomDropdown
          options={rows.map((r) => ({ value: r.key, label: r.label }))}
          value={data.activity_key || ""}
          onChange={pick}
          placeholder={error || "Select source"}
        />
      </div>
      {spec && (
        <FieldGrid min={180}>
          {spec.units ? (
            <NumUnit label={spec.label(row.activity)} field="amount" unitField="unit" units={spec.units} data={data} onChange={onChange} required />
          ) : (
            <Num label={spec.label(row.activity)} field="amount" data={data} onChange={onChange} required />
          )}
          {spec.extra && (
            <Num label={spec.extra.label} field={spec.extra.field} data={data} onChange={onChange} placeholder={spec.extra.placeholder} />
          )}
        </FieldGrid>
      )}
      {row &&
        (row.toc ? (
          <FieldGrid min={180}>
            <Num label="CH₄ in vapour (wt %)" field="toc_ch4_wt" data={data} onChange={onChange} placeholder="15" />
          </FieldGrid>
        ) : (
          <MoreOptions label="Site gas composition">
            <Composition data={data} onChange={onChange} required={false} />
          </MoreOptions>
        ))}
    </div>
  );
}

// ---- measured / engineered gas volumes ----
export function VentedGasForm({ data, onChange }) {
  const m = data.vent_method;
  const flared = data.disposition === "flared";
  const canFlare = ["volume", "gor", "rate_days", "actual"].includes(m);
  const noComposition = ["co2_mass", "agr_balance", "thc_mass", "reported_mass"].includes(m);
  return (
    <div className="s1-stack">
      {m === "volume" && (
        <FieldGrid>
          <NumUnit label="Gas volume" field="gas_volume" unitField="gas_volume_unit" units={GAS_UNITS} data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "gor" && (
        <FieldGrid min={160}>
          <Num label="GOR (scf/bbl)" field="gor" data={data} onChange={onChange} required />
          <Num label="Oil rate (bbl/day)" field="oil_rate" data={data} onChange={onChange} required />
          <Num label="Vent duration (hours)" field="vent_hours" data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "rate_days" && (
        <FieldGrid min={180}>
          <NumUnit label="Gas rate" field="gas_rate" unitField="gas_rate_unit" units={["scf/day", "Mcf/day", "MMscf/day", "m3/day"]} data={data} onChange={onChange} required />
          <Num label="Days" field="days" data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "actual" && (
        <FieldGrid min={160}>
          <NumUnit label="Actual gas volume" field="actual_volume" unitField="actual_unit" units={["ft3", "bbl", "gal", "m3"]} data={data} onChange={onChange} required />
          <Num label="Temperature (°F)" field="gas_temp_f" data={data} onChange={onChange} placeholder="60" />
          <Num label="Pressure (atm)" field="gas_pressure_atm" data={data} onChange={onChange} placeholder="1" />
        </FieldGrid>
      )}
      {m === "desiccant" && (
        <FieldGrid min={160}>
          <Num label="Vessel height (ft)" field="vessel_height_ft" data={data} onChange={onChange} required />
          <Num label="Vessel diameter (ft)" field="vessel_diameter_ft" data={data} onChange={onChange} required />
          <Num label="Gas pressure (psig)" field="vessel_pressure_psig" data={data} onChange={onChange} required />
          <Num label="Refills per year" field="refills" data={data} onChange={onChange} required />
          <Num label="Gas-filled share (%)" field="gas_fraction" data={data} onChange={onChange} placeholder="45" />
        </FieldGrid>
      )}
      {m === "co2_mass" && (
        <FieldGrid min={160}>
          <Num label="Volume released (m³)" field="physical_volume_m3" data={data} onChange={onChange} required />
          <Num label="CO₂ density (kg/m³)" field="co2_density" data={data} onChange={onChange} required />
          <Num label="CO₂ (wt %)" field="co2_wt_pct" data={data} onChange={onChange} placeholder="100" />
          <Num label="Events" field="events" data={data} onChange={onChange} placeholder="1" />
        </FieldGrid>
      )}
      {m === "agr_balance" && (
        <FieldGrid min={160}>
          <NumUnit label="Sour gas in" field="sour_gas_volume" unitField="gas_volume_unit" units={GAS_UNITS} data={data} onChange={onChange} required />
          <Num label="Sour gas CO₂ (mol %)" field="sour_co2_content" data={data} onChange={onChange} required />
          <Num label="Sweet gas out (same unit)" field="sweet_gas_volume" data={data} onChange={onChange} required />
          <Num label="Sweet gas CO₂ (mol %)" field="sweet_co2_content" data={data} onChange={onChange} placeholder="0" />
        </FieldGrid>
      )}
      {m === "thc_mass" && (
        <FieldGrid min={170}>
          <NumUnit label="Total hydrocarbon loss" field="thc_loss" unitField="thc_loss_unit" units={["t", "kg", "lb"]} data={data} onChange={onChange} required />
          <Num label="CH₄ in vent (wt %)" field="ch4_wt_pct" data={data} onChange={onChange} required />
          <Num label="CO₂ in vent (wt %)" field="co2_wt_pct" data={data} onChange={onChange} placeholder="0" />
        </FieldGrid>
      )}
      {m === "reported_mass" && (
        <FieldGrid min={170}>
          <NumUnit label="CH₄ before control" field="ch4_mass" unitField="mass_unit" units={["t", "kg", "lb"]} data={data} onChange={onChange} required />
          <Num label="CO₂ before control (same unit)" field="co2_mass" data={data} onChange={onChange} placeholder="0" />
          <Num label="Control efficiency (%)" field="control_efficiency" data={data} onChange={onChange} placeholder="0" />
        </FieldGrid>
      )}
      {!noComposition && <Composition data={data} onChange={onChange} c2={flared} />}
      {canFlare && (
        <FieldGrid min={180}>
          <div className="input-group">
            <label>Gas released</label>
            <Segmented
              ariaLabel="Gas released"
              options={[
                { value: "vented", label: "Vented" },
                { value: "flared", label: "Flared" },
              ]}
              value={flared ? "flared" : "vented"}
              onChange={(v) => onChange("disposition", v)}
            />
          </div>
          {flared && <Num label="Combustion efficiency (%)" field="combustion_efficiency" data={data} onChange={onChange} placeholder="98" />}
        </FieldGrid>
      )}
    </div>
  );
}

// ---- combustion and waste-gas methods ----
export function CombustionMethodForm({ data, onChange }) {
  const m = data.combustion_method;
  const [equip, setEquip] = useState([]);
  useEffect(() => {
    if (m !== "equipment") return undefined;
    let live = true;
    api.get("/equipment-combustion-factors").then((r) => live && setEquip(r.data?.factors || [])).catch(() => {});
    return () => {
      live = false;
    };
  }, [m]);
  const eqRow = equip.find((e) => e.key === data.equipment_type);
  const energyBy = data.energy_basis || "fuel";

  return (
    <div className="s1-stack">
      {m === "carbon_content" && (
        <FieldGrid min={170}>
          <NumUnit label="Fuel burned" field="fuel_volume" unitField="fuel_volume_unit" units={LIQ_UNITS.map((u) => u.toLowerCase())} data={data} onChange={onChange} required />
          <NumUnit label="Fuel density" field="fuel_density" unitField="density_unit" units={["lb/gal", "kg/m3", "kg/L"]} data={data} onChange={onChange} required />
          <Num label="Carbon (wt %)" field="carbon_wt_pct" data={data} onChange={onChange} required />
        </FieldGrid>
      )}
      {m === "equipment" && (
        <>
          <div className="input-group">
            <label>
              Equipment<span className="text-[color:#b91c1c]! ml-[3px]!">*</span>
            </label>
            <CustomDropdown
              options={equip.map((e) => ({ value: e.key, label: e.label }))}
              value={data.equipment_type || ""}
              onChange={(v) => onChange("equipment_type", v)}
              placeholder="Select equipment"
            />
          </div>
          <Segmented
            ariaLabel="Energy input"
            options={[
              { value: "fuel", label: "Fuel burned" },
              { value: "engine", label: "Engine hours" },
              { value: "energy", label: "Energy (MMBtu)" },
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
                  label="Fuel burned"
                  field="fuel_volume"
                  unitField="fuel_volume_unit"
                  units={eqRow && eqRow.fuel !== "natural_gas" ? ["gal", "bbl", "m3", "l"] : ["scf", "Mcf", "MMscf", "m3"]}
                  data={data}
                  onChange={onChange}
                  required
                />
                {(!eqRow || eqRow.fuel === "natural_gas") ? (
                  <Num label="HHV (Btu/scf)" field="hhv_btu_scf" data={data} onChange={onChange} placeholder="1026" />
                ) : (
                  <Num label="HHV (MMBtu/gal)" field="hhv_mmbtu_gal" data={data} onChange={onChange} placeholder={eqRow.fuel === "diesel" ? "0.138" : "0.125"} />
                )}
              </>
            )}
            {energyBy === "engine" && (
              <>
                <Num label="Rating (hp)" field="engine_hp" data={data} onChange={onChange} required />
                <Num label="Load (%)" field="load_pct" data={data} onChange={onChange} placeholder="100" />
                <Num label="Operating hours" field="operating_hours" data={data} onChange={onChange} required />
              </>
            )}
            {energyBy === "energy" && <Num label="Energy input, HHV (MMBtu)" field="energy_mmbtu" data={data} onChange={onChange} required />}
          </FieldGrid>
          <MoreOptions>
            <FieldGrid min={170}>
              <Num label="CO₂ factor (t/MMBtu)" field="co2_ef_t_mmbtu" data={data} onChange={onChange} placeholder="fuel default" />
              {energyBy === "engine" && <Num label="Heat rate (Btu/hp-hr)" field="heat_rate_btu_hphr" data={data} onChange={onChange} placeholder="7000" />}
            </FieldGrid>
          </MoreOptions>
        </>
      )}
      {m === "vehicle_distance" && (
        <>
          <FieldGrid min={170}>
            <NumUnit label="Distance" field="distance" unitField="distance_unit" units={["mile", "km"]} data={data} onChange={onChange} required />
            <Num label="Fuel economy (miles/gal)" field="fuel_economy_mpg" data={data} onChange={onChange} required />
            <div className="input-group">
              <label>Vehicle</label>
              <CustomDropdown
                options={[
                  { value: "hd_diesel_advanced", label: "Heavy-duty diesel, advanced control" },
                  { value: "diesel", label: "Other diesel vehicle" },
                  { value: "gasoline", label: "Gasoline vehicle" },
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
                placeholder="Select vehicle"
              />
            </div>
          </FieldGrid>
          <MoreOptions>
            <FieldGrid min={170}>
              <Num label="CH₄ (t / 1,000 gal)" field="ch4_t_per_kgal" data={data} onChange={onChange} placeholder="default" />
              <Num label="N₂O (t / 1,000 gal)" field="n2o_t_per_kgal" data={data} onChange={onChange} placeholder="default" />
              <Num label="HHV (MMBtu/gal)" field="hhv_mmbtu_gal" data={data} onChange={onChange} placeholder="fuel default" />
              <Num label="CO₂ factor (t/MMBtu)" field="co2_ef_t_mmbtu" data={data} onChange={onChange} placeholder="fuel default" />
            </FieldGrid>
          </MoreOptions>
        </>
      )}
      {m === "flare_voc" && (
        <>
          <FieldGrid min={170}>
            <NumUnit label="VOC emitted" field="voc_mass" unitField="voc_mass_unit" units={["t", "kg", "lb", "short_ton"]} data={data} onChange={onChange} required />
            <Num label="Combustion efficiency (%)" field="combustion_efficiency" data={data} onChange={onChange} placeholder="98" />
          </FieldGrid>
          <label className="s1-label">Flare gas analysis (wt %)</label>
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
            ariaLabel="Oxidizer feed"
            options={[
              { value: "loading", label: "Loading losses" },
              { value: "toc", label: "TOC mass" },
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
                <NumUnit label="Liquid loaded" field="liquid_loaded" unitField="liquid_unit" units={LIQ_UNITS} data={data} onChange={onChange} required />
                <Num label="Loading loss (lb VOC / 1,000 gal)" field="loading_loss_lb_kgal" data={data} onChange={onChange} required />
                <Num label="VOC share of TOC (%)" field="voc_fraction_of_toc" data={data} onChange={onChange} placeholder="85" />
              </>
            ) : (
              <NumUnit label="TOC to oxidizer" field="toc_mass" unitField="toc_mass_unit" units={["t", "kg", "lb"]} data={data} onChange={onChange} required />
            )}
            <Num label="TOC carbon (wt %)" field="toc_carbon_wt_pct" data={data} onChange={onChange} required />
            <Num label="CH₄ in TOC (wt %)" field="toc_ch4_wt_pct" data={data} onChange={onChange} required />
            <Num label="Destruction efficiency (%)" field="destruction_efficiency" data={data} onChange={onChange} placeholder="98" />
          </FieldGrid>
        </>
      )}
    </div>
  );
}

// Method switch + the matching form. `legacy` is the process's existing form.
export function SectionMethodPanel({ processType, sourceType, data, onChange, legacy }) {
  const choices = sectionChoices(processType, sourceType);
  if (!choices) return legacy;
  const cur = currentChoice(data);
  const selected = choices.some((c) => c.value === cur) ? cur : choices[0].value;

  let body = legacy;
  if (selected === "activity") body = <ActivityFactorForm processType={processType} data={data} onChange={onChange} />;
  else if (selected.startsWith("vent:")) body = <VentedGasForm data={data} onChange={onChange} />;
  else if (selected.startsWith("comb:")) body = <CombustionMethodForm data={data} onChange={onChange} />;

  return (
    <div className="s1-stack">
      {choices.length > 1 && (
        <Segmented
          ariaLabel="Calculation method"
          options={choices}
          value={selected}
          onChange={(v) => v !== selected && applyChoice(v, onChange, data)}
        />
      )}
      {body}
    </div>
  );
}
