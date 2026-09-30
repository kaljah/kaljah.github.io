// Calculation-method selection for the Scope 1 form: which API Compendium methods each process
// offers per tier, and the formData keys the server routes on (activity_key, vent_method,
// combustion_method). Components live in SectionMethods.jsx.
// Keys each method writes; cleared when the user switches method so nothing stale is sent
const METHOD_KEYS = ["activity_key", "vent_method", "combustion_method"];

// ---- which methods each process offers, per tier ----
const ACTIVITY = { value: "activity", label: "Compendium factor" };
const VENT = {
  volume: { value: "vent:volume", label: "Measured volume" },
  gor: { value: "vent:gor", label: "GOR × oil rate" },
  rate_days: { value: "vent:rate_days", label: "Rate × days" },
  actual: { value: "vent:actual", label: "Actual volume (T, P)" },
  desiccant: { value: "vent:desiccant", label: "Vessel volume" },
  co2_mass: { value: "vent:co2_mass", label: "Blowdown volume" },
  agr_balance: { value: "vent:agr_balance", label: "Sour / sweet balance" },
  thc_mass: { value: "vent:thc_mass", label: "Hydrocarbon loss (AP-42 / simulation)" },
  reported_mass: { value: "vent:reported_mass", label: "Simulation / measured result" },
};
const COMB = {
  carbon_content: { value: "comb:carbon_content", label: "Carbon content" },
  equipment: { value: "comb:equipment", label: "Equipment basis" },
  vehicle_distance: { value: "comb:vehicle_distance", label: "Distance travelled" },
  flare_voc: { value: "comb:flare_voc", label: "From VOC emitted" },
  thermal_oxidizer: { value: "comb:thermal_oxidizer", label: "Thermal oxidizer" },
};
const LEGACY = (label) => ({ value: "legacy", label });
const MEASURED = [VENT.volume, VENT.gor, VENT.rate_days, VENT.actual];

// processes that exist only for these methods
export const SECTION_PROCESSES = {
  well_testing: "Well Testing",
  workovers: "Workovers (no hydraulic fracturing)",
  casing_gas: "Casing Gas Venting",
  compressor_venting: "Compressor Venting (seals / rod packing)",
  non_routine_venting: "Non-Routine Venting (blowdowns, PRVs, dig-ins)",
  vented_gas: "Vented / Flared Gas Volume",
  desiccant_dehydrator: "Desiccant Dehydrator",
  co2_eor: "CO₂ EOR Venting",
  thermal_oxidizer: "Thermal Oxidizer",
};

const TIER = {
  default: { key: "default", tier: "Tier 1", label: "Compendium Factor", sub: "Count or throughput" },
  specific: { key: "specific", tier: "Tier 3", label: "Measured / Engineered", sub: "Gas volume and composition" },
};
// tier buttons for processes whose tiers are these methods (library is appended by the form)
export const SECTION_TIERS = {
  well_testing: [TIER.default, TIER.specific],
  workovers: [TIER.default, TIER.specific],
  casing_gas: [TIER.default, TIER.specific],
  compressor_venting: [TIER.default, TIER.specific],
  non_routine_venting: [TIER.default, TIER.specific],
  vented_gas: [TIER.specific],
  desiccant_dehydrator: [TIER.specific],
  co2_eor: [TIER.specific],
  thermal_oxidizer: [TIER.specific],
  agr: [TIER.default, { ...TIER.specific, label: "Engineering", sub: "Throughput, CO₂ in / out" }],
  dehydrator: [TIER.default, { ...TIER.specific, label: "Simulation / Measured", sub: "GLYCalc or vent measurement" }],
};

export function sectionChoices(processType, sourceType) {
  const t = sourceType;
  switch (processType) {
    case "well_testing":
    case "workovers":
    case "casing_gas":
    case "compressor_venting":
    case "non_routine_venting":
      return t === "default" ? [ACTIVITY] : t === "specific" ? MEASURED : null;
    case "vented_gas":
      return MEASURED;
    case "desiccant_dehydrator":
      return [VENT.desiccant];
    case "co2_eor":
      return [VENT.co2_mass];
    case "thermal_oxidizer":
      return [COMB.thermal_oxidizer];
    case "agr":
      return t === "default" ? [ACTIVITY] : t === "specific" ? [LEGACY("Throughput & CO₂"), VENT.agr_balance] : null;
    case "dehydrator":
      return t === "default" ? [ACTIVITY] : t === "specific" ? [{ ...VENT.volume, label: "Measured vent volume" }, VENT.reported_mass] : null;
    // Tier 1 pneumatics, loading and separators use the Compendium tables only (Tables 6-14 to 6-16,
    // 6-29, 6-34, 6-42, 6-47, 6-25 to 6-27); the old catalog rows were mislabelled or had no source
    case "pneumatic":
    case "loading":
    case "separation":
      return t === "default" ? [ACTIVITY] : null;
    case "venting":
      return t === "default" ? [LEGACY("Gas volume factor"), ACTIVITY] : null;
    case "tank":
    case "tank_flashing":
      return t === "specific" ? [LEGACY("Flashing"), VENT.actual] : null;
    // Section 6.3.9.3: working / standing losses are not a flashing calculation
    case "tank_working":
    case "tank_breathing":
      return t === "specific" ? [VENT.thc_mass] : null;
    case "combustion":
      return t === "specific" ? [LEGACY("Fuel analysis"), COMB.carbon_content, COMB.equipment] : null;
    case "mobile":
      return t === "specific" ? [COMB.vehicle_distance] : null;
    case "flaring":
    case "routine_flaring":
    case "non_routine_flaring":
    case "safety_flaring":
      return t === "specific" ? [LEGACY("Metered volume"), COMB.flare_voc] : null;
    default:
      return null;
  }
}

// the method currently selected in formData ("legacy" when none of ours is set)
export function currentChoice(data) {
  if (data.activity_key !== undefined) return "activity";
  if (data.vent_method) return `vent:${data.vent_method}`;
  if (data.combustion_method) return `comb:${data.combustion_method}`;
  return "legacy";
}

export function sectionMethodActive(data) {
  return currentChoice(data) !== "legacy";
}

// Switching method starts the method's inputs from empty: fields of the previous method are not
// submitted with the next one (Tier 3 browser test #20)
export function applyChoice(choice, onChange, data = {}) {
  Object.keys(data).forEach((k) => {
    if (k !== "process_type" && data[k] !== undefined) onChange(k, undefined);
  });
  METHOD_KEYS.forEach((k) => onChange(k, undefined));
  if (choice === "activity") onChange("activity_key", "");
  else if (choice.startsWith("vent:")) onChange("vent_method", choice.slice(5));
  else if (choice.startsWith("comb:")) onChange("combustion_method", choice.slice(5));
}

// Keep formData in step with the tier: select the first method when the current one is not offered
export function syncSectionChoice(processType, sourceType, data, onChange) {
  const choices = sectionChoices(processType, sourceType);
  const cur = currentChoice(data);
  if (!choices) {
    if (cur !== "legacy") applyChoice("legacy", onChange, data);
    return;
  }
  if (!choices.some((c) => c.value === cur)) applyChoice(choices[0].value, onChange, data);
}
