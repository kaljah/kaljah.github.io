import React, { useState, useRef, useCallback } from "react";
import Papa from "papaparse";
import api from "../api";
import UploadProgress from "./UploadProgress";
import "./ColumnMappingWizard.css";
import { PROCESS_TYPES } from "../utils/EmissionFactors";

// ─── System field definitions ─────────────────────────────────────────────────
const TEMPLATES = {
  sources: [
    {
      id: "activity",
      label: "Activity",
      required: true,
      hint: "e.g. Exploration & Production",
    },
    {
      id: "division",
      label: "Division",
      required: true,
      hint: "e.g. Production, Association",
    },
    {
      id: "facility_id",
      label: "Region",
      required: true,
      hint: "e.g. Hassi Messaoud",
    },
    { id: "field", label: "Field", required: false },
    { id: "name", label: "Equipment Name", required: true },
    { id: "equipment_id", label: "Equipment ID", required: false },
    {
      id: "type",
      label: "Process Type",
      required: true,
      hint: "e.g. combustion, flaring",
    },
    {
      id: "fuel_type",
      label: "Fuel Type",
      required: false,
      hint: "e.g. Natural Gas",
    },
    {
      id: "amount",
      label: "Quantity",
      required: false,
      hint: "Optional initial activity data",
    },
    { id: "unit", label: "Unit", required: false, hint: "e.g. scf, m3, gal" },
    { id: "year", label: "Year", required: false },
    { id: "month", label: "Month", required: false },
  ],
  activity: [
    { id: "activity", label: "Activity", required: false },
    { id: "division", label: "Division", required: false },
    { id: "facility_id", label: "Region", required: true },
    { id: "facility_name", label: "Region / Facility", required: false },
    { id: "field", label: "Field", required: false },
    { id: "group", label: "Emission Source (Group)", required: false },
    { id: "equipment", label: "Equipment Name", required: false },
    { id: "equipment_id", label: "Equipment ID", required: false },
    { id: "year", label: "Year", required: false },
    { id: "month", label: "Month", required: false },
    { id: "date", label: "Date", required: true },
    { id: "process", label: "Process Type", required: true },
    { id: "process_type", label: "Process Type (legacy)", required: false },
    { id: "fuel", label: "Activity / Fuel", required: true },
    { id: "fuel_type", label: "Fuel Type (legacy)", required: false },
    { id: "quantity", label: "Quantity", required: true },
    { id: "amount", label: "Amount", required: false },
    { id: "unit", label: "Unit", required: true },
    { id: "factor_type", label: "Factor Type", required: false },
    { id: "hhv", label: "HHV", required: false },
    { id: "ef_unit", label: "EF Unit", required: false },
    { id: "combustion_efficiency", label: "Combustion Eff", required: false },
    { id: "flare_type", label: "Flare Type", required: false },
    { id: "ch4_content", label: "CH4 Content %", required: false },
    { id: "co2_content", label: "CO2 Content %", required: false },
    { id: "control_efficiency", label: "Control Eff", required: false },
    { id: "operating_temperature", label: "Op Temp", required: false },
    { id: "temp_unit", label: "Temp Unit", required: false },
    { id: "operating_pressure", label: "Op Press", required: false },
    { id: "press_unit", label: "Press Unit", required: false },
    { id: "z_factor", label: "Z Factor", required: false },
    { id: "c1", label: "C1", required: false },
    { id: "c2", label: "C2", required: false },
    { id: "c3", label: "C3", required: false },
    { id: "c4", label: "C4", required: false },
    { id: "c5", label: "C5", required: false },
    { id: "c6", label: "C6", required: false },
    { id: "c7", label: "C7", required: false },
    { id: "c8", label: "C8", required: false },
    { id: "c9", label: "C9", required: false },
    { id: "c10", label: "C10+", required: false },
    { id: "co2_mol", label: "CO2 Mol %", required: false },
    { id: "n2_mol", label: "N2 Mol %", required: false },
    { id: "mud_type", label: "Mud Type", required: false },
    { id: "mud_unit", label: "Mud Unit", required: false },
    { id: "comp_method", label: "Comp Method", required: false },
    { id: "comp_rate", label: "Comp Rate", required: false },
    { id: "comp_duration", label: "Comp Duration", required: false },
    { id: "comp_flare_eff", label: "Comp Flare Eff", required: false },
    { id: "unload_depth", label: "Unload Depth", required: false },
    { id: "unload_diam", label: "Unload Diam", required: false },
    { id: "unload_press", label: "Unload Press", required: false },
    { id: "unload_freq", label: "Unload Freq", required: false },
    { id: "unload_flare_eff", label: "Unload Flare Eff", required: false },
    { id: "unload_temp", label: "Unload Temp", required: false },
    { id: "blowdown_pressure", label: "BD Press", required: false },
    { id: "blowdown_events", label: "BD Events", required: false },
    { id: "blowdown_temp", label: "BD Temp", required: false },
    { id: "blowdown_temp_unit", label: "BD Temp Unit", required: false },
    { id: "blowdown_press_unit", label: "BD Press Unit", required: false },
    { id: "tank_gor", label: "Tank GOR", required: false },
    { id: "tank_control_eff", label: "Tank Control Eff", required: false },
    { id: "tank_unit", label: "Tank Unit", required: false },
    { id: "tank_api_gravity", label: "Tank API Gravity", required: false },
    { id: "tank_throughput", label: "Tank Throughput", required: false },
    { id: "tank_throughput_unit", label: "Tank Thr Unit", required: false },
    { id: "tank_turnovers", label: "Tank Turnovers", required: false },
    { id: "pneu_type", label: "Pneu Type", required: false },
    { id: "pneu_count", label: "Pneu Count", required: false },
    { id: "pneu_bleed_rate", label: "Pneu Bleed Rate", required: false },
    { id: "pneu_hours", label: "Pneu Hours", required: false },
    { id: "pump_type", label: "Pump Type", required: false },
    { id: "pump_count", label: "Pump Count", required: false },
    { id: "pump_gas_rate", label: "Pump Gas Rate", required: false },
    { id: "pump_hours", label: "Pump Hours", required: false },
    { id: "comp_mode", label: "Comp Mode", required: false },
    { id: "comp_hours", label: "Comp Hours", required: false },
    { id: "comp_count", label: "Comp Count", required: false },
    { id: "operating_hours", label: "Op Hours", required: false },
    { id: "leak_count", label: "Leak Count", required: false },
    { id: "leak_duration", label: "Leak Duration", required: false },
    { id: "leak_rate", label: "Leak Rate", required: false },
    { id: "agr_throughput", label: "AGR Throughput", required: false },
    { id: "agr_co2_in", label: "AGR CO2 In", required: false },
    { id: "agr_co2_out", label: "AGR CO2 Out", required: false },
    { id: "agr_unit", label: "AGR Unit", required: false },
    { id: "agr_ch4_in", label: "AGR CH4 In", required: false },
    { id: "agr_ch4_slip", label: "AGR CH4 Slip", required: false },
    { id: "agr_control_eff", label: "AGR Control Eff", required: false },
    { id: "dehy_pump_rate", label: "Dehy Pump Rate", required: false },
    { id: "dehy_pump_unit", label: "Dehy Pump Unit", required: false },
    { id: "dehy_hours", label: "Dehy Hours", required: false },
    { id: "dehy_press", label: "Dehy Press", required: false },
    { id: "dehy_press_unit", label: "Dehy Press Unit", required: false },
    { id: "dehy_temp", label: "Dehy Temp", required: false },
    { id: "dehy_temp_unit", label: "Dehy Temp Unit", required: false },
    { id: "dehy_has_flash", label: "Dehy Has Flash", required: false },
    { id: "dehy_flash_eff", label: "Dehy Flash Eff", required: false },
    { id: "dehy_still_type", label: "Dehy Still Type", required: false },
    { id: "dehy_ch4_content", label: "Dehy CH4 Content", required: false },
    { id: "dehy_eff", label: "Dehy Eff", required: false },
    { id: "boiler_eff", label: "Boiler Eff", required: false },
    { id: "trans_loss", label: "Trans Loss", required: false },
    { id: "heat_unit", label: "Heat Unit", required: false },
    { id: "carbon_content", label: "Carbon Content", required: false },
    { id: "fugitive_method", label: "Fugitive Method", required: false },
    { id: "fugitive_ppm", label: "Fugitive PPM", required: false },
    {
      id: "meter_uncertainty_pct",
      label: "Meter Uncertainty %",
      required: false,
    },
    { id: "gc_uncertainty_pct", label: "GC Uncertainty %", required: false },
    { id: "user_unc_co2", label: "User Unc CO2", required: false },
    { id: "user_unc_ch4", label: "User Unc CH4", required: false },
    { id: "user_unc_n2o", label: "User Unc N2O", required: false },
  ],
  activity_scope2: [
    { id: "facility_id", label: "Region", required: true },
    { id: "year", label: "Year", required: true },
    { id: "month", label: "Month", required: true },
    { id: "grid_region", label: "Grid Region", required: true },
    { id: "consumption", label: "Consumption", required: true },
    { id: "unit", label: "Unit", required: true, hint: "kWh, MWh, GWh" },
  ],
  activity_scope3: [
    { id: "facility_id", label: "Region", required: true },
    { id: "year", label: "Year", required: true },
    { id: "month", label: "Month", required: true },
    { id: "category", label: "Category #", required: true, hint: "1-15" },
    {
      id: "sub_category",
      label: "Activity Type",
      required: true,
      hint: "e.g. Steel, Flight",
    },
    { id: "amount", label: "Quantity", required: true },
    { id: "unit", label: "Unit", required: true },
  ],
  custom_factors: [
    {
      id: "name",
      label: "Factor Name",
      required: true,
      hint: "e.g. Specialized Gas",
    },
    {
      id: "parent_fuel",
      label: "Parent API Fuel",
      required: false,
      hint: "e.g. Natural Gas",
    },
    { id: "unit", label: "Unit", required: true, hint: "e.g. scf, m3" },
    {
      id: "co2_factor",
      label: "CO2 Factor",
      required: true,
      hint: "Numeric value",
    },
    {
      id: "ch4_factor",
      label: "CH4 Factor",
      required: false,
      hint: "Numeric value",
    },
    {
      id: "n2o_factor",
      label: "N2O Factor",
      required: false,
      hint: "Numeric value",
    },
    {
      id: "co_factor",
      label: "CO Factor",
      required: false,
      hint: "Numeric value",
    },
    {
      id: "co2_uncertainty",
      label: "CO2 Uncertainty (%)",
      required: false,
      hint: "e.g. 5",
    },
    {
      id: "ch4_uncertainty",
      label: "CH4 Uncertainty (%)",
      required: false,
      hint: "e.g. 50",
    },
    {
      id: "n2o_uncertainty",
      label: "N2O Uncertainty (%)",
      required: false,
      hint: "e.g. 150",
    },
    { id: "usage", label: "Usage", required: false, hint: "e.g. combustion" },
  ],
  production: [
    { id: "facility_id", label: "Region", required: true },
    { id: "activity", label: "Activity", required: false },
    { id: "division", label: "Division", required: false },
    { id: "field", label: "Field", required: false },
    { id: "year", label: "Year", required: true },
    { id: "month", label: "Month", required: true },
    { id: "oil_amount", label: "Oil Quantity", required: false },
    { id: "oil_unit", label: "Oil Unit", required: false, hint: "bbl" },
    { id: "gas_amount", label: "Gas Quantity", required: false },
    { id: "gas_unit", label: "Gas Unit", required: false, hint: "mscf" },
  ],
  mitigation: [
    { id: "facility_id", label: "Region", required: true },
    { id: "name", label: "Project Name", required: true },
    {
      id: "project_type",
      label: "Type",
      required: true,
      hint: "e.g. CCUS, REC",
    },
    { id: "year", label: "Year", required: true },
    { id: "quantity_tco2e", label: "tCO2e Avoided", required: true },
    { id: "status", label: "Status", required: false, hint: "Active, Planned" },
    {
      id: "start_date",
      label: "Start Date",
      required: false,
      hint: "YYYY-MM-DD",
    },
    { id: "end_date", label: "End Date", required: false, hint: "YYYY-MM-DD" },
    { id: "investment_amount", label: "Investment", required: false },
    { id: "description", label: "Description", required: false },
  ],
  facilities: [
    { id: "name", label: "Region Name", required: true },
    { id: "activity", label: "Activity", required: true },
    { id: "division", label: "Division", required: true },
    { id: "field", label: "Field / Block", required: false },
    { id: "location", label: "Location (Wilaya)", required: true },
    { id: "boundary_type", label: "Consolidation Approach", required: true },
    { id: "boundary_detail", label: "Boundary Details", required: true },
    { id: "segment", label: "Supply Chain Segment", required: true },
    { id: "latitude", label: "Latitude", required: true },
    { id: "longitude", label: "Longitude", required: true },
  ],
};

// Auto-detect: tries to match a column header to a system field key/label
function autoDetectMapping(headers, fields) {
  const mapping = {};
  fields.forEach((field) => {
    const match = headers.find((h) => {
      const hl = h.toLowerCase();
      return (
        hl === field.key.toLowerCase() ||
        hl.includes(field.key.replace(/_/g, " ")) ||
        hl.includes(field.label.toLowerCase()) ||
        field.label.toLowerCase().includes(hl)
      );
    });
    if (match) mapping[field.key] = match;
  });
  return mapping;
}

// ─── SVG Icons ────────────────────────────────────────────────────────────────
const Icons = {
  Upload: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  ),
  Columns: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
      <line x1="15" y1="3" x2="15" y2="21" />
    </svg>
  ),
  Processing: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  FileXlsx: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="16" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  FileCsv: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
    </svg>
  ),
  Check: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  ChevronRight: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  ArrowLeft: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  ),
  Warning: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  Wand: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 4V2m0 14v-2M8 9H2m14 0h-2M3.5 3.5l1.5 1.5M16.5 16.5l1.5 1.5M16.5 3.5 15 5M3.5 20.5 5 19" />
      <path d="m3 9 9 9 9-9-9-9Z" />
    </svg>
  ),
  X: () => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};

// ─── Step indicator ───────────────────────────────────────────────────────────
const IconsSettings = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.75"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);
Icons.Settings = IconsSettings;

const STEPS = [
  { id: 1, label: "Configuration", Icon: Icons.Settings },
  { id: 2, label: "Select File", Icon: Icons.Upload },
  { id: 3, label: "Map Columns", Icon: Icons.Columns },
  { id: 4, label: "Processing", Icon: Icons.Processing },
];

function StepIndicator({ current }) {
  return (
    <div className="cmw-step-indicator">
      {STEPS.map((s, i) => {
        const done = s.id < current;
        const active = s.id === current;
        return (
          <React.Fragment key={s.id}>
            <div
              className={`cmw-step ${active ? "active" : ""} ${done ? "done" : ""}`}
            >
              <div className="cmw-step-circle">
                {done ? <Icons.Check /> : <s.Icon />}
              </div>
              <span className="cmw-step-label">{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`cmw-step-line ${done ? "done" : ""}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Main Wizard ──────────────────────────────────────────────────────────────
export default function ColumnMappingWizard({
  onClose,
  onUploadSuccess,
  type = "activity",
}) {
  const fileInputRef = useRef(null);
  const [step, setStep] = useState(type === "activity" ? 1 : 2);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({});
  const [globalFactor, setGlobalFactor] = useState("auto");
  const [jobId, setJobId] = useState(null);
  const [parseError, setParseError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showOptional, setShowOptional] = useState(false);
  const [selectedTier, setSelectedTier] = useState("3");
  const [selectedProcessScope, setSelectedProcessScope] = useState("all");
  const [selectedProcess, setSelectedProcess] = useState("flaring");
  const [overwriteDuplicates, setOverwriteDuplicates] = useState(false);

  // ── File handling ──────────────────────────────────────────────────────────
  const processFile = useCallback((f) => {
    if (!f) return;
    setParseError("");

    const isExcel = f.name.toLowerCase().endsWith(".xlsx");

    if (isExcel) {
      // For Excel: we don't parse in browser, but we still need headers.
      // Send a "preview" request or just show all system fields for manual mapping.
      setFile(f);
      setHeaders([]); // no browser-side parse for xlsx
      setMapping({});
      setStep(3);
      return;
    }

    // CSV: parse just the first row for headers
    Papa.parse(f, {
      preview: 5,
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (!results.meta.fields?.length) {
          setParseError(
            "Could not read column headers. Make sure the file has a header row.",
          );
          return;
        }
        const hdrs = results.meta.fields;
        setHeaders(hdrs);

        let base = TEMPLATES[type] || [];
        let allFields = base.map((f) => ({
          key: f.id,
          label: f.label,
          required: f.required,
          hint: f.hint || "",
        }));
        setMapping(autoDetectMapping(hdrs, allFields));

        setFile(f);
        setStep(3);
      },
      error: () =>
        setParseError(
          "Failed to parse the file. Please ensure it is a valid CSV.",
        ),
    });
  }, []);

  const onFileInputChange = (e) => {
    processFile(e.target.files[0]);
    e.target.value = "";
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    processFile(e.dataTransfer.files[0]);
  };

  // ── Submit upload ──────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const form = new FormData();
    form.append("file", file);
    form.append("global_factor_type", globalFactor);

    let scopeStr = type;
    if (type === "activity") scopeStr = "1";
    if (type === "activity_scope2") scopeStr = "2";
    if (type === "activity_scope3") scopeStr = "3";
    form.append("scope", scopeStr);
    
    if (type === "facilities") {
        form.append("overwrite_duplicates", overwriteDuplicates);
    }

    // Pass the column mapping so the server can use correct column names
    form.append("column_mapping", JSON.stringify(mapping));

    try {
      const res = await api.post("/emissions/upload/start", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJobId(res.data.job_id);
      setStep(4);
    } catch (err) {
      alert(
        "Error starting upload: " + (err.response?.data?.error || err.message),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Download template ──────────────────────────────────────────────────────
  const downloadTemplate = async (fmt) => {
    if (type === "activity") {
      try {
        const res = await api.get(
          `/emissions/template/${fmt}?tier=${selectedTier}&process=${selectedProcessScope === "specific" ? selectedProcess : "all"}`,
          { responseType: "blob" },
        );
        const url = URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement("a");
        a.href = url;
        a.download =
          fmt === "excel"
            ? "GHG_Emissions_Template_v2.xlsx"
            : "emissions_template.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
      } catch {
        alert("Template download failed.");
      }
      return;
    }

    // Generate client-side template for non-activity types
    let currentTemplate = TEMPLATES[type] || [];
    const headers = currentTemplate.map((t) => t.id).join(",");

    let csvContent = headers;

    if (type === "custom_factors") {
      csvContent = `${headers}\nSpecialized Generator Gas,Natural Gas,scf,53.06,0.001,0.0001,0,5,50,150,combustion`;
    } else if (type === "production") {
      csvContent = `${headers}\nHassi Messaoud,Exploration & Production,Production,Bir Berkine,2024,1,50000,bbl,12000,mscf`;
    } else if (type === "mitigation") {
      csvContent = `${headers}\nHassi Messaoud,Solar Farm A,REC,2024,1500,Active,2024-01-01,,500000,Solar panel installation`;
    } else if (type === "sources") {
      csvContent = `${headers}\nExploration & Production,Production,Hassi Messaoud,Bir Berkine,Combustion Unit A,EQ-001,combustion,Natural Gas,1000,scf,2024,1`;
    } else if (type === "activity_scope2") {
      csvContent = `${headers}\nHassi Messaoud,2024,1,National Grid,500,MWh`;
    } else if (type === "activity_scope3") {
      csvContent = `${headers}\nHassi Messaoud,2024,1,1,Purchased Goods,500,tonnes`;
    } else if (type === "facilities") {
      csvContent = `${headers}\nHassi R'Mel,Exploration & Production,Production,Block A,Laghouat,Operational Control,Details here,Upstream,33.8,3.2`;
    }

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${type}_import_template.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // ── Validation ─────────────────────────────────────────────────────────────

  // Dynamic fields logic
  const currentFields = React.useMemo(() => {
    let base = TEMPLATES[type] || [];

    let allFields = base.map((f) => ({
      key: f.id,
      label: f.label,
      required: f.required,
      hint: f.hint || "",
    }));

    let req = allFields.filter((f) => f.required);
    let opt = allFields.filter((f) => !f.required);

    if (type === "activity") {
      const generalFields = [
        "activity",
        "division",
        "facility_id",
        "facility_name",
        "field",
        "group",
        "year",
        "month",
        "date",
        "process",
        "process_type",
        "fuel",
        "fuel_type",
        "amount",
        "quantity",
        "unit",
        "factor_type",
        "equipment",
        "equipment_id",
        "equipment_name",
      ];

      let filteredBase = allFields.filter((f) => generalFields.includes(f.key));
      req = filteredBase.filter((f) => f.required);
      opt = filteredBase.filter((f) => !f.required);

      if (selectedTier === "3") {
        const processFields = {
          combustion: [
            "hhv",
            "ef_unit",
            "combustion_efficiency",
            "operating_temperature",
            "temp_unit",
            "operating_pressure",
            "press_unit",
            "z_factor",
            "c1",
            "c2",
            "c3",
            "c4",
            "c5",
            "c6",
            "c7",
            "c8",
            "c9",
            "c10",
            "co2_mol",
            "n2_mol",
          ],
          flaring: [
            "hhv",
            "ef_unit",
            "flare_type",
            "ch4_content",
            "co2_content",
            "control_efficiency",
            "operating_temperature",
            "temp_unit",
            "operating_pressure",
            "press_unit",
            "z_factor",
            "c1",
            "c2",
            "c3",
            "c4",
            "c5",
            "c6",
            "c7",
            "c8",
            "c9",
            "c10",
            "co2_mol",
            "n2_mol",
          ],
          drilling: ["mud_type", "mud_unit"],
          completions: [
            "comp_method",
            "comp_rate",
            "comp_duration",
            "ch4_content",
            "co2_content",
            "comp_flare_eff",
          ],
          unloading: [
            "unload_depth",
            "unload_diam",
            "unload_press",
            "unload_freq",
            "unload_flare_eff",
            "ch4_content",
            "co2_content",
            "unload_temp",
            "temp_unit",
          ],
          blowdown: [
            "blowdown_pressure",
            "blowdown_events",
            "ch4_content",
            "co2_content",
            "control_efficiency",
            "blowdown_temp",
            "blowdown_temp_unit",
            "blowdown_press_unit",
            "z_factor",
          ],
          tank_flashing: [
            "tank_gor",
            "tank_ch4_content",
            "tank_control_eff",
            "tank_unit",
            "tank_api_gravity",
          ],
          tank_working_standing: [
            "tank_throughput",
            "tank_throughput_unit",
            "tank_ch4_content",
            "tank_control_eff",
            "tank_turnovers",
          ],
          pneumatic_device: [
            "pneu_type",
            "pneu_count",
            "pneu_bleed_rate",
            "pneu_hours",
            "ch4_content",
            "co2_content",
          ],
          pneumatic_pump: [
            "pump_type",
            "pump_count",
            "pump_gas_rate",
            "pump_hours",
            "ch4_content",
            "co2_content",
          ],
          centrifugal_compressor: [
            "comp_mode",
            "comp_hours",
            "ch4_content",
            "co2_content",
          ],
          reciprocating_compressor: [
            "comp_mode",
            "comp_hours",
            "ch4_content",
            "co2_content",
          ],
          fugitives_equipment: [
            "fugitive_method",
            "fugitive_ppm",
            "comp_count",
            "ch4_content",
            "co2_content",
            "operating_hours",
          ],
          fugitives_leaks: [
            "leak_count",
            "leak_duration",
            "leak_rate",
            "ch4_content",
            "co2_content",
          ],
          agr: [
            "agr_throughput",
            "agr_co2_in",
            "agr_co2_out",
            "agr_ch4_in",
            "agr_ch4_out",
            "agr_vent_rate",
            "agr_ch4_slip",
            "agr_control_eff",
          ],
          dehydrator: [
            "dehy_throughput",
            "dehy_pump_rate",
            "dehy_pump_unit",
            "dehy_hours",
            "dehy_press",
            "dehy_press_unit",
            "dehy_temp",
            "dehy_temp_unit",
            "dehy_has_flash",
            "dehy_flash_eff",
            "dehy_still_type",
            "dehy_ch4_content",
            "dehy_eff",
            "c1",
            "c2",
            "c3",
            "c4",
            "c5",
            "c6",
            "c7",
            "c8",
            "c9",
            "c10",
          ],
        };

        let allowed = [];
        if (selectedProcessScope === "all") {
          Object.values(processFields).forEach((arr) => {
            allowed.push(...arr);
          });
          allowed = [...new Set(allowed)];
        } else {
          allowed = processFields[selectedProcess] || [];
        }

        allowed.forEach((f) => {
          if (!opt.find((x) => x.key === f)) {
            opt.push({
              key: f,
              label: f.replace(/_/g, " ").toUpperCase(),
              hint: "Tier 3 specific",
              required: false,
            });
          }
        });
      }
    }

    return { req, opt, all: [...req, ...opt] };
  }, [type, selectedTier, selectedProcessScope, selectedProcess]);

  const activeRequired = currentFields.req;
  const activeOptional = currentFields.opt;

  const missingRequired = activeRequired.filter((f) => !mapping[f.key]);

  const canProceed = missingRequired.length === 0 || headers.length === 0; // xlsx: skip client-side check

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      className="cmw-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="cmw-modal">
        {/* Header */}
        <div className="cmw-header">
          <div>
            <h2 className="cmw-title">
              Import{" "}
              {type === "sources"
                ? "Equipment"
                : type === "custom_factors"
                  ? "Custom Factors"
                  : type === "production"
                    ? "Production Data"
                    : type === "mitigation"
                      ? "Mitigation Projects"
                      : "Emissions Data"}
            </h2>
            <p className="cmw-subtitle">
              Upload a CSV or Excel file to bulk-import your records
            </p>
          </div>
          <button className="cmw-close-btn" onClick={onClose}>
            <Icons.X />
          </button>
        </div>

        {/* Step Indicator */}
        <StepIndicator current={step} />

        {/* ── STEP 1: Configuration ── */}
        {step === 1 && type === "activity" && (
          <div className="cmw-body">
            <div
              style={{
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "24px",
              }}
            >
              <div>
                <h3
                  style={{
                    marginBottom: "16px",
                    color: "var(--text-primary)",
                    fontSize: "1.1rem",
                  }}
                >
                  Calculation Tier
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                  }}
                >
                  <div
                    className={`cmw-mode-card ${selectedTier === "1" ? "active" : ""}`}
                    onClick={() => setSelectedTier("1")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedTier === "1"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "8px",
                      }}
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedTier === "1"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 style={{ margin: 0, color: "var(--text-primary)" }}>
                        Tier 1 (Default Factors)
                      </h4>
                    </div>
                    <p
                      style={{
                        margin: 0,
                        fontSize: "0.9rem",
                        color: "var(--text-secondary)",
                      }}
                    >
                      Basic calculation using industry defaults.
                    </p>
                  </div>
                  <div
                    className={`cmw-mode-card ${selectedTier === "3" ? "active" : ""}`}
                    onClick={() => setSelectedTier("3")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedTier === "3"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "8px",
                      }}
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedTier === "3"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 style={{ margin: 0, color: "var(--text-primary)" }}>
                        Tier 3 (Engineering)
                      </h4>
                    </div>
                    <p
                      style={{
                        margin: 0,
                        fontSize: "0.9rem",
                        color: "var(--text-secondary)",
                      }}
                    >
                      Advanced calculation using process specifications.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3
                  style={{
                    marginBottom: "16px",
                    color: "var(--text-primary)",
                    fontSize: "1.1rem",
                  }}
                >
                  Process Scope
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                    marginBottom: "16px",
                  }}
                >
                  <div
                    className={`cmw-mode-card ${selectedProcessScope === "all" ? "active" : ""}`}
                    onClick={() => setSelectedProcessScope("all")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedProcessScope === "all"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "8px",
                      }}
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedProcessScope === "all"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 style={{ margin: 0, color: "var(--text-primary)" }}>
                        All Processes
                      </h4>
                    </div>
                    <p
                      style={{
                        margin: 0,
                        fontSize: "0.9rem",
                        color: "var(--text-secondary)",
                      }}
                    >
                      Upload data for various process types together.
                    </p>
                  </div>
                  <div
                    className={`cmw-mode-card ${selectedProcessScope === "specific" ? "active" : ""}`}
                    onClick={() => setSelectedProcessScope("specific")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedProcessScope === "specific"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "8px",
                      }}
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedProcessScope === "specific"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 style={{ margin: 0, color: "var(--text-primary)" }}>
                        Choose by Process
                      </h4>
                    </div>
                    <p
                      style={{
                        margin: 0,
                        fontSize: "0.9rem",
                        color: "var(--text-secondary)",
                      }}
                    >
                      Upload data for a single specific process.
                    </p>
                  </div>
                </div>

                {selectedProcessScope === "specific" && (
                  <div style={{ marginTop: "12px" }}>
                    <label
                      style={{
                        display: "block",
                        marginBottom: "8px",
                        color: "var(--text-secondary)",
                        fontWeight: "bold",
                      }}
                    >
                      Select Process Type:
                    </label>
                    <select
                      value={selectedProcess}
                      onChange={(e) => setSelectedProcess(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "12px",
                        borderRadius: "6px",
                        border: "1px solid var(--border-color)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                        outline: "none",
                      }}
                    >
                      {Object.entries(PROCESS_TYPES).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Navigation Footer */}
        <div
          className="cmw-footer"
          style={{
            borderTop: "1px solid var(--border-color)",
            padding: "16px 24px",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          {step > (type === "activity" ? 1 : 2) && step < 4 ? (
            <button className="cmw-btn-ghost" onClick={() => setStep(step - 1)}>
              <Icons.ArrowLeft /> Back
            </button>
          ) : (
            <div></div>
          )}

          {step === 1 && (
            <button className="cmw-btn-primary" onClick={() => setStep(2)}>
              Next <Icons.ChevronRight />
            </button>
          )}
        </div>

        {/* ── STEP 2: File Select ── */}
        {step === 2 && (
          <div className="cmw-body">
            {type === "facilities" && (
              <div className="cmw-config-section" style={{ marginBottom: '20px', padding: '16px', border: '1px solid var(--border-color)', borderRadius: '8px', background: 'var(--bg-secondary)' }}>
                <h3 style={{ marginBottom: '8px', fontSize: '1rem', color: 'var(--text-primary)' }}>Import Settings</h3>
                <label className="cmw-config-label" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input 
                    type="checkbox" 
                    checked={overwriteDuplicates} 
                    onChange={(e) => setOverwriteDuplicates(e.target.checked)}
                  />
                  Overwrite existing Regions with the same name
                </label>
                <p className="cmw-hint" style={{ marginTop: '4px', marginLeft: '24px' }}>If unchecked, duplicates will be skipped with an error.</p>
              </div>
            )}
            {/* Drop zone */}
            <div
              className={`cmw-dropzone ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx"
                style={{ display: "none" }}
                onChange={onFileInputChange}
              />
              <div className="cmw-dropzone-icon">
                <Icons.Upload />
              </div>
              <p className="cmw-dropzone-text">
                Drag &amp; drop your file here, or <span>click to browse</span>
              </p>
              <p className="cmw-dropzone-sub">
                Supports .xlsx and .csv — optimised for millions of rows
              </p>
              {parseError && (
                <div className="cmw-inline-error">
                  <Icons.Warning />
                  {parseError}
                </div>
              )}
            </div>

            {/* Template download */}
            <div className="cmw-template-section">
              <p className="cmw-template-label">
                Don't have a file yet? Start from our template:
              </p>
              <div className="cmw-template-btns">
                {type === "activity" && (
                  <button
                    className="cmw-template-btn"
                    onClick={() => downloadTemplate("excel")}
                  >
                    <span className="cmw-template-btn-icon">
                      <Icons.FileXlsx />
                    </span>
                    <span>
                      <strong>Excel Template</strong>
                      <small>
                        With dropdowns, sample data & engineering sheets
                      </small>
                    </span>
                  </button>
                )}
                <button
                  className="cmw-template-btn"
                  onClick={() => downloadTemplate("csv")}
                >
                  <span className="cmw-template-btn-icon">
                    <Icons.FileCsv />
                  </span>
                  <span>
                    <strong>CSV Template</strong>
                    <small>Lightweight flat file for maximum performance</small>
                  </span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 2: Column Mapping ── */}
        {step === 3 && (
          <div className="cmw-body">
            {/* File badge */}
            <div className="cmw-file-badge">
              <div className="cmw-file-badge-icon">
                <Icons.FileXlsx />
              </div>
              <div>
                <p className="cmw-file-name">{file?.name}</p>
                <p className="cmw-file-size">
                  {file ? (file.size / 1024).toFixed(1) + " KB" : ""}
                </p>
              </div>
              {headers.length > 0 && (
                <div className="cmw-auto-badge">
                  <Icons.Wand />
                  <span>
                    {Object.keys(mapping).length} columns auto-detected
                  </span>
                </div>
              )}
            </div>

            {/* Excel note */}
            {headers.length === 0 && (
              <div className="cmw-info-banner">
                <Icons.Warning />
                <span>
                  Excel files are processed server-side. If your column names
                  match the template exactly, mapping is automatic. Otherwise,
                  use the table below to tell us what each column should map to.
                </span>
              </div>
            )}

            {/* Missing required fields warning */}
            {headers.length > 0 && missingRequired.length > 0 && (
              <div className="cmw-warning-banner">
                <Icons.Warning />
                <span>
                  <strong>
                    {missingRequired.length} required field
                    {missingRequired.length > 1 ? "s" : ""} not mapped:
                  </strong>{" "}
                  {missingRequired.map((f) => f.label).join(", ")}
                </span>
              </div>
            )}

            {/* Mapping table */}
            <div className="cmw-mapping-container">
              <div className="cmw-mapping-group-label">Required Fields</div>
              <div className="cmw-mapping-table">
                <div className="cmw-mapping-header">
                  <span>System Field</span>
                  <span>Description</span>
                  <span>Your Column</span>
                  <span>Status</span>
                </div>

                {activeRequired.map((field) => (
                  <MappingRow
                    key={field.key}
                    field={field}
                    headers={headers}
                    value={mapping[field.key] || ""}
                    onChange={(val) =>
                      setMapping((m) => ({ ...m, [field.key]: val }))
                    }
                  />
                ))}
              </div>

              <button
                className="cmw-optional-toggle"
                onClick={() => setShowOptional((v) => !v)}
              >
                <Icons.ChevronRight />
                {showOptional ? "Hide" : "Show"} optional fields (
                {activeOptional.length})
              </button>

              {showOptional && (
                <>
                  <div
                    className="cmw-mapping-group-label"
                    style={{ marginTop: "12px" }}
                  >
                    Optional Fields
                  </div>
                  <div className="cmw-mapping-table">
                    <div className="cmw-mapping-header">
                      <span>System Field</span>
                      <span>Description</span>
                      <span>Your Column</span>
                      <span>Status</span>
                    </div>
                    {activeOptional.map((field) => (
                      <MappingRow
                        key={field.key}
                        field={field}
                        headers={headers}
                        value={mapping[field.key] || ""}
                        onChange={(val) =>
                          setMapping((m) => ({ ...m, [field.key]: val }))
                        }
                      />
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Factor type override */}
            <div className="cmw-factor-row">
              <label className="cmw-factor-label">
                Default factor type when not specified in file
              </label>
              <select
                className="cmw-factor-select"
                value={globalFactor}
                onChange={(e) => setGlobalFactor(e.target.value)}
              >
                <option value="auto">Auto-detect from file</option>
                <option value="default">Force Standard (API Compendium)</option>
                <option value="custom">Force Custom Factors</option>
              </select>
            </div>
          </div>
        )}

        {/* ── STEP 3: Processing ── */}
        {step === 4 && jobId && (
          <div className="cmw-body cmw-body--progress">
            <UploadProgress
              jobId={jobId}
              onComplete={() => {
                if (onUploadSuccess) onUploadSuccess();
                onClose();
              }}
              onCancel={onClose}
            />
          </div>
        )}

        {/* Footer actions */}
        {step !== 4 && (
          <div className="cmw-footer">
            <button
              className="cmw-btn-ghost"
              onClick={
                step === (type === "activity" ? 1 : 2)
                  ? onClose
                  : () => setStep((s) => s - 1)
              }
            >
              {step === (type === "activity" ? 1 : 2) ? (
                <>
                  <Icons.X /> Cancel
                </>
              ) : (
                <>
                  <Icons.ArrowLeft /> Back
                </>
              )}
            </button>

            {step === 3 && (
              <button
                className="cmw-btn-primary"
                onClick={handleSubmit}
                disabled={isSubmitting || (!canProceed && headers.length > 0)}
              >
                {isSubmitting ? (
                  <span className="cmw-spinner" />
                ) : (
                  <Icons.Processing />
                )}
                {isSubmitting ? "Starting…" : "Start Import"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Single mapping row ────────────────────────────────────────────────────────
function MappingRow({ field, headers, value, onChange }) {
  const mapped = !!value;

  return (
    <div
      className={`cmw-mapping-row ${!mapped && field.required ? "unmapped" : ""}`}
    >
      <div className="cmw-field-name">
        {field.label}
        {field.required && <span className="cmw-required-dot" />}
      </div>
      <div className="cmw-field-hint">{field.hint}</div>
      <div className="cmw-field-select">
        {headers.length > 0 ? (
          <select
            className={`cmw-select ${mapped ? "matched" : ""}`}
            value={value}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">— Not mapped —</option>
            {headers.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        ) : (
          <input
            className={`cmw-text-input ${mapped ? "matched" : ""}`}
            placeholder="Column name in your file"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />
        )}
      </div>
      <div className="cmw-field-status">
        {mapped ? (
          <span className="cmw-status-ok">
            <Icons.Check />
          </span>
        ) : (
          <span className="cmw-status-empty" />
        )}
      </div>
    </div>
  );
}
