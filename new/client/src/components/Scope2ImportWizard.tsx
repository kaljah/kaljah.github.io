import React from "react";
import { Activity, Layers } from "lucide-react";
import ImportWizard from "./import-wizard/ImportWizard";
import { FieldGroupData } from "./import-wizard/mapping";

// Scope 2 (purchased electricity, steam and CHP) bulk import: the column layout plus the shared wizard.
const FIELD_GROUPS: FieldGroupData[] = [
  {
    id: "identity",
    label: "Location & Identity",
    icon: Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "activity",      label: "Activity",       required: false, hint: "e.g. Exploration & Production" },
      { key: "division",      label: "Division",       required: false, hint: "e.g. Production, Association" },
      { key: "field",         label: "Field",          required: false, hint: "e.g. Bir Berkine" },
    ],
  },
  {
    id: "measurement",
    label: "Measurement & Type",
    icon: Activity,
    fields: [
      { key: "source_type",   label: "Source Type",   required: false, hint: "electricity, indirect_steam, or cogen_allocation" },
      { key: "grid_region",   label: "Grid Region",   required: false, hint: "Grid name as listed on the Scope 2 form (e.g. Algerian National Grid). Required for electricity unless a supplier factor is given." },
      { key: "factor",        label: "Supplier Factor", required: false, hint: "Electricity: supplier / contract factor in kg CO2e/kWh (used when the grid is not listed). Steam: boiler factor in kg CO2/MMBtu" },
      { key: "consumption",   label: "Consumption",   required: true,  hint: "Amount of electricity/steam purchased" },
      { key: "unit",          label: "Unit",          required: true,  hint: "Electricity: kWh, MWh, GWh. Steam: MMBtu, GJ, tonne, klb" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column" },
    ],
  },
  {
    id: "steam",
    label: "Steam & CHP (optional)",
    icon: Activity,
    fields: [
      { key: "boiler_eff",        label: "Boiler Efficiency", required: false, hint: "Steam: % (85) or fraction (0.85). Default 80 %" },
      { key: "trans_loss",        label: "Transmission Loss", required: false, hint: "Steam: percentage, e.g. 5 = 5 %, 0.9 = 0.9 %. Default 0" },
      { key: "total_emissions",   label: "CHP Total Emissions", required: false, hint: "CHP: plant emissions, t CO2e" },
      { key: "heat_output_mmbtu", label: "CHP Heat Output", required: false, hint: "CHP: heat bought, MMBtu" },
      { key: "power_output_mwh",  label: "CHP Power Output", required: false, hint: "CHP: power bought, MWh" },
      { key: "heat_efficiency",   label: "CHP Heat Efficiency", required: false, hint: "CHP: % or fraction. Default 80 %" },
      { key: "power_efficiency",  label: "CHP Power Efficiency", required: false, hint: "CHP: % or fraction. Default 35 %" },
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
      title="Scope 2 Bulk Import"
      subtitle="Upload electricity and indirect steam data from CSV or Excel"
      fieldGroupsFor={groupsFor}
      scopeFor={() => "2"}
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
};

export default Scope2ImportWizard;
