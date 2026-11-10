import React from "react";
import { Activity, Download, FileSpreadsheet, Layers } from "lucide-react";
import { Button } from "../ui";
import ImportWizard from "./import-wizard/ImportWizard";
import { FieldGroupData } from "./import-wizard/mapping";
import { t } from "../i18n";

// Scope 2 (purchased electricity, steam and CHP) bulk import: the column layout plus the shared wizard.
const FIELD_GROUPS: FieldGroupData[] = [
  {
    id: "identity",
    label: t("Location & Identity"),
    icon: Layers,
    fields: [
      { key: "date",          label: t("Date"),           required: true,  hint: t("Format: YYYY-MM-DD or YYYY-MM") },
      { key: "facility_name", label: t("Region / Facility"), required: true, hint: t("Must match an existing region in the system") },
      { key: "activity",      label: t("Activity"),       required: false, hint: t("e.g. Exploration & Production") },
      { key: "division",      label: t("Division"),       required: false, hint: t("e.g. Production, Association") },
      { key: "field",         label: t("Field"),          required: false, hint: t("e.g. Sector Alpha-1") },
    ],
  },
  {
    id: "measurement",
    label: t("Measurement & Type"),
    icon: Activity,
    fields: [
      { key: "source_type",   label: t("Source Type"),   required: false, hint: t("electricity, indirect_steam, or cogen_allocation") },
      { key: "grid_region",   label: t("Grid Region"),   required: false, hint: t("Grid name as listed on the Scope 2 form (e.g. Algerian National Grid). Required for electricity unless a supplier factor is given.") },
      { key: "factor",        label: t("Supplier Factor"), required: false, hint: t("Electricity: supplier / contract factor in kg CO2e/kWh (used when the grid is not listed). Steam: boiler factor in kg CO2/MMBtu") },
      { key: "consumption",   label: t("Consumption"),   required: true,  hint: t("Amount of electricity/steam purchased") },
      { key: "unit",          label: t("Unit"),          required: true,  hint: t("Electricity: kWh, MWh, GWh. Steam: MMBtu, GJ, tonne, klb") },
      { key: "year",          label: t("Year"),          required: true,  hint: t("4-digit year (e.g. 2024) — required unless using a date column") },
      { key: "month",         label: t("Month"),         required: true,  hint: t("1–12 — required unless using a date column") },
    ],
  },
  {
    id: "steam",
    label: t("Steam & CHP (optional)"),
    icon: Activity,
    fields: [
      { key: "boiler_eff",        label: t("Boiler Efficiency"), required: false, hint: t("Steam: % (85) or fraction (0.85). Default 80 %") },
      { key: "trans_loss",        label: t("Transmission Loss"), required: false, hint: t("Steam: percentage, e.g. 5 = 5 %, 0.9 = 0.9 %. Default 0") },
      { key: "steam_enthalpy_btu_lb", label: t("Steam Enthalpy"), required: false, hint: t("Steam bought by mass (lb, klb, kg, short_ton, tonne): Btu/lb above water at 212 °F, from steam tables. Required for a mass") },
      { key: "total_emissions",   label: t("CHP Total Emissions"), required: false, hint: t("CHP: plant emissions, t CO2e") },
      { key: "heat_output_mmbtu", label: t("CHP Heat Output"), required: false, hint: t("CHP: heat bought, MMBtu") },
      { key: "power_output_mwh",  label: t("CHP Power Output"), required: false, hint: t("CHP: power bought, MWh") },
      { key: "heat_efficiency",   label: t("CHP Heat Efficiency"), required: false, hint: t("CHP: % or fraction. Default 80 %") },
      { key: "power_efficiency",  label: t("CHP Power Efficiency"), required: false, hint: t("CHP: % or fraction. Default 35 %") },
    ],
  }
];

const groupsFor = (): FieldGroupData[] => FIELD_GROUPS;

export interface Scope2ImportWizardProps {
  onClose: () => void;
  onUploadSuccess?: () => void;
}

export const Scope2ImportWizard: React.FC<Scope2ImportWizardProps> = ({ onClose, onUploadSuccess }) => {
  const downloadTemplate = () => {
    const header = "facility_name,date,year,month,source_type,grid_region,consumption,unit,factor";
    const sample = "Basin Alpha,2024-01-01,2024,1,electricity,Algerian National Grid,500,MWh,";
    const csv = `${header}\n${sample}\n`;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "scope2_import_template.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const fileExtras = (
    <div className="flex flex-col gap-2.5">
      <p className="m-0 text-sm font-medium text-text-secondary">{t("Don't have a file? Download a sample CSV template:")}</p>
      <div className="flex flex-wrap gap-2.5">
        <Button
          variant="secondary"
          className="h-auto min-w-0 flex-1 justify-start gap-3 px-4 py-3 text-left"
          onClick={downloadTemplate}
        >
          <FileSpreadsheet className="size-5 shrink-0" aria-hidden="true" />
          <span className="flex flex-col">
            <strong className="text-sm">{t("Scope 2 CSV Template")}</strong>
            <small className="text-xs font-normal opacity-80">{t("Includes electricity and steam columns with sample entries")}</small>
          </span>
          <Download className="ml-auto size-4 shrink-0" aria-hidden="true" />
        </Button>
      </div>
      <p className="m-0 text-xs text-text-secondary">
        {t("Have an export from another system? Upload it as it is: you can map custom headers to system fields.")}
      </p>
    </div>
  );

  return (
    <ImportWizard
      title={t("Scope 2 Bulk Import")}
      subtitle={t("Upload electricity and indirect steam data from CSV or Excel")}
      fieldGroupsFor={groupsFor}
      scopeFor={() => "2"}
      fileExtras={fileExtras}
      overwriteLabel={t("Overwrite existing Scope 2 records with matching region, month, source type, and grid/meter")}
      overwriteHint={t("If unchecked, duplicate records will be skipped to prevent double-counting.")}
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default Scope2ImportWizard;
