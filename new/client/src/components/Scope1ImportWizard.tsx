import React, { useCallback, useState } from "react";
import { Activity, Container, Cpu, Download, Droplets, File as FileIcon, FileSpreadsheet, Flame, Layers, Settings, TriangleAlert, Wind, Zap } from "lucide-react";
import { Badge, Banner, Button, Field, NativeSelect, RadioCardGroup } from "../ui";
import api from "../api";
import { useToast } from "./Toast";
import ImportWizard from "./import-wizard/ImportWizard";
import { controlClass, FieldGroupData } from "./import-wizard/mapping";
import { cn } from "../ui/cn";

// ─── Process catalogue (keys are the server's Scope 1 process types) ─────────
const COMP = ["c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","co2_mol","n2_mol"];

export interface ProcessCatalogueItem {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string; [key: string]: any }>;
  tier3Extra: string[];
}

const PROCESS_CATALOGUE: ProcessCatalogueItem[] = [
  { key: "combustion",    label: "Combustion",             icon: Flame,     tier3Extra: ["hhv", ...COMP, "combustion_efficiency", "operating_temperature", "temp_unit", "operating_pressure", "press_unit", "z_factor"] },
  { key: "flaring",       label: "Flaring",                icon: Flame,     tier3Extra: ["flare_type", "control_efficiency", ...COMP] },
  { key: "venting",       label: "Venting",                icon: Wind,      tier3Extra: ["vent_method", "disposition", "ch4_content", "co2_content"] },
  { key: "blowdown",      label: "Blowdowns",              icon: Zap,       tier3Extra: ["blowdown_pressure", "blowdown_events", "blowdown_temp", "blowdown_temp_unit", "blowdown_press_unit", "z_factor", "ch4_content", "co2_content"] },
  { key: "tank_flashing", label: "Tank Flashing",          icon: Container, tier3Extra: ["tank_gor", "tank_ch4_content", "tank_control_eff", "tank_api_gravity"] },
  { key: "pneumatic",     label: "Pneumatic Devices",      icon: Cpu,       tier3Extra: ["pneu_count", "pneu_bleed_rate", "pneu_bleed_unit", "pneu_hours", "pneu_ch4_content"] },
  { key: "fugitive",      label: "Equipment Leaks",        icon: Droplets,  tier3Extra: ["fugitive_method", "component_type", "service", "m21_below_count", "m21_above_count"] },
  { key: "completions",   label: "Well Completions",       icon: Layers,    tier3Extra: ["comp_method", "comp_rate", "comp_rate_unit", "comp_duration", "comp_flare_eff", "ch4_content", "co2_content"] },
  { key: "unloading",     label: "Liquids Unloading",      icon: Layers,    tier3Extra: ["unload_depth", "unload_diam", "unload_press", "unload_freq", "unload_flare_eff", "ch4_content", "co2_content"] },
  { key: "drilling",      label: "Drilling",               icon: Layers,    tier3Extra: ["mud_type"] },
  { key: "dehydrator",    label: "Dehydrators",            icon: Droplets,  tier3Extra: ["vent_method", "ch4_content", "co2_content"] },
  { key: "agr",           label: "AGR / Acid Gas Removal", icon: Activity,  tier3Extra: ["agr_co2_in", "agr_co2_out", "agr_ch4_in", "agr_ch4_slip", "agr_control_eff"] },
];

// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS: FieldGroupData[] = [
  {
    id: "identity",
    label: "Location & Identity",
    icon: Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM (or map Year and Month)" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "activity",      label: "Activity",       required: false, hint: "e.g. Exploration & Production" },
      { key: "division",      label: "Division",       required: false, hint: "e.g. Production, Association" },
      { key: "field",         label: "Field",          required: false, hint: "e.g. Bir Berkine" },
      { key: "group",         label: "Emission Source",required: false, hint: "Logical grouping for this emission source" },
      { key: "equipment",     label: "Equipment Name", required: false, hint: "Name of the piece of equipment" },
      { key: "equipment_id",  label: "Equipment ID",   required: false, hint: "Unique identifier for the equipment (duplicate check)" },
    ],
  },
  {
    id: "measurement",
    label: "Measurement",
    icon: Activity,
    fields: [
      { key: "process",       label: "Process Type",  required: true,  hint: "e.g. combustion, flaring, venting (keys or the form's names)" },
      { key: "fuel",          label: "Activity / Fuel", required: false, hint: "Emission factor name as listed in the manual form (default and custom rows)" },
      { key: "quantity",      label: "Quantity",      required: true,  hint: "Activity of the month" },
      { key: "unit",          label: "Unit",          required: true,  hint: "e.g. scf, Mscf, m3, bbl, gal, tonne, days, devices" },
      { key: "factor_type",   label: "Factor Type",   required: false, hint: "default (API Compendium) | custom (saved factor) | specific (Tier 3)" },
      { key: "operating_hours", label: "Operating Hours", required: false, hint: "Hours in the month: required for pneumatic controller factors and equipment leaks" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column (YYYY-MM)" },
    ],
  },
  {
    id: "gas_composition",
    label: "Gas Composition (Tier 3)",
    icon: Settings,
    tier3Only: true,
    fields: [
      { key: "c1",      label: "C1 (Methane) mol%",  required: false, hint: "Methane mole %" },
      { key: "c2",      label: "C2 (Ethane) mol%",   required: false, hint: "Ethane mole %" },
      { key: "c3",      label: "C3 (Propane) mol%",  required: false, hint: "Propane mole %" },
      { key: "c4",      label: "C4 mol%",            required: false, hint: "Butane mole %" },
      { key: "c5",      label: "C5 mol%",            required: false, hint: "Pentane mole %" },
      { key: "c6",      label: "C6 mol%",            required: false, hint: "Hexane mole %" },
      { key: "c7",      label: "C7 mol%",            required: false, hint: "" },
      { key: "c8",      label: "C8 mol%",            required: false, hint: "" },
      { key: "c9",      label: "C9 mol%",            required: false, hint: "" },
      { key: "c10",     label: "C10+ mol%",          required: false, hint: "" },
      { key: "co2_mol", label: "CO₂ mol%",           required: false, hint: "CO2 mole % of the gas" },
      { key: "n2_mol",  label: "N₂ mol%",            required: false, hint: "Nitrogen mole %" },
      { key: "hhv",     label: "HHV",               required: false, hint: "Higher heating value (Btu/scf for gas)" },
      { key: "ch4_content", label: "CH4 Content %",  required: false, hint: "CH4 mole % when the full composition is not given" },
      { key: "co2_content", label: "CO2 Content %",  required: false, hint: "CO2 mole % when the full composition is not given" },
    ],
  },
  {
    id: "combustion_params",
    label: "Combustion / Flaring Parameters (Tier 3)",
    icon: Flame,
    tier3Only: true,
    fields: [
      { key: "combustion_efficiency", label: "Combustion Efficiency %", required: false, hint: "Defaults to 99.5 % for combustion" },
      { key: "flare_type",           label: "Flare Type",             required: false, hint: "elevated | enclosed_ground | air_assisted | steam_assisted" },
      { key: "control_efficiency",   label: "Flare Control Efficiency %", required: false, hint: "Flare destruction efficiency %" },
      { key: "operating_temperature",label: "Metering Temp",          required: false, hint: "Only for volumes in m3 / cf read at metering conditions" },
      { key: "temp_unit",            label: "Temp Unit",              required: false, hint: "C or F" },
      { key: "operating_pressure",   label: "Metering Pressure",      required: false, hint: "Only for volumes in m3 / cf read at metering conditions" },
      { key: "press_unit",           label: "Press Unit",             required: false, hint: "psig, psia, kPa, barg, bara" },
      { key: "z_factor",             label: "Z Factor",               required: false, hint: "Gas compressibility factor" },
    ],
  },
  {
    id: "vent_params",
    label: "Venting / Dehydrator / Blowdown (Tier 3)",
    icon: Wind,
    tier3Only: true,
    fields: [
      { key: "vent_method",         label: "Vent Method",          required: false, hint: "volume: the quantity is the measured gas volume (scf, Mcf, MMscf, m3)" },
      { key: "disposition",         label: "Disposition",          required: false, hint: "vented (default) or flared" },
      { key: "blowdown_pressure",   label: "Blowdown Pressure",    required: false, hint: "Vessel pressure before blowdown" },
      { key: "blowdown_events",     label: "Blowdown Events",      required: false, hint: "Events in the month" },
      { key: "blowdown_temp",       label: "Blowdown Temp",        required: false, hint: "Gas temperature in the vessel" },
      { key: "blowdown_temp_unit",  label: "Blowdown Temp Unit",   required: false, hint: "F | C | K" },
      { key: "blowdown_press_unit", label: "Blowdown Press Unit",  required: false, hint: "psig | psia | kPa" },
    ],
  },
  {
    id: "pneumatic_params",
    label: "Pneumatic Parameters (Tier 3)",
    icon: Cpu,
    tier3Only: true,
    fields: [
      { key: "pneu_count",       label: "Pneumatic Count",      required: false, hint: "Number of devices" },
      { key: "pneu_bleed_rate",  label: "Bleed Rate",           required: false, hint: "Measured bleed rate per device" },
      { key: "pneu_bleed_unit",  label: "Bleed Rate Unit",      required: false, hint: "scf or m3 (per hour)" },
      { key: "pneu_hours",       label: "Pneumatic Hours",      required: false, hint: "Operating hours in the month" },
      { key: "pneu_ch4_content", label: "Supply Gas CH4 %",     required: false, hint: "CH4 mole % of the supply gas" },
    ],
  },
  {
    id: "tank_params",
    label: "Tank Parameters (Tier 3)",
    icon: Container,
    tier3Only: true,
    fields: [
      { key: "tank_gor",            label: "Tank GOR",             required: false, hint: "Flash gas-to-oil ratio (scf/bbl)" },
      { key: "tank_ch4_content",    label: "Tank CH4 Content %",   required: false, hint: "CH4 mole % of the flash gas" },
      { key: "tank_control_eff",    label: "Tank Control Eff %",   required: false, hint: "Vapour control efficiency" },
      { key: "tank_api_gravity",    label: "Tank API Gravity",     required: false, hint: "API gravity of the stored liquid" },
    ],
  },
  {
    id: "fugitive_params",
    label: "Equipment Leak Parameters (Tier 3)",
    icon: Wind,
    tier3Only: true,
    fields: [
      { key: "fugitive_method", label: "Leak Method",       required: false, hint: "screening | correlation | ogi | measurement" },
      { key: "component_type",  label: "Component Type",    required: false, hint: "valve | connector | flange | open_ended_line | pump_seal | other" },
      { key: "service",         label: "Service",           required: false, hint: "gas | light_oil | heavy_oil | water_oil" },
      { key: "m21_below_count", label: "Screened < 10,000 ppmv", required: false, hint: "Components screened below 10,000 ppmv" },
      { key: "m21_above_count", label: "Screened ≥ 10,000 ppmv", required: false, hint: "Components screened at or above 10,000 ppmv" },
    ],
  },
  {
    id: "well_params",
    label: "Well / Drilling Parameters (Tier 3)",
    icon: Layers,
    tier3Only: true,
    fields: [
      { key: "mud_type",          label: "Mud Type",           required: false, hint: "water_based | oil_based | synthetic (quantity in drilling days)" },
      { key: "comp_method",       label: "Completion Method",  required: false, hint: "metered_volume | rate_duration | gor_liquid" },
      { key: "comp_rate",         label: "Flowback Rate",      required: false, hint: "Gas rate during flowback" },
      { key: "comp_rate_unit",    label: "Flowback Rate Unit", required: false, hint: "Mcf/hr (default) | Mcf/day | scf/hr | m3/hr" },
      { key: "comp_duration",     label: "Flowback Duration",  required: false, hint: "Hours" },
      { key: "comp_flare_eff",    label: "Completion Flare %", required: false, hint: "% of flowback gas flared" },
      { key: "unload_depth",      label: "Well Depth (ft)",    required: false, hint: "Liquids unloading" },
      { key: "unload_diam",       label: "Casing Diameter (in)", required: false, hint: "Liquids unloading" },
      { key: "unload_press",      label: "Shut-in Pressure (psig)", required: false, hint: "Liquids unloading" },
      { key: "unload_freq",       label: "Unloading Events",   required: false, hint: "Events in the month" },
      { key: "unload_flare_eff",  label: "Unloading Flare %",  required: false, hint: "% of unloading gas flared" },
    ],
  },
  {
    id: "dehydrator_agr",
    label: "AGR Parameters (Tier 3)",
    icon: Droplets,
    tier3Only: true,
    fields: [
      { key: "agr_co2_in",        label: "AGR CO₂ In %",       required: false, hint: "CO2 mole % in the feed" },
      { key: "agr_co2_out",       label: "AGR CO₂ Out %",      required: false, hint: "CO2 mole % in the sweet gas" },
      { key: "agr_ch4_in",        label: "AGR CH₄ In %",       required: false, hint: "CH4 mole % in the feed" },
      { key: "agr_ch4_slip",      label: "AGR CH₄ Slip",       required: false, hint: "Fraction of inlet CH4 (e.g. 0.001)" },
      { key: "agr_control_eff",   label: "AGR Control Eff %",  required: false, hint: "Acid gas destruction efficiency" },
    ],
  },
  {
    id: "uncertainty",
    label: "Uncertainty Overrides",
    icon: Settings,
    fields: [
      { key: "user_unc_co2", label: "User Uncertainty CO₂ %", required: false, hint: "Override the system uncertainty for CO2" },
      { key: "user_unc_ch4", label: "User Uncertainty CH₄ %", required: false, hint: "Override the system uncertainty for CH4" },
      { key: "user_unc_n2o", label: "User Uncertainty N₂O %", required: false, hint: "Override the system uncertainty for N2O" },
    ],
  },
];

const TIER_OPTIONS = [
  { value: "1", title: "Tier 1 — Standard", badge: <Badge tone="info">Minimum fields</Badge>, description: "Uses API Compendium default emission factors. Only requires fuel type, quantity, and unit. Fast and simple." },
  { value: "3", title: "Tier 3 — Engineering", badge: <Badge tone="success">Full precision</Badge>, description: "Uses actual gas composition (C1–C10), operating conditions (T/P), and process-specific parameters for maximum accuracy." },
  { value: "auto", title: "Both Tiers — Auto Detect", badge: <Badge tone="brand">Recommended</Badge>, description: "Mixes Tier 1 and Tier 3 rows in one file. The system detects per-row: if gas composition columns are filled, Tier 3 is used; otherwise Tier 1." },
];

const TIER_NOTE: Record<string, string> = {
  "1": "Tier 1 only requires: Region, Date, Process, Fuel, Quantity, Unit.",
  "3": "Tier 3 requires all Tier 1 fields plus gas composition and process engineering parameters.",
  auto: "Auto-detect is ideal when you have a mix of sources — some with gas composition data (Tier 3) and some without (Tier 1).",
};

const SCOPE_OPTIONS = [
  { value: "all", title: "All Processes", description: "Your file contains a Process column that identifies the type (Combustion, Flaring, Venting, etc.) for each row." },
  { value: "specific", title: "Specific Process(es)", description: "Your file is dedicated to one or more specific processes. Select which ones apply to filter the column mapping to only the relevant fields." },
];

const TEMPLATES = [
  { fmt: "excel" as const, icon: FileSpreadsheet, title: "Excel Template", note: "With dropdowns, sample data & engineering sheets" },
  { fmt: "csv" as const, icon: FileIcon, title: "CSV Template", note: "Lightweight flat file — best for large datasets" },
];

interface ProcessTileProps {
  process: ProcessCatalogueItem;
  selected: boolean;
  onToggle: () => void;
}

const ProcessTile: React.FC<ProcessTileProps> = ({ process, selected, onToggle }) => {
  const Icon = process.icon;
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onToggle}
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-md border bg-surface px-3 py-2.5 text-left text-sm font-semibold text-text transition-colors",
        selected ? "border-brand-500 bg-selected-bg" : "border-border hover:border-ink-300",
      )}
    >
      <Icon className="size-4 shrink-0 text-brand-700" aria-hidden="true" />
      {process.label}
    </button>
  );
};

export interface Scope1ImportWizardProps {
  onClose: () => void;
  onUploadSuccess?: () => void;
}

/** Scope 1 bulk import: pick the calculation tier and process scope, then the shared file and column-mapping steps. */
export const Scope1ImportWizard: React.FC<Scope1ImportWizardProps> = ({ onClose, onUploadSuccess }) => {
  const toast = useToast();
  const [tier, setTier] = useState<string>("auto");
  const [processScope, setProcessScope] = useState<string>("all");
  const [selectedProcesses, setSelectedProcesses] = useState<string[]>([]);
  const [globalFactor, setGlobalFactor] = useState<string>("auto");

  const toggleProcess = (key: string) => setSelectedProcesses((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));

  const fieldGroupsFor = useCallback(
    (): FieldGroupData[] => FIELD_GROUPS.map((g) => ({ ...g, badge: g.tier3Only && tier === "auto" ? "Tier 3" : undefined })),
    [tier],
  );

  // Tier 1 hides the engineering groups; a specific-process file keeps only the parameters those processes use.
  const fieldFilter = useCallback(
    (group: FieldGroupData, field: any) => {
      if (!group.tier3Only) return true;
      if (tier === "1") return false;
      if (processScope !== "specific") return true;
      return selectedProcesses.some((pk) => PROCESS_CATALOGUE.find((p) => p.key === pk)?.tier3Extra.includes(field.key));
    },
    [tier, processScope, selectedProcesses],
  );

  const downloadTemplate = async (fmt: "excel" | "csv") => {
    try {
      const processParam = processScope === "specific" && selectedProcesses.length ? selectedProcesses.join(",") : "all";
      const res = await api.get(`/emissions/template/${fmt}?tier=${tier}&process=${processParam}`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = fmt === "excel" ? "Scope1_Template.xlsx" : "scope1_template.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      toast.error("Template download failed.");
    }
  };

  const preSteps = [
    {
      label: "Upload mode",
      content: (
        <div className="flex flex-col gap-3">
          <h3 className="m-0 flex items-center gap-2 text-md font-bold text-text">
            <Settings className="size-4 text-brand-500" aria-hidden="true" /> Select calculation tier
          </h3>
          <p className="m-0 text-sm text-text-secondary">Choose how emissions will be calculated for each row in your file.</p>
          <RadioCardGroup label="Calculation tier" value={tier} onChange={setTier} options={TIER_OPTIONS} />
          <Banner tone="info">{TIER_NOTE[tier]}</Banner>
        </div>
      ),
    },
    {
      label: "Process scope",
      canNext: processScope !== "specific" || selectedProcesses.length > 0,
      content: (
        <div className="flex flex-col gap-3">
          <h3 className="m-0 flex items-center gap-2 text-md font-bold text-text">
            <Layers className="size-4 text-brand-500" aria-hidden="true" /> Process scope
          </h3>
          <p className="m-0 text-sm text-text-secondary">Does your file contain data for all process types, or a specific process?</p>
          <RadioCardGroup label="Process scope" value={processScope} onChange={setProcessScope} options={SCOPE_OPTIONS} columns="md:grid-cols-2" />
          {processScope === "specific" && (
            <div className="flex flex-col gap-2.5">
              <p className="m-0 text-sm font-semibold text-text">Select which processes are in your file:</p>
              <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(170px,1fr))]">
                {PROCESS_CATALOGUE.map((p) => (
                  <ProcessTile key={p.key} process={p} selected={selectedProcesses.includes(p.key)} onToggle={() => toggleProcess(p.key)} />
                ))}
              </div>
              {selectedProcesses.length === 0 && (
                <p role="status" className="m-0 flex items-center gap-1.5 text-sm font-medium text-warning-fg">
                  <TriangleAlert className="size-4" aria-hidden="true" /> Select at least one process type to continue.
                </p>
              )}
            </div>
          )}
        </div>
      ),
    },
  ];

  const fileExtras = (
    <>
      <div className="flex flex-col gap-2.5">
        <p className="m-0 text-sm font-medium text-text-secondary">Don't have a file? Download a pre-configured template:</p>
        <div className="flex flex-wrap gap-2.5">
          {TEMPLATES.map(({ fmt, icon: Icon, title, note }) => (
            <Button key={fmt} variant="secondary" className="h-auto min-w-0 flex-1 justify-start gap-3 px-4 py-3 text-left" onClick={() => downloadTemplate(fmt)}>
              <Icon className="size-5 shrink-0 text-brand-700" aria-hidden="true" />
              <span className="flex flex-col">
                <strong className="text-sm">{title}</strong>
                <small className="text-xs font-normal text-text-secondary">{note}</small>
              </span>
              <Download className="ml-auto size-4 shrink-0" aria-hidden="true" />
            </Button>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge tone={tier === "1" ? "info" : tier === "3" ? "success" : "brand"}>{tier === "1" ? "Tier 1" : tier === "3" ? "Tier 3" : "Auto-detect"}</Badge>
        <Badge>{processScope === "all" ? "All processes" : `${selectedProcesses.length} process${selectedProcesses.length !== 1 ? "es" : ""} selected`}</Badge>
      </div>
    </>
  );

  const mappingExtras = (
    <Field label="Default factor when not specified in file">
      <NativeSelect className={controlClass} value={globalFactor} onChange={(e) => setGlobalFactor(e.target.value)}>
        <option value="auto">Auto-detect from file</option>
        <option value="default">Force Standard (API Compendium)</option>
        <option value="custom">Force Custom Factors</option>
        <option value="specific">Force Tier 3 (site data)</option>
      </NativeSelect>
    </Field>
  );

  return (
    <ImportWizard
      title="Scope 1 Bulk Import"
      subtitle="Upload emissions data from CSV or Excel"
      fieldGroupsFor={fieldGroupsFor}
      scopeFor={() => "1"}
      preSteps={preSteps}
      fieldFilter={fieldFilter}
      fileExtras={fileExtras}
      mappingExtras={mappingExtras}
      extraForm={(form) => form.append("global_factor_type", globalFactor)}
      finalLabel="Submitted for review"
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default Scope1ImportWizard;
