import React from "react";
import { Activity, Layers } from "lucide-react";
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
      { key: "field",         label: t("Field"),          required: false, hint: t("e.g. Bir Berkine") },
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
  return (
    <ImportWizard
      title={t("Scope 2 Bulk Import")}
      subtitle={t("Upload electricity and indirect steam data from CSV or Excel")}
      fieldGroupsFor={groupsFor}
      scopeFor={() => "2"}
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default Scope2ImportWizard;
