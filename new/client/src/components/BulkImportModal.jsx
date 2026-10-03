import BulkImportModalUploadProgressContainer from "./bulk-import/BulkImportModalUploadProgressContainer";
import React, { useState, useRef, useEffect } from "react";
import { NativeSelect } from "../ui/NativeSelect";
import { activateOnKey } from "../utils/a11yKeys";
import api from "../api";
import Modal from "./Modal";
import { useToast } from "./Toast";
import {
  FileText,
  Upload,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Info,
} from "lucide-react";
import Papa from "papaparse"; // NEW-05 FIX: use PapaParse instead of fragile string splitting
import { PROCESS_TYPES } from "../utils/EmissionFactors";
import "./BulkImportModal.css";

const BulkImportModal = ({ isOpen, onClose, type, onImportSuccess }) => {
  const toast = useToast();
  const fileInputRef = useRef(null);
  const pollIntervalRef = useRef(null);
  const [file, setFile] = useState(null);
  const [csvData, setCsvData] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({});
  const [step, setStep] = useState(1); // 1: Upload, 2: Mapping, 3: Preview
  const [loading, setLoading] = useState(false);
  const [uploadJobId, setUploadJobId] = useState(null);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [showCheatSheet, setShowCheatSheet] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [mappedRecords, setMappedRecords] = useState([]);
  const [selectedTier, setSelectedTier] = useState("3");
  const [selectedProcess, setSelectedProcess] = useState("all");

  useEffect(() => {
    if (isOpen) {
      // reset the wizard each time the parent opens it (the open state lives in the parent)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStep(type === "activity" ? 0 : 1);
      setFile(null);
      setCsvData([]);
      setHeaders([]);
      setMapping({});
      setValidationErrors([]);
      setMappedRecords([]);
      setSelectedTier("3");
      setSelectedProcess("all");
      setUploadJobId(null);
      setUploadStatus(null);
    }
  }, [isOpen, type]);

  const VALID_FUELS = [
    "Natural Gas",
    "Diesel (No. 2 Fuel Oil)",
    "Crude Oil",
    "Motor Gasoline",
    "LPG",
    "Propane",
    "Fuel Oil",
  ];
  const VALID_UNITS = ["scf", "m3", "gal", "bbl", "tonnes/yr", "kg", "tonne"];

  const HIERARCHY = {
    "Exploration & Production": ["Production", "Association"],
    "Liquifaction and Separation": ["LNG", "LPG"],
    "Refining and Petrochemicals": ["Refining", "Petrochemicals"],
    "Transport (TRC)": ["TRC"],
  };

  // Templates for different import types
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
      { id: "year", label: "Year", required: false },
      { id: "month", label: "Month", required: false },
      { id: "date", label: "Date", required: false },
      { id: "process_type", label: "Process Type", required: true },
      { id: "fuel", label: "Fuel/Gas Type", required: true },
      { id: "fuel_type", label: "Broad Fuel Type", required: false },
      { id: "amount", label: "Quantity", required: true },
      { id: "quantity", label: "Quantity", required: false },
      { id: "unit", label: "Unit", required: true },
      { id: "factor_type", label: "Factor Type", required: false },
      { id: "equipment_id", label: "Equipment ID", required: false },
      { id: "equipment_name", label: "Equipment Name", required: false },

      // Core Tier 1/3 physical parameters
      { id: "hhv", label: "HHV", required: false },
      { id: "ef_unit", label: "EF Unit", required: false },
      { id: "combustion_efficiency", label: "Combustion Eff", required: false },
      { id: "operating_temperature", label: "Operating Temp", required: false },
      { id: "temp_unit", label: "Temp Unit", required: false },
      { id: "operating_pressure", label: "Operating Press", required: false },
      { id: "press_unit", label: "Press Unit", required: false },
      { id: "z_factor", label: "Z Factor", required: false },

      // Gas Composition (Tier 3)
      { id: "c1", label: "C1 Mol%", required: false },
      { id: "c2", label: "C2 Mol%", required: false },
      { id: "c3", label: "C3 Mol%", required: false },
      { id: "c4", label: "C4 Mol%", required: false },
      { id: "c5", label: "C5 Mol%", required: false },
      { id: "c6", label: "C6 Mol%", required: false },
      { id: "c7", label: "C7 Mol%", required: false },
      { id: "c8", label: "C8 Mol%", required: false },
      { id: "c9", label: "C9 Mol%", required: false },
      { id: "c10", label: "C10 Mol%", required: false },
      { id: "n2_mol", label: "N2 Mol%", required: false },
      { id: "co2_mol", label: "CO2 Mol%", required: false },

      // Process-specific Tier 3 parameters
      { id: "flare_type", label: "Flare Type", required: false },
      { id: "ch4_content", label: "CH4 Content %", required: false },
      { id: "co2_content", label: "CO2 Content %", required: false },
      {
        id: "control_efficiency",
        label: "Control Efficiency %",
        required: false,
      },
      { id: "mud_type", label: "Mud Type", required: false },
      { id: "mud_unit", label: "Mud Unit", required: false },
      { id: "comp_method", label: "Comp Method", required: false },
      { id: "comp_rate", label: "Comp Rate", required: false },
      { id: "comp_duration", label: "Comp Duration", required: false },
      { id: "comp_liquid_bbl", label: "Comp Liquid bbl", required: false },
      { id: "comp_gor", label: "Comp GOR", required: false },
      { id: "comp_flare_eff", label: "Comp Flare Eff %", required: false },
      { id: "comp_choke_size", label: "Comp Choke Size", required: false },
      { id: "comp_whp", label: "Comp WHP", required: false },
      { id: "unload_depth", label: "Unload Depth", required: false },
      { id: "unload_diam", label: "Unload Diam", required: false },
      { id: "unload_press", label: "Unload Press", required: false },
      { id: "unload_freq", label: "Unload Freq", required: false },
      { id: "unload_flare_eff", label: "Unload Flare Eff", required: false },
      { id: "unload_temp", label: "Unload Temp", required: false },
      { id: "blowdown_pressure", label: "Blowdown Press", required: false },
      { id: "blowdown_events", label: "Blowdown Events", required: false },
      { id: "blowdown_unit", label: "Blowdown Unit", required: false },
      { id: "blowdown_temp", label: "Blowdown Temp", required: false },
      {
        id: "blowdown_temp_unit",
        label: "Blowdown Temp Unit",
        required: false,
      },
      {
        id: "blowdown_press_unit",
        label: "Blowdown Press Unit",
        required: false,
      },
      { id: "tank_gor", label: "Tank GOR", required: false },
      { id: "tank_ch4_content", label: "Tank CH4 Content", required: false },
      { id: "tank_control_eff", label: "Tank Control Eff", required: false },
      { id: "tank_unit", label: "Tank Unit", required: false },
      { id: "tank_api_gravity", label: "Tank API Gravity", required: false },
      { id: "pneu_count", label: "Pneu Count", required: false },
      { id: "pneu_bleed_rate", label: "Pneu Bleed Rate", required: false },
      { id: "pneu_bleed_unit", label: "Pneu Bleed Unit", required: false },
      { id: "pneu_hours", label: "Pneu Hours", required: false },
      { id: "pneu_ch4_content", label: "Pneu CH4 Content", required: false },
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
      { id: "boiler_eff", label: "Boiler Efficiency (% or fraction)", required: false },
      { id: "trans_loss", label: "Transmission Loss (%)", required: false },
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
      { id: "category", label: "Category", required: true },
      { id: "sub_category", label: "Sub Category", required: false },
      { id: "amount", label: "Amount", required: true },
      { id: "unit", label: "Unit", required: true },
      { id: "emission_factor", label: "Emission Factor", required: true },
      { id: "ef_unit", label: "EF Unit", required: true },
      { id: "co2e", label: "CO2e", required: false },
    ],
    facilities: [
      { id: "name", label: "Facility Name", required: true },
      { id: "location", label: "Location", required: false },
      { id: "description", label: "Description", required: false },
      { id: "activity", label: "Activity", required: false },
      { id: "division", label: "Division", required: false },
      { id: "region", label: "Region", required: false },
      { id: "field", label: "Field", required: false },
      { id: "segment", label: "Segment", required: false },
      { id: "code", label: "Code", required: false },
      { id: "external_id", label: "External ID", required: false },
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
      {
        id: "status",
        label: "Status",
        required: false,
        hint: "Active, Planned",
      },
      {
        id: "start_date",
        label: "Start Date",
        required: false,
        hint: "YYYY-MM-DD",
      },
      {
        id: "end_date",
        label: "End Date",
        required: false,
        hint: "YYYY-MM-DD",
      },
      { id: "investment_amount", label: "Investment", required: false },
      { id: "description", label: "Description", required: false },
    ],
  };

  const currentTemplate = React.useMemo(() => {
    let base = TEMPLATES[type] || [];
    if (type === "activity") {
      return base.filter((t) => {
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
          "process_type",
          "fuel",
          "fuel_type",
          "amount",
          "quantity",
          "unit",
          "factor_type",
          "equipment_id",
          "equipment_name",
        ];
        if (generalFields.includes(t.id)) return true;

        if (selectedTier === "1") return false;

        if (selectedProcess === "all") return true;

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
          pneumatic: [
            "pneu_count",
            "pneu_bleed_rate",
            "pneu_bleed_unit",
            "pneu_hours",
            "pneu_ch4_content",
          ],
          agr: [
            "agr_co2_in",
            "agr_co2_out",
            "agr_unit",
            "agr_ch4_in",
            "agr_ch4_slip",
            "agr_control_eff",
          ],
          dehydrator: [
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
          ],
          fugitive: ["fugitive_method", "fugitive_ppm"],
          indirect_steam: ["boiler_eff", "trans_loss", "heat_unit"],
          stoichiometry: ["carbon_content"],
        };

        const specificFields = processFields[selectedProcess] || [];
        return specificFields.includes(t.id);
      });
    }
    return base;
  }, [type, selectedTier, selectedProcess]);

  const downloadTemplate = async () => {
    if (type === "activity") {
      try {
        const res = await api.get(
          `/emissions/template/csv?tier=${selectedTier}&process=${selectedProcess}`,
          { responseType: "blob" }
        );
        const url = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = `scope1_template_${selectedProcess || "all"}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => window.URL.revokeObjectURL(url), 1000);
      } catch (err) {
        console.error("Template download failed:", err);
        toast.error("Failed to download emissions template.");
      }
      // Use the backend's comprehensive template generator for emissions data
      const baseUrl = import.meta.env.VITE_API_URL || "/api";
      window.location.href = `${baseUrl}/emissions/template/csv?tier=${selectedTier}&process=${selectedProcess}`;
      return;
    }

    const headers = currentTemplate.map((t) => t.id).join(",");

    // Generate a sample row for each process type to show variety
    const sampleRows = Object.keys(PROCESS_TYPES)
      .map((procType, index) => {
        return currentTemplate
          .map((t) => {
            if (t.id === "year") return "2024";
            if (t.id === "month") return "1";
            if (t.id === "activity") return "Exploration & Production";
            if (t.id === "division") return "Production";
            if (t.id === "facility_id") return "Hassi Messaoud";
            if (t.id === "field") return "Bir Berkine";
            if (t.id === "type" || t.id === "process_type") return procType;
            if (t.id === "equipment_id") return `EQ-${100 + index}`;
            if (t.id === "name") return `${PROCESS_TYPES[procType]} Unit`;
            if (t.id === "fuel" || t.id === "fuel_type") {
              if (
                procType === "combustion" ||
                procType === "flaring" ||
                procType === "venting"
              )
                return "Natural Gas";
              if (procType === "mobile") return "Diesel";
              return "-";
            }
            if (t.id === "unit") {
              if (procType === "combustion") return "scf";
              if (procType === "flaring" || procType === "venting") return "m3";
              if (procType === "mobile") return "gal";
              return "tonnes/yr";
            }
            if (t.id === "amount")
              return procType === "mobile" ? "500" : "1000";
            if (t.id === "flare_type")
              return procType === "flaring" ? "elevated" : "-";
            if (t.id === "ch4_content")
              return procType === "flaring" ||
                procType === "venting" ||
                procType === "pneumatic"
                ? "85.5"
                : "-";
            if (t.id === "hhv") return procType === "combustion" ? "1050" : "-";
            if (t.id === "comp_flare_eff")
              return procType === "flaring" || procType === "combustion"
                ? "98.0"
                : "-";
            if (t.id === "hours") return "8760";
            if (t.id === "tank_gor") return procType === "tank" ? "500" : "-";
            if (t.id === "tank_api_gravity")
              return procType === "tank" ? "35" : "-";
            return "";
          })
          .join(",");
      })
      .join("\n");

    let csvContent = `${headers}\n${sampleRows}`;

    if (type === "custom_factors") {
      csvContent = `${headers}\nSpecialized Generator Gas,Natural Gas,scf,53.06,0.001,0.0001,0,5,50,150,combustion`;
    }
    if (type === "production") {
      csvContent = `${headers}\nHassi Messaoud,Exploration & Production,Production,Bir Berkine,2024,1,50000,bbl,12000,mscf`;
    }
    if (type === "mitigation") {
      csvContent = `${headers}\nHassi Messaoud,Solar Farm A,REC,2024,1500,Active,2024-01-01,,500000,Solar panel installation`;
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

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (type === "activity") {
        // For activity, we rely on the background processor
        setStep(3);
      } else {
        parseCSV(selectedFile);
      }
    }
  };

  const parseCSV = (file) => {
    // NEW-05 FIX: use PapaParse for robust CSV parsing (handles quotes and commas in values)
    Papa.parse(file, {
      header: false,
      skipEmptyLines: true,
      preview: 10, // Only parse first 10 rows to save memory on huge files
      complete: (results) => {
        const data = results.data;
        if (!data || data.length === 0) {
          setLoading(false);
          return toast.error("Empty file");
        }

        const csvHeaders = data[0].map((h) => (h || "").trim());
        const dataRows = data
          .slice(1)
          .map((row) => row.map((v) => (v || "").trim()));

        setHeaders(csvHeaders);
        setCsvData(dataRows);

        // Auto-mapping logic
        const initialMapping = {};
        currentTemplate.forEach((t) => {
          const match = csvHeaders.find(
            (h) =>
              h.toLowerCase() === t.id.toLowerCase() ||
              h.toLowerCase() === t.label.toLowerCase() ||
              h.toLowerCase().replace(/[^a-z0-9]/g, "") ===
                t.id.toLowerCase().replace(/[^a-z0-9]/g, ""),
          );
          if (match) initialMapping[t.id] = match;
        });
        setMapping(initialMapping);
        setLoading(false);
        setStep(2);
      },
      error: (error) => {
        setLoading(false);
        toast.error(`Failed to parse CSV: ${error.message}`);
      },
    });
  };


  const handlePreview = () => {
    setLoading(true);

    // Wrap in setTimeout to allow the loader to render before heavy processing
    setTimeout(() => {
      const errors = [];

      // Pre-calculate header indices for performance (O(Columns) instead of O(Rows * Columns * Headers))
      const headerIndexMap = {};
      currentTemplate.forEach((t) => {
        const header = mapping[t.id];
        headerIndexMap[t.id] = headers.indexOf(header);
      });

      const records = csvData.map((row, rowIndex) => {
        const record = {};
        currentTemplate.forEach((t) => {
          const index = headerIndexMap[t.id];
          if (index !== -1 && index !== undefined) record[t.id] = row[index];
        });

        // Validation checks
        if (record.type && !PROCESS_TYPES[record.type.toLowerCase()]) {
          errors.push(
            `Row ${rowIndex + 1}: Invalid Process Type "${record.type}"`,
          );
        }
        if (
          record.process_type &&
          !PROCESS_TYPES[record.process_type.toLowerCase()]
        ) {
          errors.push(
            `Row ${rowIndex + 1}: Invalid Process Type "${record.process_type}"`,
          );
        }

        if (record.activity && !HIERARCHY[record.activity]) {
          errors.push(
            `Row ${rowIndex + 1}: Unknown Activity "${record.activity}"`,
          );
        } else if (
          record.activity &&
          record.division &&
          !HIERARCHY[record.activity].includes(record.division)
        ) {
          errors.push(
            `Row ${rowIndex + 1}: Division "${record.division}" does not belong to "${record.activity}"`,
          );
        }

        return record;
      });

      setMappedRecords(records);
      setValidationErrors(errors);
      setLoading(false);
      setStep(3);
    }, 50);
  };

  const handleImport = async () => {
    if (
      validationErrors.length > 0 &&
      type !== "activity" &&
      type !== "activity_scope2" &&
      type !== "activity_scope3"
    ) {
      toast.error("Please fix validation errors before importing.");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append(
        "global_factor_type",
        selectedTier === "1" ? "default" : "custom",
      );
      formData.append("mapping", JSON.stringify(mapping));

      let scopeStr = type;
      if (type === "activity") scopeStr = "1";
      if (type === "activity_scope2") scopeStr = "2";
      if (type === "activity_scope3") scopeStr = "3";

      formData.append("scope", scopeStr);

      const res = await api.post("/emissions/upload/start", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const jobId = res.data.job_id;
      setUploadJobId(jobId);

      // Start polling with cleanup protection
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await api.get(`/emissions/upload/status/${jobId}`);
          setUploadStatus(statusRes.data);

          if (
            statusRes.data.status === "completed" ||
            statusRes.data.status === "failed"
          ) {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setLoading(false);
            if (statusRes.data.status === "completed") {
              toast.success(
                `Import complete! Processed ${statusRes.data.processed} rows.`,
              );
              // Trigger success callback after clicking "Done" inside the UI
            } else {
              toast.error(`Import failed.`);
            }
          }
        } catch {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setLoading(false);
          toast.error("Error checking upload status.");
        }
      }, 1000);
    } catch (error) {
      setLoading(false);
      console.error("Import failed:", error);
      const serverError = error.response?.data?.error || "Server error";
      toast.error(`Import failed: ${serverError}`);
    }
  };

  const isMappingValid = () => {
    return currentTemplate
      .filter((t) => t.required)
      .every((t) => mapping[t.id]);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Bulk Import: ${type === "sources" ? "Equipment" : type === "custom_factors" ? "Custom Factors" : "Activity Data"}`}
      maxWidth="700px"
    >
      <div className="[display:flex] [flex-direction:column] [gap:20px]">
        {step === 0 && type === "activity" && (
          <div className="upload-mode-selection p-[20px]!">
            <h3
              className="mb-[24px]! text-center! text-[color:var(--text-primary)]!"
            >
              1. Select Calculation Tier
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
              }}
            >
              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="mode-card"
                onClick={() => {
                  setSelectedTier("1");
                  setStep(0.5);
                }}
                style={{
                  padding: "24px",
                  border: "2px solid",
                  borderColor:
                    selectedTier === "1" ? "#10b981" : "var(--border-color)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  backgroundColor:
                    selectedTier === "1"
                      ? "rgba(16, 185, 129, 0.05)"
                      : "transparent",
                }}
              >
                <h4
                  className="m-[0_0_8px_0]! text-[color:#2e7d32]! text-center!"
                >
                  Tier 1
                </h4>
                <p
                  className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]! text-center!"
                >
                  Standard activity data using default API emission factors.
                </p>
              </div>
              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="mode-card"
                onClick={() => {
                  setSelectedTier("3");
                  setStep(0.5);
                }}
                style={{
                  padding: "24px",
                  border: "2px solid",
                  borderColor:
                    selectedTier === "3" ? "#10b981" : "var(--border-color)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  backgroundColor:
                    selectedTier === "3"
                      ? "rgba(16, 185, 129, 0.05)"
                      : "transparent",
                }}
              >
                <h4
                  className="m-[0_0_8px_0]! text-[color:#2e7d32]! text-center!"
                >
                  Tier 3
                </h4>
                <p
                  className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]! text-center!"
                >
                  Detailed engineering inputs and custom gas compositions.
                </p>
              </div>
            </div>
          </div>
        )}

        {step === 0.5 && type === "activity" && (
          <div className="upload-mode-selection p-[20px]!">
            <h3
              className="mb-[24px]! text-center! text-[color:var(--text-primary)]!"
            >
              2. Select Process Scope
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
                marginBottom: "24px",
              }}
            >
              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="mode-card"
                onClick={() => {
                  setSelectedProcess("all");
                  setStep(1);
                }}
                style={{
                  padding: "24px",
                  border: "2px solid var(--border-color)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                <h4
                  className="m-[0_0_8px_0]! text-[color:#2e7d32]! text-center!"
                >
                  All Processes
                </h4>
                <p
                  className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]! text-center!"
                >
                  Upload a comprehensive dataset containing multiple process
                  types at once.
                </p>
              </div>
              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="mode-card"
                onClick={() => {
                  setStep(0.75);
                }}
                style={{
                  padding: "24px",
                  border: "2px solid var(--border-color)",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                <h4
                  className="m-[0_0_8px_0]! text-[color:#2e7d32]! text-center!"
                >
                  Choose by Process
                </h4>
                <p
                  className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]! text-center!"
                >
                  Download a targeted template for one specific process (e.g.
                  Flaring).
                </p>
              </div>
            </div>
            <div className="text-center!">
              <button
                className="action-btn secondary"
                onClick={() => setStep(0)}
              >
                Back
              </button>
            </div>
          </div>
        )}

        {step === 0.75 && type === "activity" && (
          <div className="upload-mode-selection p-[20px]!">
            <h3
              className="mb-[24px]! text-center! text-[color:var(--text-primary)]!"
            >
              3. Choose Specific Process
            </h3>
            <label
              className="block! mb-[8px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]!"
            >
              Which process type are you uploading data for?
            </label>
            <NativeSelect
              className="mole-input"
              value={selectedProcess}
              onChange={(e) => {
                setSelectedProcess(e.target.value);
              }}
              style={{
                padding: "12px",
                width: "100%",
                borderRadius: "6px",
                border: "1px solid var(--border-color)",
                marginBottom: "20px",
              }}
            >
              <option value="all" disabled>
                Select Process Type...
              </option>
              {Object.entries(PROCESS_TYPES).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </NativeSelect>
            <div
              className="flex! gap-[12px]! justify-end!"
            >
              <button
                className="action-btn secondary"
                onClick={() => setStep(0.5)}
              >
                Back
              </button>
              <button
                className="action-btn"
                onClick={() => setStep(1)}
                disabled={selectedProcess === "all"}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 1 && (
          <>
            {type === "activity" && (
              <div
                className="mb-[16px]! flex! justify-between! items-center!"
              >
                <span className="font-semibold! text-[color:#2e7d32]!">
                  {selectedTier === "1"
                    ? "Tier 1 (Default Factors)"
                    : selectedProcess === "all"
                      ? "Tier 3 (All Processes)"
                      : `Tier 3 (${PROCESS_TYPES[selectedProcess]})`}
                </span>
                <button
                  className="action-btn secondary p-[6px_12px]! text-[length:0.8rem]!"
                 
                  onClick={() => setStep(0)}
                >
                  Change Type
                </button>
              </div>
            )}
            <div role="button" tabIndex={0} onKeyDown={activateOnKey}
              className="[border:2px_dashed_rgba(16,_185,_129,_0.3)] [&&]:[border-radius:var(--radius-md)] [padding:40px] [text-align:center] [background:rgba(16,_185,_129,_0.03)] [cursor:pointer] [transition:all_0.3s_ease] hover:[border-color:var(--color-green-500)] hover:[background:rgba(16,_185,_129,_0.08)]"
              onClick={() => fileInputRef.current.click()}
            >
              <Upload
                size={48}
                className="text-[color:#2e7d32]! mb-[16px]!"
              />
              <h3>Click or Drag CSV File</h3>
              <p className="text-[color:var(--text-secondary)]! mt-[8px]!">
                Standard CSV format with headers
              </p>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".csv"
                className="hidden!"
              />

              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="[display:flex] [align-items:center] [gap:8px] [color:var(--color-green-700)] [font-size:var(--text-base)] [font-weight:500] [padding:6px_12px] [border:1px_dashed_var(--color-green-500)] [&&]:[border-radius:var(--radius-sm)] [background:rgba(16,_185,_129,_0.05)] [transition:all_0.2s_ease] [cursor:pointer] hover:[background:rgba(16,_185,_129,_0.1)] hover:[transform:translateY(-1px)]"
                onClick={(e) => {
                  e.stopPropagation();
                  downloadTemplate();
                }}
                style={{ marginTop: type === "activity" ? "16px" : "0" }}
              >
                <FileText size={14} />
                <span>Download targeted CSV template</span>
              </div>

              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                className="[margin-top:12px] [display:flex] [align-items:center] [gap:8px] [color:var(--text-secondary)] [font-size:var(--text-sm)] [cursor:pointer] [text-decoration:underline] [opacity:0.8] hover:[opacity:1] hover:[color:var(--color-green-700)]"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowCheatSheet(!showCheatSheet);
                }}
              >
                <Info size={14} />
                <span>
                  {showCheatSheet
                    ? "Hide System Identifiers"
                    : "Show System Identifiers (Cheat Sheet)"}
                </span>
              </div>

              {showCheatSheet && (
                <div role="presentation"
                  className="[margin-top:16px] [background:#f3f4f6] [border-radius:var(--radius-md)] [padding:16px] [text-align:left] [display:flex] [flex-direction:column] [gap:12px] [border:1px_solid_rgba(0,_0,_0,_0.05)]"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="cheat-section">
                    <strong>Activities &amp; Divisions:</strong>
                    <ul>
                      {Object.entries(HIERARCHY).map(([act, divs]) => (
                        <li key={act}>
                          {act}: <i>{divs.join(", ")}</i>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="cheat-section">
                    <strong>Process Types (Codes):</strong>
                    <div className="[display:flex] [flex-wrap:wrap] [gap:6px] [margin-top:4px]">
                      {Object.keys(PROCESS_TYPES).map((t) => (
                        <span key={t} className="[background:white] [padding:2px_8px] [border-radius:var(--radius-sm)] [border:1px_solid_rgba(0,_0,_0,_0.1)] [font-family:monospace] [font-size:var(--text-sm)] [color:var(--sonatrach-orange)]">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="cheat-section">
                    <strong>Common Units:</strong>
                    <div className="[display:flex] [flex-wrap:wrap] [gap:6px] [margin-top:4px]">
                      {VALID_UNITS.map((u) => (
                        <span key={u} className="[background:white] [padding:2px_8px] [border-radius:var(--radius-sm)] [border:1px_solid_rgba(0,_0,_0,_0.1)] [font-family:monospace] [font-size:var(--text-sm)] [color:var(--sonatrach-orange)]">
                          {u}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="cheat-section">
                    <strong>Engineering Params:</strong>
                    <ul className="text-[length:0.8rem]! opacity-[0.9]!">
                      <li>
                        <b>Flare Type:</b> elevated, enclosed_ground, pit
                      </li>
                      <li>
                        <b>HHV:</b> Natural Gas (~1050), Diesel (~138000)
                      </li>
                      <li>
                        <b>Efficiency:</b> 98.0 for Flaring default
                      </li>
                      <li>
                        <b>GOR:</b> Gas-Oil Ratio for Tank Flash
                      </li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div className="[display:flex] [align-items:center] [justify-content:center] [gap:12px] [padding:12px] [background:white] [border-radius:var(--radius-md)] [border:1px_solid_rgba(0,_0,_0,_0.1)]">
              <FileText size={20} className="text-[color:#2e7d32]!" />
              <span>
                {file?.name} ({csvData.length} records detected)
              </span>
            </div>

            <div className="[max-height:300px] [overflow-y:auto] [border:1px_solid_rgba(0,_0,_0,_0.05)] [&&]:[border-radius:var(--radius-md)] [padding:16px] [background:#f9fafb]">
              <h4
                className="mb-[16px]! flex! items-center! gap-[8px]!"
              >
                <Loader2
                  size={16}
                  className="spin"
                  style={{ display: loading ? "block" : "none" }}
                />
                Map CSV Columns to System Fields
              </h4>
              <div className="mapping-grid">
                {currentTemplate.map((t) => (
                  <div key={t.id} className="mapping-row">
                    <div className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)]">
                      {t.label}{" "}
                      {t.required && (
                        <span className="text-[color:#b91c1c]!">*</span>
                      )}
                      {t.hint && (
                        <div
                          className="text-[length:0.75rem]! font-normal! opacity-[0.6]!"
                        >
                          {t.hint}
                        </div>
                      )}
                    </div>
                    <NativeSelect
                      className="mapping-select"
                      value={mapping[t.id] || ""}
                      onChange={(e) =>
                        setMapping({ ...mapping, [t.id]: e.target.value })
                      }
                    >
                      <option value="">-- Discard Field --</option>
                      {headers.map((h) => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                ))}
              </div>
            </div>

            <div className="[font-size:var(--text-sm)] [color:var(--text-secondary)] [display:flex] [align-items:center] [gap:6px]">
              <Info size={14} />
              <span>
                Make sure units (e.g. m3, bbl) and process types match the
                system identifiers.
              </span>
            </div>

            <div className="[display:flex] [justify-content:flex-end] [gap:12px] [margin-top:20px]">
              <button
                className="action-btn bg-[color:var(--text-secondary)]!"
               
                onClick={() => setStep(1)}
              >
                Back
              </button>
              <button
                className="action-btn"
                disabled={!isMappingValid()}
                onClick={handlePreview}
              >
                Preview Data
              </button>
            </div>
          </>
        )}

        {step === 3 && type === "activity" && (
          <BulkImportModalUploadProgressContainer
        file={file}
        handleImport={handleImport}
        loading={loading}
        onClose={onClose}
        onImportSuccess={onImportSuccess}
        setStep={setStep}
        uploadJobId={uploadJobId}
        uploadStatus={uploadStatus}
      />
        )}

        {step === 3 && type !== "activity" && (
          <>
            {!uploadJobId ? (
              <>
                <div className="preview-header">
                  <h4>
                    <CheckCircle2
                      size={18}
                      style={{
                        color: validationErrors.length ? "#b91c1c" : "#2e7d32",
                      }}
                    />{" "}
                    Preview & Validate
                  </h4>
                  <span>{mappedRecords.length} records mapped</span>
                </div>

                {validationErrors.length > 0 && (
                  <div className="validation-error-box">
                    <h5>
                      <AlertCircle size={16} /> Validation Errors Found
                    </h5>
                    <ul>
                      {validationErrors.slice(0, 5).map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                      {validationErrors.length > 5 && (
                        <li>...and {validationErrors.length - 5} more</li>
                      )}
                    </ul>
                    <p className="mt-[8px]! text-[length:0.75rem]!">
                      Please go back and check your CSV identifiers.
                    </p>
                  </div>
                )}

                <div className="[max-height:250px] [overflow-y:auto] [overflow-x:auto] [border-radius:var(--radius-md)] [border:1px_solid_rgba(0,_0,_0,_0.1)]">
                  <table className="preview-table">
                    <thead>
                      <tr>
                        {currentTemplate.map((t) => (
                          <th key={t.id}>{t.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mappedRecords.slice(0, 10).map((rec, i) => (
                        <tr key={i}>
                          {currentTemplate.map((t) => {
                            const value = rec[t.id];
                            const isHierarchyError =
                              (t.id === "activity" || t.id === "division") &&
                              rec.activity &&
                              rec.division &&
                              !HIERARCHY[rec.activity]?.includes(rec.division);

                            return (
                              <td
                                key={t.id}
                                style={{
                                  color: isHierarchyError
                                    ? "#b91c1c"
                                    : "inherit",
                                }}
                              >
                                {value || "-"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {mappedRecords.length > 10 && (
                    <div className="[text-align:center] [padding:8px] [font-size:var(--text-sm)] [color:var(--text-secondary)] [background:#f9fafb] [border-top:1px_solid_rgba(0,_0,_0,_0.05)]">
                      Showing first 10 records...
                    </div>
                  )}
                </div>

                <div className="[display:flex] [justify-content:flex-end] [gap:12px] [margin-top:20px]">
                  <button
                    className="action-btn bg-[color:var(--text-secondary)]!"
                   
                    onClick={() => setStep(2)}
                  >
                    Back to Mapping
                  </button>
                  <button
                    className="action-btn"
                    disabled={validationErrors.length > 0 || loading}
                    onClick={handleImport}
                  >
                    {loading ? (
                      <Loader2 size={16} className="spin" />
                    ) : (
                      "Confirm & Import Store"
                    )}
                  </button>
                </div>
              </>
            ) : (
              <div className="[width:100%] [margin-top:16px] [display:flex] [flex-direction:column] [align-items:center] p-[20px]!">
                {uploadStatus ? (
                  <>
                    <div
                      className="flex! justify-between! w-full! mb-[8px]!"
                    >
                      <span className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-primary)]">
                        {uploadStatus.status === "completed"
                          ? "Import Complete!"
                          : uploadStatus.status === "failed"
                            ? "Import Failed"
                            : "Processing..."}
                      </span>
                      <span className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-primary)]">
                        {Math.round(uploadStatus.progress)}%
                      </span>
                    </div>
                    <div className="[width:100%] [height:12px] [background:#e5e7eb] [border-radius:var(--radius-sm)] [overflow:hidden] [margin-top:4px]">
                      <div
                        className="[height:100%] [border-radius:var(--radius-sm)] [transition:width_0.3s_ease]"
                        style={{
                          width: `${uploadStatus.progress}%`,
                          background:
                            uploadStatus.status === "failed"
                              ? "#ef4444"
                              : "#10b981",
                        }}
                      ></div>
                    </div>
                    <div
                      className="[font-size:var(--text-sm)] [color:var(--text-secondary)] mt-[8px]! text-center!"
                     
                    >
                      Processed {uploadStatus.processed} of {uploadStatus.total}{" "}
                      rows
                    </div>

                    {uploadStatus.skipped_count > 0 && (
                      <div
                        className="mt-[16px]! p-[12px]! bg-[color:#fff1f2]! rounded-[8px]! [border:1px_solid_#fecdd3]! w-full!"
                      >
                        <h5
                          className="text-[color:#be123c]! m-[0_0_8px_0]! flex! items-center! gap-[6px]!"
                        >
                          <AlertCircle size={16} />
                          Skipped Rows ({uploadStatus.skipped_count})
                        </h5>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: "20px",
                            fontSize: "0.85rem",
                            color: "#9f1239",
                            maxHeight: "100px",
                            overflowY: "auto",
                          }}
                        >
                          {uploadStatus.skipped_preview
                            ?.slice(0, 5)
                            .map((skip, idx) => (
                              <li key={idx}>
                                Row {skip.row}: {skip.reason}
                              </li>
                            ))}
                          {uploadStatus.skipped_count > 5 && (
                            <li>
                              ...and {uploadStatus.skipped_count - 5} more
                              skipped rows
                            </li>
                          )}
                        </ul>
                      </div>
                    )}

                    {(uploadStatus.status === "completed" ||
                      uploadStatus.status === "failed") && (
                      <div className="mt-[24px]! text-center!">
                        <button
                          className="action-btn"
                          onClick={() => {
                            if (onImportSuccess) onImportSuccess();
                            onClose();
                          }}
                        >
                          Done
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div
                    className="flex! flex-col! items-center! gap-[12px]!"
                  >
                    <Loader2
                      size={32}
                      className="spin text-[color:#2e7d32]!"
                     
                    />
                    <span className="text-[color:var(--text-secondary)]!">
                      Initializing background job...
                    </span>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
};

export default BulkImportModal;
