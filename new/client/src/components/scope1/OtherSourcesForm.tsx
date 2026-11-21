import React, { useEffect } from "react";
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { t } from "../../i18n";

// API Compendium 2021 sections 5 / 7.5 / 7.6 sources calculated from their own inputs (no emission factor):
// fire suppression, wastewater, refrigerant (HFC) and electrical equipment (SF6). They were reachable through the API
// and the CSV only (GB RY2022 GB-045). Field names are the server's (calculations/fugitive_other.py, FireSuppression).

export const OTHER_SOURCE_PROCESSES = ["fire_suppression", "wastewater", "refrigerant", "electrical_equipment"];

export interface OtherSourcesFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

type Spec = { field: string; label: string; required?: boolean; placeholder?: string; options?: [string, string][] };

const num = (field: string, label: string, required = false, placeholder?: string): Spec => ({ field, label, required, placeholder });

const WASTEWATER: Record<string, Spec[]> = {
  aerobic: [
    num("bod5_mg_l", t("BOD5 removed (mg/L)"), true, "e.g. 25"),
    num("mcf", t("MCF (optional, at most 0.1)")),
    num("cod_kg_m3", t("COD (kg/m³), with an MCF")),
  ],
  anaerobic_epa: [num("bod5_lb_ft3", t("BOD5 loading (lb/ft³)"), true), num("fad_pct", t("Fraction anaerobically digested (%)"), true)],
  ipcc: [
    num("cod_kg_m3", t("COD (kg/m³)"), true),
    {
      field: "treatment_type", label: t("Treatment type (or enter the MCF)"), options: [
        ["", t("Select")], ["aerobic_centralized", t("Aerobic, centralised (MCF 0)")],
        ["anaerobic_reactor", t("Anaerobic reactor (MCF 0.8)")], ["anaerobic_shallow_lagoon", t("Anaerobic shallow lagoon (MCF 0.2)")],
        ["anaerobic_deep_lagoon", t("Anaerobic deep lagoon (MCF 0.8)")],
      ],
    },
    num("mcf", t("MCF (fraction)")),
  ],
};

const MASS_BALANCE: Spec[] = [
  num("stock_begin", t("Stock at the beginning of the year"), true),
  num("stock_end", t("Stock at the end of the year"), true),
  num("purchases", t("Purchases"), true),
  num("sales", t("Sales and disbursements"), true),
  num("capacity_increase", t("Net increase in equipment capacity")),
  { field: "mass_unit", label: t("Mass unit"), options: [["kg", "kg"], ["lb", "lb"], ["tonne", t("tonne")]] },
];

const REFRIGERANT: Record<string, Spec[]> = {
  charge: [
    num("equipment_count", t("Number of units"), true),
    num("charge_kg", t("Full charge per unit (kg)"), true),
    num("operating_rate_pct", t("Operating emission rate (% of charge per year, blank = Table 7-83)")),
    { field: "equipment_type", label: t("Equipment type (Table 7-83)"), options: [
      ["", t("Select")], ["domestic_refrigeration", t("Domestic refrigeration")], ["stand_alone_commercial", t("Stand-alone commercial")],
      ["medium_large_commercial_refrigeration", t("Medium / large commercial refrigeration")],
      ["transport_refrigeration", t("Transport refrigeration")], ["industrial_refrigeration", t("Industrial refrigeration")],
    ] },
  ],
  mass_balance: MASS_BALANCE,
};

const SF6: Record<string, Spec[]> = {
  mass_balance: MASS_BALANCE,
  recharge: [num("recharge", t("SF₆ recharged in the period"), true), { field: "mass_unit", label: t("Mass unit"), options: [["kg", "kg"], ["lb", "lb"]] }],
};

const Fields: React.FC<{ specs: Spec[]; data: Record<string, any>; onChange: (f: string, v: any) => void }> = ({ specs, data, onChange }) => (
  <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
    {specs.map((s) => (
      <Field key={s.field} label={<>{s.label}{s.required && <span className="text-[color:var(--color-red-700)]! ms-[3px]!">*</span>}</>}>
        {s.options ? (
          <NativeSelect value={data[s.field] ?? ""} onChange={(e) => onChange(s.field, e.target.value || undefined)}>
            {s.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </NativeSelect>
        ) : (
          <Input type="number" step="any" value={data[s.field] ?? ""} placeholder={s.placeholder}
            onChange={(e) => onChange(s.field, e.target.value)} required={s.required} />
        )}
      </Field>
    ))}
  </div>
);

export const OtherSourcesForm: React.FC<OtherSourcesFormProps> = ({ data, onChange }) => {
  const p = data.process_type;

  // the activity sent at the top level: the released mass, the wastewater flow, or the unit count / gas bought
  useEffect(() => {
    if (p === "fire_suppression" && !data.unit) onChange("unit", "kg");
    if (p === "wastewater") {
      if (!data.wastewater_method) onChange("wastewater_method", "aerobic");
      if (!data.flow_unit) onChange("flow_unit", "m3");
      if (!data.unit) onChange("unit", data.flow_unit || "m3"); // the form refuses a record without a unit
    }
    if (p === "electrical_equipment" && !data.unit) onChange("unit", "kg");
    if (p === "refrigerant" && !data.unit) onChange("unit", "units");
    if (p === "refrigerant" && !data.refrigerant_method) onChange("refrigerant_method", "charge");
    if (p === "electrical_equipment" && !data.electrical_method) onChange("electrical_method", "mass_balance");
    // again after the form is reset following a save (it cleared the unit and the next save was refused)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p, data.unit, data.flow_unit, data.wastewater_method, data.refrigerant_method, data.electrical_method]);

  if (p === "fire_suppression") {
    return (
      <Fields data={data} onChange={onChange} specs={[
        { field: "agent_type", label: t("Agent"), options: [
          ["co2", "CO₂"], ["hfc_227ea", "HFC-227ea"], ["hfc_125", "HFC-125"], ["hfc_236fa", "HFC-236fa"],
          ["halon_1301", "Halon 1301"], ["fk_5_1_12", "FK-5-1-12"], ["other", t("Other")],
        ] },
        num("amount", t("Agent released (kg)"), true),
      ]} />
    );
  }
  if (p === "wastewater") {
    const m = data.wastewater_method || "aerobic";
    return (
      <div className="grid gap-3">
        <Fields data={data} onChange={(f, v) => { onChange(f, v); if (f === "flow") onChange("amount", v); if (f === "flow_unit") onChange("unit", v); }} specs={[
          { field: "wastewater_method", label: t("Method (Compendium 7.5)"), options: [
            ["aerobic", t("Aerobic treatment, CO₂ (Eq 7-19)")], ["anaerobic_epa", t("Anaerobic, EPA (Eq 7-20)")], ["ipcc", t("IPCC, COD and MCF (Eq 7-17)")],
          ] },
          num("flow", t("Wastewater flow"), true),
          { field: "flow_unit", label: t("Flow unit"), options: [["m3", "m³"], ["m3/day", "m³/day"], ["m3/yr", "m³/yr"], ["gal", "gal"], ["gal/day", "gal/day"], ["ft3", "ft³"]] },
        ]} />
        <Fields data={data} onChange={onChange} specs={WASTEWATER[m] || []} />
        <Fields data={data} onChange={onChange} specs={[num("n_effluent_mg_l", t("Effluent nitrogen (mg/L), for N₂O (Eq 7-18)"))]} />
      </div>
    );
  }
  if (p === "refrigerant" || p === "electrical_equipment") {
    const isHfc = p === "refrigerant";
    const methodField = isHfc ? "refrigerant_method" : "electrical_method";
    const m = data[methodField] || (isHfc ? "charge" : "mass_balance");
    const table = isHfc ? REFRIGERANT : SF6;
    const amountFrom = isHfc && m === "charge" ? "equipment_count" : m === "recharge" ? "recharge" : "purchases";
    return (
      <div className="grid gap-3">
        <Fields data={data} onChange={onChange} specs={[
          { field: methodField, label: t("Method"), options: isHfc
            ? [["charge", t("Charge x operating rate (Eq 7-21)")], ["mass_balance", t("Mass balance (Eq 7-22)")]]
            : [["mass_balance", t("Mass balance (Eq 7-23)")], ["recharge", t("Recharge (Eq 7-24)")]] },
          ...(isHfc ? [{ field: "refrigerant", label: t("Refrigerant"), options: [["HFC-134a", "HFC-134a"], ["R-404A", "R-404A"], ["R-407C", "R-407C"], ["R-410A", "R-410A"], ["R-507A", "R-507A"]] as [string, string][] }] : []),
        ]} />
        <Fields data={data} onChange={(f, v) => { onChange(f, v); if (f === amountFrom) { onChange("amount", v); onChange("unit", isHfc && m === "charge" ? "units" : data.mass_unit || "kg"); } }} specs={table[m] || []} />
      </div>
    );
  }
  return null;
};

export default OtherSourcesForm;
