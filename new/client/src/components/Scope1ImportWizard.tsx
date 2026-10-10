import React, { useCallback, useState } from "react";
import { Activity, Container, Cpu, Download, Droplets, File as FileIcon, FileSpreadsheet, Flame, Layers, Settings, Wind, Zap } from "lucide-react";
import { Badge, Banner, Button, RadioCardGroup } from "../ui";
import api from "../api";
import { useToast } from "./Toast";
import ImportWizard from "./import-wizard/ImportWizard";
import { FieldGroupData } from "./import-wizard/mapping";
import { cn } from "../ui/cn";
import { t } from "../i18n";

// ─── Process catalogue (keys are the server's Scope 1 process types) ─────────
const COMP = ["c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","co2_mol","n2_mol"];

export interface ProcessCatalogueItem {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string; [key: string]: any }>;
  tier3Extra: string[];
}

const PROCESS_CATALOGUE: ProcessCatalogueItem[] = [
  { key: "combustion",    label: t("Combustion"),             icon: Flame,     tier3Extra: ["hhv", ...COMP, "combustion_efficiency", "operating_temperature", "temp_unit", "operating_pressure", "press_unit", "z_factor"] },
  { key: "flaring",       label: t("Flaring"),                icon: Flame,     tier3Extra: ["flare_type", "combustion_efficiency", "destruction_efficiency", "control_efficiency", ...COMP] },
  { key: "venting",       label: t("Venting"),                icon: Wind,      tier3Extra: ["vent_method", "disposition", "ch4_content", "co2_content"] },
  { key: "blowdown",      label: t("Blowdowns"),              icon: Zap,       tier3Extra: ["blowdown_pressure", "blowdown_events", "blowdown_temp", "blowdown_temp_unit", "blowdown_press_unit", "z_factor", "ch4_content", "co2_content"] },
  { key: "tank_flashing", label: t("Tank Flashing"),          icon: Container, tier3Extra: ["tank_gor", "tank_ch4_content", "tank_control_eff", "tank_api_gravity"] },
  { key: "pneumatic",     label: t("Pneumatic Devices"),      icon: Cpu,       tier3Extra: ["pneu_count", "pneu_bleed_rate", "pneu_bleed_unit", "pneu_hours", "pneu_ch4_content"] },
  { key: "fugitive",      label: t("Equipment Leaks"),        icon: Droplets,  tier3Extra: ["fugitive_method", "component_type", "service", "m21_below_count", "m21_above_count"] },
  { key: "completions",   label: t("Well Completions"),       icon: Layers,    tier3Extra: ["comp_method", "comp_rate", "comp_rate_unit", "comp_duration", "comp_flare_eff", "ch4_content", "co2_content"] },
  { key: "unloading",     label: t("Liquids Unloading"),      icon: Layers,    tier3Extra: ["unload_depth", "unload_diam", "unload_press", "unload_freq", "unload_flare_eff", "ch4_content", "co2_content"] },
  { key: "drilling",      label: t("Drilling"),               icon: Layers,    tier3Extra: ["mud_type"] },
  { key: "dehydrator",    label: t("Dehydrators"),            icon: Droplets,  tier3Extra: ["vent_method", "ch4_content", "co2_content"] },
  { key: "agr",           label: t("AGR / Acid Gas Removal"), icon: Activity,  tier3Extra: ["agr_co2_in", "agr_co2_out", "agr_ch4_in", "agr_ch4_slip", "agr_control_eff"] },
];

// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS: FieldGroupData[] = [
  {
    id: "identity",
    label: t("Location & Identity"),
    icon: Layers,
    fields: [
      { key: "date",          label: t("Date"),           required: true,  hint: t("Format: YYYY-MM-DD or YYYY-MM (or map Year and Month)") },
      { key: "facility_name", label: t("Region / Facility"), required: true, hint: t("Must match an existing region in the system") },
      { key: "activity",      label: t("Activity"),       required: false, hint: t("e.g. Exploration & Production") },
      { key: "division",      label: t("Division"),       required: false, hint: t("e.g. Production, Association") },
      { key: "field",         label: t("Field"),          required: false, hint: t("e.g. Bir Berkine") },
      { key: "group",         label: t("Emission Source"),required: false, hint: t("Logical grouping for this emission source") },
      { key: "equipment",     label: t("Equipment Name"), required: false, hint: t("Name of the piece of equipment") },
      { key: "equipment_id",  label: t("Equipment ID"),   required: false, hint: t("Unique identifier for the equipment (duplicate check)") },
    ],
  },
  {
    id: "measurement",
    label: t("Measurement"),
    icon: Activity,
    fields: [
      { key: "process",       label: t("Process Type"),  required: true,  hint: t("e.g. combustion, flaring, venting (keys or the form's names)") },
      { key: "fuel",          label: t("Activity / Fuel"), required: false, hint: t("Emission factor name as listed in the manual form (default and custom rows)") },
      { key: "quantity",      label: t("Quantity"),      required: true,  hint: t("Activity of the month") },
      { key: "unit",          label: t("Unit"),          required: true,  hint: t("e.g. scf, Mscf, m3, bbl, gal, tonne, days, devices") },
      { key: "factor_type",   label: t("Factor Type"),   required: false, hint: t("default (API Compendium) | custom (saved factor) | specific (Tier 3)") },
      { key: "operating_hours", label: t("Operating Hours"), required: false, hint: t("Hours in the month: required for pneumatic controller factors and equipment leaks") },
      { key: "year",          label: t("Year"),          required: true,  hint: t("4-digit year (e.g. 2024) — required unless using a date column") },
      { key: "month",         label: t("Month"),         required: true,  hint: t("1–12 — required unless using a date column (YYYY-MM)") },
    ],
  },
  {
    id: "gas_composition",
    label: t("Gas Composition (Tier 3)"),
    icon: Settings,
    tier3Only: true,
    fields: [
      { key: "c1",      label: t("C1 (Methane) mol%"),  required: false, hint: t("Methane mole %") },
      { key: "c2",      label: t("C2 (Ethane) mol%"),   required: false, hint: t("Ethane mole %") },
      { key: "c3",      label: t("C3 (Propane) mol%"),  required: false, hint: t("Propane mole %") },
      { key: "c4",      label: t("C4 mol%"),            required: false, hint: t("Butane mole %") },
      { key: "c5",      label: t("C5 mol%"),            required: false, hint: t("Pentane mole %") },
      { key: "c6",      label: t("C6 mol%"),            required: false, hint: t("Hexane mole %") },
      { key: "c7",      label: t("C7 mol%"),            required: false, hint: "" },
      { key: "c8",      label: t("C8 mol%"),            required: false, hint: "" },
      { key: "c9",      label: t("C9 mol%"),            required: false, hint: "" },
      { key: "c10",     label: t("C10+ mol%"),          required: false, hint: "" },
      { key: "co2_mol", label: t("CO₂ mol%"),           required: false, hint: t("CO2 mole % of the gas") },
      { key: "n2_mol",  label: t("N₂ mol%"),            required: false, hint: t("Nitrogen mole %") },
      { key: "hhv",     label: "HHV",               required: false, hint: t("Higher heating value (Btu/scf for gas)") },
      { key: "ch4_content", label: t("CH4 Content %"),  required: false, hint: t("CH4 mole % when the full composition is not given") },
      { key: "co2_content", label: t("CO2 Content %"),  required: false, hint: t("CO2 mole % when the full composition is not given") },
    ],
  },
  {
    id: "combustion_params",
    label: t("Combustion / Flaring Parameters (Tier 3)"),
    icon: Flame,
    tier3Only: true,
    fields: [
      { key: "combustion_efficiency", label: t("Combustion Efficiency %"), required: false, hint: t("Combustion: defaults to 99.5 %. Flaring: % of carbon converted to CO2 (blank = 96.5 %)") },
      { key: "destruction_efficiency", label: t("Flare Destruction Efficiency %"), required: false, hint: t("% of CH4 destroyed (blank = 98 %, 99.5 % at Downstream facilities)") },
      { key: "flare_type",           label: t("Flare Type"),             required: false, hint: t("elevated | enclosed_ground | air_assisted | steam_assisted") },
      { key: "control_efficiency",   label: t("Flare Control Efficiency %"), required: false, hint: t("Flare destruction efficiency %") },
      { key: "operating_temperature",label: t("Metering Temp"),          required: false, hint: t("Only for volumes in m3 / cf read at metering conditions") },
      { key: "temp_unit",            label: t("Temp Unit"),              required: false, hint: t("C or F") },
      { key: "operating_pressure",   label: t("Metering Pressure"),      required: false, hint: t("Only for volumes in m3 / cf read at metering conditions") },
      { key: "press_unit",           label: t("Press Unit"),             required: false, hint: t("psig, psia, kPa, barg, bara") },
      { key: "z_factor",             label: t("Z Factor"),               required: false, hint: t("Gas compressibility factor") },
    ],
  },
  {
    id: "vent_params",
    label: t("Venting / Dehydrator / Blowdown (Tier 3)"),
    icon: Wind,
    tier3Only: true,
    fields: [
      { key: "vent_method",         label: t("Vent Method"),          required: false, hint: t("volume: the quantity is the measured gas volume (scf, Mcf, MMscf, m3)") },
      { key: "disposition",         label: t("Disposition"),          required: false, hint: t("vented (default) or flared") },
      { key: "blowdown_pressure",   label: t("Blowdown Pressure"),    required: false, hint: t("Vessel pressure before blowdown") },
      { key: "blowdown_events",     label: t("Blowdown Events"),      required: false, hint: t("Events in the month") },
      { key: "blowdown_temp",       label: t("Blowdown Temp"),        required: false, hint: t("Gas temperature in the vessel") },
      { key: "blowdown_temp_unit",  label: t("Blowdown Temp Unit"),   required: false, hint: "F | C | K" },
      { key: "blowdown_press_unit", label: t("Blowdown Press Unit"),  required: false, hint: t("psig | psia | kPa") },
    ],
  },
  {
    id: "pneumatic_params",
    label: t("Pneumatic Parameters (Tier 3)"),
    icon: Cpu,
    tier3Only: true,
    fields: [
      { key: "pneu_count",       label: t("Pneumatic Count"),      required: false, hint: t("Number of devices") },
      { key: "pneu_bleed_rate",  label: t("Bleed Rate"),           required: false, hint: t("Measured bleed rate per device") },
      { key: "pneu_bleed_unit",  label: t("Bleed Rate Unit"),      required: false, hint: t("scf or m3 (per hour)") },
      { key: "pneu_hours",       label: t("Pneumatic Hours"),      required: false, hint: t("Operating hours in the month") },
      { key: "pneu_ch4_content", label: t("Supply Gas CH4 %"),     required: false, hint: t("CH4 mole % of the supply gas") },
    ],
  },
  {
    id: "tank_params",
    label: t("Tank Parameters (Tier 3)"),
    icon: Container,
    tier3Only: true,
    fields: [
      { key: "tank_gor",            label: t("Tank GOR"),             required: false, hint: t("Flash gas-to-oil ratio (scf/bbl)") },
      { key: "tank_ch4_content",    label: t("Tank CH4 Content %"),   required: false, hint: t("CH4 mole % of the flash gas") },
      { key: "tank_control_eff",    label: t("Tank Control Eff %"),   required: false, hint: t("Vapour control efficiency") },
      { key: "tank_api_gravity",    label: t("Tank API Gravity"),     required: false, hint: t("API gravity of the stored liquid") },
    ],
  },
  {
    id: "fugitive_params",
    label: t("Equipment Leak Parameters (Tier 3)"),
    icon: Wind,
    tier3Only: true,
    fields: [
      { key: "fugitive_method", label: t("Leak Method"),       required: false, hint: t("screening | correlation | ogi | measurement") },
      { key: "component_type",  label: t("Component Type"),    required: false, hint: t("valve | connector | flange | open_ended_line | pump_seal | other") },
      { key: "service",         label: t("Service"),           required: false, hint: t("gas | light_oil | heavy_oil | water_oil") },
      { key: "m21_below_count", label: t("Screened < 10,000 ppmv"), required: false, hint: t("Components screened below 10,000 ppmv") },
      { key: "m21_above_count", label: t("Screened ≥ 10,000 ppmv"), required: false, hint: t("Components screened at or above 10,000 ppmv") },
    ],
  },
  {
    id: "well_params",
    label: t("Well / Drilling Parameters (Tier 3)"),
    icon: Layers,
    tier3Only: true,
    fields: [
      { key: "mud_type",          label: t("Mud Type"),           required: false, hint: t("water_based | oil_based | synthetic (quantity in drilling days)") },
      { key: "comp_method",       label: t("Completion Method"),  required: false, hint: t("metered_volume | rate_duration | gor_liquid") },
      { key: "comp_rate",         label: t("Flowback Rate"),      required: false, hint: t("Gas rate during flowback") },
      { key: "comp_rate_unit",    label: t("Flowback Rate Unit"), required: false, hint: t("Mcf/hr (default) | Mcf/day | scf/hr | m3/hr") },
      { key: "comp_duration",     label: t("Flowback Duration"),  required: false, hint: t("Hours") },
      { key: "comp_flare_eff",    label: t("Completion Flare %"), required: false, hint: t("% of flowback gas flared") },
      { key: "unload_depth",      label: t("Well Depth (ft)"),    required: false, hint: t("Liquids unloading") },
      { key: "unload_diam",       label: t("Casing Diameter (in)"), required: false, hint: t("Liquids unloading") },
      { key: "unload_press",      label: t("Shut-in Pressure (psig)"), required: false, hint: t("Liquids unloading") },
      { key: "unload_freq",       label: t("Unloading Events"),   required: false, hint: t("Events in the month") },
      { key: "unload_flare_eff",  label: t("Unloading Flare %"),  required: false, hint: t("% of unloading gas flared") },
    ],
  },
  {
    id: "dehydrator_agr",
    label: t("AGR Parameters (Tier 3)"),
    icon: Droplets,
    tier3Only: true,
    fields: [
      { key: "agr_co2_in",        label: t("AGR CO₂ In %"),       required: false, hint: t("CO2 mole % in the feed") },
      { key: "agr_co2_out",       label: t("AGR CO₂ Out %"),      required: false, hint: t("CO2 mole % in the sweet gas") },
      { key: "agr_ch4_in",        label: t("AGR CH₄ In %"),       required: false, hint: t("CH4 mole % in the feed") },
      { key: "agr_ch4_slip",      label: t("AGR CH₄ Slip"),       required: false, hint: t("Fraction of inlet CH4 (e.g. 0.001)") },
      { key: "agr_control_eff",   label: t("AGR Control Eff %"),  required: false, hint: t("Acid gas destruction efficiency") },
    ],
  },
  {
    id: "uncertainty",
    label: t("Uncertainty Overrides"),
    icon: Settings,
    fields: [
      { key: "user_unc_co2", label: t("User Uncertainty CO₂ %"), required: false, hint: t("Override the system uncertainty for CO2") },
      { key: "user_unc_ch4", label: t("User Uncertainty CH₄ %"), required: false, hint: t("Override the system uncertainty for CH4") },
      { key: "user_unc_n2o", label: t("User Uncertainty N₂O %"), required: false, hint: t("Override the system uncertainty for N2O") },
    ],
  },
];

const TIER_OPTIONS = [
  { value: "1", title: t("Tier 1 — Standard"), badge: <Badge tone="info">{t("Minimum fields")}</Badge>, description: t("Every row uses the API Compendium default factors (the file's factor_type column is ignored). Needs fuel, quantity and unit.") },
  { value: "2", title: t("Tier 2 — Custom / Site Factors"), badge: <Badge tone="info">{t("Site data")}</Badge>, description: t("Every row uses your saved custom factors (Manage Data › Custom Factors), or a catalog fuel with your measured HHV / density.") },
  { value: "3", title: t("Tier 3 — Engineering"), badge: <Badge tone="success">{t("Full precision")}</Badge>, description: t("Every row is calculated from site data: gas composition (C1–C10), operating conditions and process parameters.") },
  { value: "auto", title: t("Per row — mixed tiers"), badge: <Badge tone="brand">{t("Recommended")}</Badge>, description: t("Mixes Tier 1, 2 and 3 rows in one file. Each row's factor_type column (default / custom / specific) selects its tier.") },
];

const TIER_NOTE: Record<string, string> = {
  "1": "Tier 1 only requires: Region, Date, Process, Fuel, Quantity, Unit.",
  "2": "Tier 2 requires the Tier 1 fields with factor_type custom and either a saved custom factor name in Fuel, or a catalog fuel with hhv (and hhv_unit) / density.",
  "3": "Tier 3 requires all Tier 1 fields plus gas composition and process engineering parameters.",
  auto: "Auto-detect is ideal for a mix of sources: each row's factor_type column selects Tier 1, 2 or 3.",
};

// the tier chosen in step 1 is the one the server applies (it used to be a second, independent
// "Default factor" select in the mapping step: choosing Tier 3 in step 1 still imported per row)
const TIER_TO_FACTOR: Record<string, string> = { "1": "default", "2": "custom", "3": "specific", auto: "auto" };
const TIER_LABEL: Record<string, string> = {
  "1": "Tier 1 for every row",
  "2": "Tier 2 for every row",
  "3": "Tier 3 for every row",
  auto: "Tier per row (factor_type column)",
};

const TEMPLATES = [
  { fmt: "excel" as const, icon: FileSpreadsheet, title: t("Excel template"), recommended: true, note: "Dropdowns for your facilities, processes, and the fuels and units of each process; examples and a reference sheet" },
  { fmt: "csv" as const, icon: FileIcon, title: t("CSV template"), recommended: false, note: "Same columns, for exports from other systems. Example rows dated EXAMPLE are never imported." },
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

/** Scope 1 bulk import: pick the calculation tier, then the shared file, check and column-mapping steps. */
export const Scope1ImportWizard: React.FC<Scope1ImportWizardProps> = ({ onClose, onUploadSuccess }) => {
  const toast = useToast();
  const [tier, setTier] = useState<string>("auto");
  // processes whose Tier 3 input columns the template adds (none selected = every process)
  const [selectedProcesses, setSelectedProcesses] = useState<string[]>([]);
  const [optionalCols, setOptionalCols] = useState<boolean>(false);

  const toggleProcess = (key: string) => setSelectedProcesses((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));

  const fieldGroupsFor = useCallback(
    (): FieldGroupData[] => FIELD_GROUPS.map((g) => ({ ...g, badge: g.tier3Only && tier === "auto" ? "Tier 3" : undefined })),
    [tier],
  );

  // Tier 1 and Tier 2 files have no engineering inputs
  const fieldFilter = useCallback((group: FieldGroupData) => !(group.tier3Only && (tier === "1" || tier === "2")), [tier]);

  const downloadTemplate = async (fmt: "excel" | "csv") => {
    try {
      const processParam = selectedProcesses.length ? selectedProcesses.join(",") : "all";
      const res = await api.get(`/emissions/template/${fmt}?tier=${tier}&process=${processParam}${optionalCols ? "&optional=1" : ""}`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      const stem = `scope1_template_${tier === "auto" ? "per_row" : `tier${tier}`}`;
      a.download = fmt === "excel" ? `${stem}.xlsx` : `${stem}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      toast.error(t("Template download failed."));
    }
  };

  const preSteps = [
    {
      label: t("Calculation"),
      content: (
        <div className="flex flex-col gap-3">
          <h3 className="m-0 flex items-center gap-2 text-md font-bold text-text">
            <Settings className="size-4 text-brand-500" aria-hidden="true" />{" "}{t("Select calculation tier")}
          </h3>
          <p className="m-0 text-sm text-text-secondary">{t("Choose how emissions will be calculated for each row in your file.")}</p>
          <RadioCardGroup label={t("Calculation tier")} value={tier} onChange={setTier} options={TIER_OPTIONS} columns="md:grid-cols-2" />
          <Banner tone="info">{TIER_NOTE[tier]}</Banner>
        </div>
      ),
    },
  ];

  const fileExtras = (
    <>
      <div className="flex flex-col gap-2.5">
        <p className="m-0 text-sm font-medium text-text-secondary">{t("Don't have a file? Download a template made for")}{" "}{TIER_LABEL[tier]}:</p>
        {(tier === "3" || tier === "auto") && (
          <div className="flex flex-col gap-2">
            <p className="m-0 text-xs text-text-secondary">{t("Add the Tier 3 input columns for")}{selectedProcesses.length ? "" : t(" every process")}:</p>
            <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(170px,1fr))]">
              {PROCESS_CATALOGUE.map((p) => (
                <ProcessTile key={p.key} process={p} selected={selectedProcesses.includes(p.key)} onToggle={() => toggleProcess(p.key)} />
              ))}
            </div>
          </div>
        )}
        <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
          <input type="checkbox" className="size-4 accent-brand-500" checked={optionalCols} onChange={(e) => setOptionalCols(e.target.checked)} />
          {t("Include optional columns (activity, division, field, metering conditions, uncertainty)")}
        </label>
        <div className="flex flex-wrap gap-2.5">
          {TEMPLATES.map(({ fmt, icon: Icon, title, note, recommended }) => (
            <Button
              key={fmt}
              variant={recommended ? "primary" : "secondary"}
              className="h-auto min-w-0 flex-1 justify-start gap-3 px-4 py-3 text-left"
              onClick={() => downloadTemplate(fmt)}
            >
              <Icon className="size-5 shrink-0" aria-hidden="true" />
              <span className="flex flex-col">
                <strong className="text-sm">
                  {title}
                  {recommended && t(" (recommended)")}
                </strong>
                <small className="text-xs font-normal opacity-80">{note}</small>
              </span>
              <Download className="ml-auto size-4 shrink-0" aria-hidden="true" />
            </Button>
          ))}
        </div>
        <p className="m-0 text-xs text-text-secondary">
          {t("Have an export from another system? Upload it as it is: you match its columns once and can save that mapping for the next file.")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge tone={tier === "3" ? "success" : tier === "auto" ? "brand" : "info"}>{TIER_LABEL[tier]}</Badge>
      </div>
    </>
  );

  const mappingExtras = (
    <p className="m-0 text-sm text-text-secondary">
      {t("Calculation:")}{" "}<strong className="text-text">{TIER_LABEL[tier]}</strong>{" "}{t("(chosen in the first step)")}
    </p>
  );

  return (
    <ImportWizard
      title={t("Scope 1 Bulk Import")}
      subtitle={t("Upload emissions data from CSV or Excel")}
      fieldGroupsFor={fieldGroupsFor}
      scopeFor={() => "1"}
      preSteps={preSteps}
      fieldFilter={fieldFilter}
      fileExtras={fileExtras}
      mappingExtras={mappingExtras}
      extraForm={(form) => form.append("global_factor_type", TIER_TO_FACTOR[tier] || "auto")}
      optionsKey={tier}
      checkBeforeImport
      alwaysShownKeys={["fuel"]}
      finalLabel="Submitted for review"
      overwriteLabel="Replace existing records. A row for the same facility, month, process, fuel and equipment as a record already in the platform replaces it, and that record goes back to Pending review. Unticked, such rows are skipped and listed as duplicates."
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default Scope1ImportWizard;
