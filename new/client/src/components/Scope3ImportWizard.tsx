import React from "react";
import { Download, FileSpreadsheet, Globe, Layers, Settings } from "lucide-react";
import { Button } from "../ui";
import ImportWizard, { ImportWizardMode } from "./import-wizard/ImportWizard";
import { FieldGroupData } from "./import-wizard/mapping";
import { t } from "../i18n";

// Scope 3 bulk import: activity-based or spend-based (EEIO / NAICS) column layouts on the shared wizard.
const FIELD_GROUPS_ACTIVITY: FieldGroupData[] = [
  {
    id: "identity",
    label: t("Location & Identity"),
    icon: Layers,
    fields: [
      { key: "date",          label: t("Date"),           required: true,  hint: t("Format: YYYY-MM-DD or YYYY-MM") },
      { key: "facility_name", label: t("Region / Facility"), required: true, hint: t("Must match an existing region in the system") },
      { key: "year",          label: t("Year"),          required: true,  hint: t("4-digit year (e.g. 2024) — required unless using a date column") },
      { key: "month",         label: t("Month"),         required: true,  hint: t("1–12 — required unless using a date column") },
    ],
  },
  {
    id: "classification",
    label: t("GHG Protocol Classification"),
    icon: Globe,
    fields: [
      { key: "category",      label: t("Category"),      required: true,  hint: t("e.g. 1, 2, 3... or 'Category 11'") },
      { key: "sub_category",  label: t("Sub Category"),  required: false, hint: t("Activity name as in the Scope 3 form (e.g. Truck Transport) to use its factor") },
      { key: "notes",         label: t("Description / Notes"), required: false, hint: t("Description of the emission source") },
    ],
  },
  {
    id: "measurement",
    label: t("Activity & Emissions"),
    icon: Settings,
    fields: [
      { key: "amount",          label: t("Activity Data Amount"), required: true, hint: t("Quantity of the activity") },
      { key: "unit",            label: t("Activity Unit"),        required: true, hint: t("e.g. kg, USD, miles") },
      { key: "emission_factor", label: t("Emission Factor"),      required: false, hint: t("kg CO2e per activity unit. If empty, the factor of the Sub Category activity in the Scope 3 form is used (unit must match).") },
      { key: "ef_unit",         label: t("EF Unit"),              required: false, hint: t("kg CO2e per unit (default), t CO2e per unit, or kg CO2e per $1,000") },
      { key: "co2e",            label: t("Total CO2e"),           required: false, hint: t("Provide direct CO2e to skip calculations") },
    ],
  }
];

const FIELD_GROUPS_EEIO: FieldGroupData[] = [
  {
    id: "identity",
    label: t("Location & Identity"),
    icon: Layers,
    fields: [
      { key: "date",          label: t("Date"),           required: true,  hint: t("Format: YYYY-MM-DD or YYYY-MM") },
      { key: "facility_name", label: t("Region / Facility"), required: true, hint: t("Must match an existing region in the system") },
      { key: "year",          label: t("Year"),          required: true,  hint: t("4-digit year") },
      { key: "month",         label: t("Month"),         required: true,  hint: "1–12" },
    ],
  },
  {
    id: "measurement",
    label: t("Spend & NAICS"),
    icon: Settings,
    fields: [
      { key: "naics_code",      label: t("NAICS Code"),      required: true,  hint: t("6-digit 2017 NAICS code (EPA supply chain factors)") },
      { key: "spend_usd",       label: t("Spend (USD)"),     required: true,  hint: t("Amount spent in USD") },
      { key: "notes",           label: t("Description / Notes"), required: false, hint: t("Optional supplier or purchase description") },
    ],
  }
];

const MODES: ImportWizardMode[] = [
  { value: "activity", label: t("Activity data") },
  { value: "eeio", label: t("Spend (EEIO / NAICS)") },
];
const groupsFor = (mode?: string): FieldGroupData[] => (mode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROIRY_ACTIVITY_FALLBACK(mode));
const FIELD_GROIRY_ACTIVITY_FALLBACK = (_mode?: string) => FIELD_GROUPS_ACTIVITY;

export interface Scope3ImportWizardProps {
  onClose: () => void;
  onUploadSuccess?: () => void;
}

export const Scope3ImportWizard: React.FC<Scope3ImportWizardProps> = ({ onClose, onUploadSuccess }) => {
  const downloadActivityTemplate = () => {
    const header = "facility_name,year,month,category,sub_category,amount,unit,emission_factor,ef_unit,notes";
    const sample = "Hassi Messaoud,2024,1,4,Truck Transport,10000,t-km,0.12841,kg,Crude trucking";
    const csv = `${header}\n${sample}\n`;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "scope3_activity_template.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const downloadEeioTemplate = () => {
    const header = "facility_name,year,month,naics_code,spend_usd,notes";
    const sample = "Hassi Messaoud,2024,1,211120,50000,Well drilling equipment procurement";
    const csv = `${header}\n${sample}\n`;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "scope3_spend_eeio_template.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const fileExtras = (currentMode?: string) => {
    const isEeio = currentMode === "eeio";
    return (
      <div className="flex flex-col gap-2.5">
        <p className="m-0 text-sm font-medium text-text-secondary">
          {t("Don't have a file? Download a sample CSV template:")}
        </p>
        <div className="flex flex-wrap gap-2.5">
          <Button
            variant="secondary"
            className="h-auto min-w-0 flex-1 justify-start gap-3 px-4 py-3 text-left"
            onClick={isEeio ? downloadEeioTemplate : downloadActivityTemplate}
          >
            <FileSpreadsheet className="size-5 shrink-0" aria-hidden="true" />
            <span className="flex flex-col">
              <strong className="text-sm">
                {isEeio ? t("Scope 3 Spend (EEIO) CSV Template") : t("Scope 3 Activity CSV Template")}
              </strong>
              <small className="text-xs font-normal opacity-80">
                {isEeio
                  ? t("Includes NAICS code and spend columns with sample entry")
                  : t("Includes GHG Protocol categories and activity columns with sample entry")}
              </small>
            </span>
            <Download className="ml-auto size-4 shrink-0" aria-hidden="true" />
          </Button>
        </div>
        <p className="m-0 text-xs text-text-secondary">
          {t("Have an export from another system? Upload it as it is: you can map custom headers to system fields.")}
        </p>
      </div>
    );
  };

  const overwriteLabel = (currentMode?: string) =>
    currentMode === "eeio"
      ? t("Overwrite existing Scope 3 spend records with matching region, month, and NAICS code")
      : t("Overwrite existing Scope 3 activity records with matching region, month, and category/activity");

  return (
    <ImportWizard
      title={t("Scope 3 Bulk Import")}
      subtitle={t("Upload value chain emissions data from CSV or Excel")}
      modes={MODES}
      fieldGroupsFor={groupsFor}
      scopeFor={(mode) => (mode === "eeio" ? "3_eeio" : "3")}
      fileExtras={fileExtras}
      overwriteLabel={overwriteLabel}
      overwriteHint={t("If unchecked, duplicate records will be skipped to prevent double-counting.")}
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default Scope3ImportWizard;
