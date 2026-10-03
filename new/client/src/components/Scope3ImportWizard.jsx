import React from "react";
import { Globe, Layers, Settings } from "lucide-react";
import ImportWizard from "./import-wizard/ImportWizard";

// Scope 3 bulk import: activity-based or spend-based (EEIO / NAICS) column layouts on the shared wizard.
const FIELD_GROUPS_ACTIVITY = [
  {
    id: "identity",
    label: "Location & Identity",
    icon: Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column" },
    ],
  },
  {
    id: "classification",
    label: "GHG Protocol Classification",
    icon: Globe,
    fields: [
      { key: "category",      label: "Category",      required: true,  hint: "e.g. 1, 2, 3... or 'Category 11'" },
      { key: "sub_category",  label: "Sub Category",  required: false, hint: "Activity name as in the Scope 3 form (e.g. Truck Transport) to use its factor" },
      { key: "notes",         label: "Description / Notes", required: false, hint: "Description of the emission source" },
    ],
  },
  {
    id: "measurement",
    label: "Activity & Emissions",
    icon: Settings,
    fields: [
      { key: "amount",          label: "Activity Data Amount", required: true, hint: "Quantity of the activity" },
      { key: "unit",            label: "Activity Unit",        required: true, hint: "e.g. kg, USD, miles" },
      { key: "emission_factor", label: "Emission Factor",      required: false, hint: "kg CO2e per activity unit. If empty, the factor of the Sub Category activity in the Scope 3 form is used (unit must match)." },
      { key: "ef_unit",         label: "EF Unit",              required: false, hint: "kg CO2e per unit (default), t CO2e per unit, or kg CO2e per $1,000" },
      { key: "co2e",            label: "Total CO2e",           required: false, hint: "Provide direct CO2e to skip calculations" },
    ],
  }
];

const FIELD_GROUPS_EEIO = [
  {
    id: "identity",
    label: "Location & Identity",
    icon: Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12" },
    ],
  },
  {
    id: "measurement",
    label: "Spend & NAICS",
    icon: Settings,
    fields: [
      { key: "naics_code",      label: "NAICS Code",      required: true,  hint: "6-digit 2017 NAICS code (EPA supply chain factors)" },
      { key: "spend_usd",       label: "Spend (USD)",     required: true,  hint: "Amount spent in USD" },
      { key: "notes",           label: "Description / Notes", required: false, hint: "Optional supplier or purchase description" },
    ],
  }
];

const MODES = [
  { value: "activity", label: "Activity data" },
  { value: "eeio", label: "Spend (EEIO / NAICS)" },
];
const groupsFor = (mode) => (mode === "eeio" ? FIELD_GROUPS_EEIO : FIELD_GROUPS_ACTIVITY);

export default function Scope3ImportWizard({ onClose, onUploadSuccess }) {
  return (
    <ImportWizard
      title="Scope 3 Bulk Import"
      subtitle="Upload value chain emissions data from CSV or Excel"
      modes={MODES}
      fieldGroupsFor={groupsFor}
      scopeFor={(mode) => (mode === "eeio" ? "3_eeio" : "3")}
      onClose={onClose}
      onUploadSuccess={onUploadSuccess}
    />
  );
}
