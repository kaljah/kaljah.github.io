import React, { useCallback, useMemo, useState } from "react";
import { Download, File as FileIcon, FileSpreadsheet, Settings } from "lucide-react";
import { Button, Field, NativeSelect, RadioCardGroup } from "../ui";
import api from "../api";
import { PROCESS_TYPES } from "../utils/EmissionFactors";
import { useToast } from "./Toast";
import ImportWizard from "./import-wizard/ImportWizard";
import { controlClass, FieldGroupData, MappingField } from "./import-wizard/mapping";
import { TEMPLATES, TemplateField } from "./column-mapping/templates";
import { t as tr } from "../i18n";

const TITLES: Record<string, string> = {
  sources: "Equipment",
  custom_factors: "Custom Factors",
  production: "Production Data",
  mitigation: "Mitigation Projects",
};

// Server scope code for each wizard type; the other types upload under their own name.
const SCOPE_OF: Record<string, string> = { activity: "1", activity_scope2: "2", activity_scope3: "3" };

// Sample row appended to the client-side CSV template of each non-emissions type.
const SAMPLE_ROW: Record<string, string> = {
  custom_factors: "Specialized Generator Gas,Natural Gas,MMBtu,53.06,0.001,0.0001,0,5,50,150,combustion",
  production: "Hassi Messaoud,Exploration & Production,Production,Bir Berkine,2024,1,50000,bbl,12000,mscf",
  mitigation: "Hassi Messaoud,Solar Farm A,REC,2024,1500,Active,2024-01-01,,500000,Solar panel installation",
  sources: "Exploration & Production,Production,Hassi Messaoud,Bir Berkine,Combustion Unit A,EQ-001,combustion,Natural Gas,5 MW,2015-06-01,Active",
  activity_scope2: "Hassi Messaoud,2024,1,Algerian National Grid,500,MWh,electricity,",
  activity_scope3: "Hassi Messaoud,2024,1,4,Truck Transport,10000,t-km,0.12841,kg,,Crude trucking",
  facilities: "Hassi R'Mel,Laghouat,HRM-01,100,operated,Exploration & Production,Production,Block A,Laghouat,Operational Control,Details here,Upstream,33.8,3.2",
};

// Scope 1 columns shown before any Tier 3 inputs.
const GENERAL_FIELDS: string[] = [
  "activity", "division", "facility_id", "facility_name", "field", "group", "year", "month", "date", "process", "process_type",
  "fuel", "fuel_type", "amount", "quantity", "unit", "factor_type", "equipment", "equipment_id", "equipment_name",
];

// Tier 3 inputs each calculator reads (same field names as the Scope 1 templates)
const COMP: string[] = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "co2_mol", "n2_mol"];
const VENT: string[] = ["vent_method", "disposition", "ch4_content", "co2_content"];
const FLARE: string[] = ["flare_type", "control_efficiency", ...COMP];
const PROCESS_FIELDS: Record<string, string[]> = {
  combustion: ["hhv", ...COMP, "combustion_efficiency", "operating_temperature", "temp_unit", "operating_pressure", "press_unit", "z_factor"],
  flaring: FLARE,
  routine_flaring: FLARE,
  non_routine_flaring: FLARE,
  safety_flaring: FLARE,
  venting: [...VENT, "blowdown_pressure", "blowdown_events", "blowdown_temp", "blowdown_temp_unit", "blowdown_press_unit", "z_factor"],
  tank_flashing: ["tank_gor", "tank_ch4_content", "tank_control_eff", "tank_api_gravity"],
  pneumatic: ["pneu_count", "pneu_bleed_rate", "pneu_bleed_unit", "pneu_hours", "pneu_ch4_content", "operating_hours"],
  fugitive: ["fugitive_method", "component_type", "service", "m21_below_count", "m21_above_count", "operating_hours"],
  completions: ["comp_method", "comp_rate", "comp_rate_unit", "comp_duration", "comp_flare_eff", "ch4_content", "co2_content"],
  unloading: ["unload_depth", "unload_diam", "unload_press", "unload_freq", "unload_flare_eff", "ch4_content", "co2_content"],
  drilling: ["mud_type"],
  dehydrator: VENT,
  vented_gas: VENT,
  agr: ["agr_co2_in", "agr_co2_out", "agr_ch4_in", "agr_ch4_slip", "agr_control_eff"],
  stoichiometry: ["carbon_content"],
};

const TIER_OPTIONS = [
  { value: "1", title: tr("Tier 1 (Default Factors)"), description: tr("Basic calculation using industry defaults.") },
  { value: "3", title: tr("Tier 3 (Engineering)"), description: tr("Advanced calculation using process specifications.") },
];
const SCOPE_OPTIONS = [
  { value: "all", title: tr("All Processes"), description: tr("Upload data for various process types together.") },
  { value: "specific", title: tr("Choose by Process"), description: tr("Upload data for a single specific process.") },
];

const asField = (f: TemplateField): MappingField => ({ key: f.id, label: f.label, required: f.required, hint: f.hint || "" });

/** Required and optional columns for a wizard type; Tier 3 inputs are added for emissions data. */
function fieldsFor(type: string, tier: string, processScope: string, process: string): MappingField[] {
  let fields: MappingField[] = (TEMPLATES[type] || []).map(asField);
  if (type === "activity") {
    fields = fields.filter((f) => GENERAL_FIELDS.includes(f.key));
    if (tier === "3") {
      const allowed = processScope === "all" ? [...new Set(Object.values(PROCESS_FIELDS).flat())] : PROCESS_FIELDS[process] || [];
      allowed.forEach((key) => {
        if (!fields.some((f) => f.key === key)) {
          fields.push({ key, label: key.replace(/_/g, " ").toUpperCase(), hint: tr("Tier 3 specific"), required: false });
        }
      });
    }
  }
  return fields;
}

export interface ColumnMappingWizardProps {
  onClose: () => void;
  onUploadSuccess?: () => void;
  type?: string;
}

/** Generic bulk importer for emissions rows and master data; `type` picks the column set and server scope. */
export const ColumnMappingWizard: React.FC<ColumnMappingWizardProps> = ({ onClose, onUploadSuccess, type = "activity" }) => {
  const toast = useToast();
  const [tier, setTier] = useState<string>("3");
  const [processScope, setProcessScope] = useState<string>("all");
  const [process, setProcess] = useState<string>("flaring");
  const [globalFactor, setGlobalFactor] = useState<string>("auto");
  const isEmissions = type === "activity";

  const fieldGroupsFor = useCallback((): FieldGroupData[] => {
    const fields = fieldsFor(type, tier, processScope, process);
    const groups: FieldGroupData[] = [
      { id: "required", label: tr("Required fields"), icon: Settings, fields: fields.filter((f) => f.required) },
      { id: "optional", label: tr("Optional fields"), icon: Settings, fields: fields.filter((f) => !f.required) },
    ];
    return groups.filter((g) => g.fields.length > 0);
  }, [type, tier, processScope, process]);

  const downloadTemplate = async (fmt: "excel" | "csv") => {
    if (isEmissions) {
      try {
        const res = await api.get(`/emissions/template/${fmt}?tier=${tier}&process=${processScope === "specific" ? process : "all"}`, { responseType: "blob" });
        const url = URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement("a");
        a.href = url;
        a.download = fmt === "excel" ? "GHG_Emissions_Template_v2.xlsx" : "emissions_template.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
      } catch {
        toast.error(tr("Template download failed."));
      }
      return;
    }
    const header = (TEMPLATES[type] || []).map((t) => t.id).join(",");
    const csv = SAMPLE_ROW[type] ? `${header}\n${SAMPLE_ROW[type]}` : header;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${type}_import_template.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const preSteps = useMemo(
    () =>
      isEmissions
        ? [
            {
              label: tr("Configuration"),
              content: (
                <div className="flex flex-col gap-5">
                  <section className="flex flex-col gap-3">
                    <h3 className="m-0 text-md font-bold text-text">{tr("Calculation tier")}</h3>
                    <RadioCardGroup label={tr("Calculation tier")} value={tier} onChange={setTier} options={TIER_OPTIONS} columns="md:grid-cols-2" />
                  </section>
                  <section className="flex flex-col gap-3">
                    <h3 className="m-0 text-md font-bold text-text">{tr("Process scope")}</h3>
                    <RadioCardGroup label={tr("Process scope")} value={processScope} onChange={setProcessScope} options={SCOPE_OPTIONS} columns="md:grid-cols-2" />
                    {processScope === "specific" && (
                      <Field label={tr("Select process type")}>
                        <NativeSelect className={controlClass} value={process} onChange={(e) => setProcess(e.target.value)}>
                          {Object.entries(PROCESS_TYPES).map(([k, v]) => (
                            <option key={k} value={k}>
                              {typeof v === "string" ? v : (v as any)?.label || k}
                            </option>
                          ))}
                        </NativeSelect>
                      </Field>
                    )}
                  </section>
                </div>
              ),
            },
          ]
        : [],
    [isEmissions, tier, processScope, process],
  );

  const fileExtras = (
    <div className="flex flex-col gap-2.5">
      <p className="m-0 text-sm font-medium text-text-secondary">{tr("Don't have a file yet? Start from our template:")}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {isEmissions && (
          <Button variant="secondary" className="h-auto justify-start gap-3 px-4 py-3 text-left" onClick={() => downloadTemplate("excel")}>
            <FileSpreadsheet className="size-5 shrink-0 text-brand-700" aria-hidden="true" />
            <span className="flex flex-col">
              <strong className="text-sm">{tr("Excel Template")}</strong>
              <small className="text-xs font-normal text-text-secondary">{tr("With dropdowns, sample data & engineering sheets")}</small>
            </span>
            <Download className="ml-auto size-4 shrink-0" aria-hidden="true" />
          </Button>
        )}
        <Button variant="secondary" className="h-auto justify-start gap-3 px-4 py-3 text-left" onClick={() => downloadTemplate("csv")}>
          <FileIcon className="size-5 shrink-0 text-brand-700" aria-hidden="true" />
          <span className="flex flex-col">
            <strong className="text-sm">{tr("CSV Template")}</strong>
            <small className="text-xs font-normal text-text-secondary">{tr("Lightweight flat file for maximum performance")}</small>
          </span>
          <Download className="ml-auto size-4 shrink-0" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );

  const mappingExtras = (
    <Field label={tr("Default factor type when not specified in file")}>
      <NativeSelect className={controlClass} value={globalFactor} onChange={(e) => setGlobalFactor(e.target.value)}>
        <option value="auto">{tr("Auto-detect from file")}</option>
        <option value="default">{tr("Force Standard (API Compendium)")}</option>
        <option value="custom">{tr("Force Custom Factors")}</option>
      </NativeSelect>
    </Field>
  );

  const facilities = type === "facilities";
  return (
    <ImportWizard
      title={`Import ${TITLES[type] || (facilities ? "Regions" : "Emissions Data")}`}
      subtitle={tr("Upload a CSV or Excel file to bulk-import your records")}
      fieldGroupsFor={fieldGroupsFor}
      scopeFor={() => SCOPE_OF[type] || type}
      preSteps={preSteps}
      fileExtras={fileExtras}
      mappingExtras={mappingExtras}
      extraForm={(form) => form.append("global_factor_type", globalFactor)}
      finalLabel="Processing"
      overwriteLabel={facilities ? "Overwrite existing Regions with the same name" : "Overwrite existing records with matching facility, date, and source"}
      overwriteHint={facilities ? "If unchecked, duplicate regions will be skipped with an error." : "If unchecked, duplicate records will be skipped to prevent double-counting."}
      reviewable={type in SCOPE_OF}
      regionAccess={false}
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default ColumnMappingWizard;
