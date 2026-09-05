import React, { useState, useEffect } from "react";
import api from "../api";
import CustomDropdown from "./CustomDropdown";
import { useToast } from "./Toast";
import { formatNumber } from "../utils/formatters";
import "./ScopeTables.css";
import "./Scope1Form.css";

// Sub-components
import Scope1ImportWizard from "./Scope1ImportWizard";
import { Upload, Trash2 } from "lucide-react";
import CombustionForm from "./scope1/CombustionForm";
import DrillingForm from "./scope1/DrillingForm";
import CompletionsForm from "./scope1/CompletionsForm";
import UnloadingForm from "./scope1/UnloadingForm";
import BlowdownForm from "./scope1/BlowdownForm";
import AGRForm from "./scope1/AGRForm";
import DehydratorForm from "./scope1/DehydratorForm";
import PneumaticsForm from "./scope1/PneumaticsForm"; // Can use for tank as well or separate
import TankForm from "./scope1/TankForm";
import FugitivesForm from "./scope1/FugitivesForm";
import GasCompositionCalculator from "./GasCompositionCalculator";
import {
  API_FACTORS,
  PROCESS_GROUPS,
  PROCESS_TYPES as PROCESS_TYPES_MAP,
} from "../utils/EmissionFactors";
import {
  getProcessTypesForSegment,
  formatUncertainty,
  getSegmentColor,
  getSegmentBgColor,
  convertActivityData,
} from "../utils/emissionFactorsAPI";

const PROCESS_TYPES = PROCESS_TYPES_MAP;

const Scope1Form = () => {
  const toast = useToast();
  const [loading, setLoading] = useState(false);

  // Core Identity State
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [facilityId, setFacilityId] = useState("");
  const [activity, setActivity] = useState("");
  const [division, setDivision] = useState("");
  const [field, setField] = useState("");

  const [processType, setProcessType] = useState("combustion");
  const [streamType, setStreamType] = useState("Upstream"); // 'Upstream', 'Midstream', 'Downstream'
  const [groupName, setGroupName] = useState("");
  const [equipmentId, setEquipmentId] = useState("");

  // Dynamic Form Data State
  const [formData, setFormData] = useState({});

  // Hoisted State for Factor Selection
  const [sourceType, setSourceType] = useState("default"); // 'default', 'custom', 'specific'
  const [fuelOptions, setFuelOptions] = useState([]);
  const [customFactors, setCustomFactors] = useState([]);

  // Specific Factors State
  const [specFactors, setSpecFactors] = useState({
    co2: "",
    co2Unit: "kg/m3",
    ch4: "",
    ch4Unit: "kg/m3",
    n2o: "",
    n2oUnit: "kg/m3",
    co: "",
    coUnit: "kg/m3",
  });

  // Per-GHG uncertainty: null means 'not applicable' (custom / specific)
  const [uncertainty, setUncertainty] = useState({
    co2: null,
    ch4: null,
    n2o: null,
  });
  const [userUncertainty, setUserUncertainty] = useState({
    co2: "",
    ch4: "",
    n2o: "",
  });
  const [meterUncertaintyPct, setMeterUncertaintyPct] = useState("2.0"); // Default Tier 3 ±2.0%
  const [gcUncertaintyPct, setGcUncertaintyPct] = useState("");

  const [facilities, setFacilities] = useState([]);
  const [emissionSources, setEmissionSources] = useState([]);
  const [emissionSourceId, setEmissionSourceId] = useState("");
  const [entries, setEntries] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [showGasCalc, setShowGasCalc] = useState(false);
  const [processTypesAvailable, setProcessTypesAvailable] = useState([]); // API 2021: Dynamic process types
  const [importModal, setImportModal] = useState({
    isOpen: false,
    type: "activity",
  });
  const RECORDS_PER_PAGE = 10;

  // Table filter state
  const [filterYear, setFilterYear] = useState("");
  const [filterProcess, setFilterProcess] = useState("");
  const [filterSearch, setFilterSearch] = useState("");

  useEffect(() => {
    loadFacilities();
    loadEntries();
    loadCustomFactors();
    loadEmissionSources();
  }, []);

  // BUG-UI-07 FIX: Re-load entries whenever any filter or page changes
  useEffect(() => {
    loadEntries();
  }, [filterYear, filterProcess, filterSearch, currentPage]);

  // Auto-populate activity, division, and field when facility is selected
  useEffect(() => {
    if (facilityId && facilities.length > 0) {
      const selectedFacility = facilities.find(
        (f) => f.id.toString() === facilityId,
      );
      if (selectedFacility) {
        setActivity(selectedFacility.activity || "");
        setDivision(selectedFacility.division || "");
        setField(selectedFacility.field || "");
      }
    } else {
      setActivity("");
      setDivision("");
      setField("");
    }
  }, [facilityId, facilities]);

  // Auto-populate Equipment ID and Group Name from selected emission source
  useEffect(() => {
    if (emissionSourceId && emissionSources.length > 0) {
      const selectedSource = emissionSources.find(
        (s) => s.id.toString() === emissionSourceId,
      );
      if (selectedSource) {
        if (selectedSource.equipment_id)
          setEquipmentId(selectedSource.equipment_id);
        if (selectedSource.name) setGroupName(selectedSource.name);
      }
    }
  }, [emissionSourceId, emissionSources]);

  // API 2021: Load available process types when segment changes
  useEffect(() => {
    const loadProcessTypes = async () => {
      if (!streamType) return;
      const types = await getProcessTypesForSegment(streamType.toLowerCase());
      setProcessTypesAvailable(types);
    };
    loadProcessTypes();
  }, [streamType]);

  const loadCustomFactors = async () => {
    try {
      const res = await api.get("/custom-factors");
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setCustomFactors(data);
    } catch (error) {
      console.error("Failed to load custom factors:", error);
    }
  };

  // Filter fuels based on process type
  useEffect(() => {
    if (!processType) return;

    if (sourceType === "default" || sourceType === "specific") {
      const options = Object.keys(API_FACTORS)
        .filter((key) => {
          const factor = API_FACTORS[key];

          // Specific logic for Fugitives (Pipeline vs Standard)
          if (processType === "fugitive") {
            const isPipeline = formData.fugitive_method === "pipeline";
            const hasPipelineTag =
              factor.usage && factor.usage.includes("fugitive_pipeline");
            const hasFugitiveTag =
              factor.usage && factor.usage.includes("fugitive");

            if (isPipeline) return hasPipelineTag;
            return hasFugitiveTag;
          }

          // Standard usage check for other processes
          const usageMatch = factor.usage && factor.usage.includes(processType);
          const streamMatch = !factor.stream || factor.stream === streamType;

          return usageMatch && streamMatch;
        })
        .map((k) => ({
          value: k,
          label: k,
          factor: API_FACTORS[k],
        }));
      setFuelOptions(options);
    } else {
      const options = customFactors
        .filter(
          (f) => !f.usage || f.usage.includes(processType) || f.usage === "All",
        )
        .map((f) => ({ value: f.id.toString(), label: f.factor_name }));
      setFuelOptions(options);
    }
  }, [
    processType,
    sourceType,
    customFactors,
    streamType,
    formData.fugitive_method,
  ]);

  // Custom renderOption for emission factors with segment badges and uncertainty
  const renderFactorOption = (option) => {
    if (!option.factor) return option.label;

    const factor = option.factor;
    const segment = factor.segment || factor.stream;
    const uncertainty = factor.uncertainty;
    const maxUncertainty = uncertainty
      ? Math.max(
          uncertainty.co2 || 0,
          uncertainty.ch4 || 0,
          uncertainty.n2o || 0,
        )
      : 0;

    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          gap: "8px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            flex: 1,
            minWidth: 0,
          }}
        >
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {option.label}
          </span>
          {segment && (
            <span
              style={{
                padding: "2px 5px",
                borderRadius: "3px",
                fontSize: "0.6rem",
                fontWeight: 600,
                flexShrink: 0,
                background: getSegmentBgColor(segment),
                color: getSegmentColor(segment),
              }}
            >
              {segment}
            </span>
          )}
        </div>
        {uncertainty && maxUncertainty > 0 && (
          <span
            style={{
              fontSize: "0.65rem",
              color: "#9ca3af",
              fontWeight: 500,
              flexShrink: 0,
            }}
            title={`Uncertainty: CO₂ ${formatUncertainty(uncertainty.co2)}, CH₄ ${formatUncertainty(uncertainty.ch4)}, N₂O ${formatUncertainty(uncertainty.n2o)}`}
          >
            {formatUncertainty(maxUncertainty)}
          </span>
        )}
      </div>
    );
  };

  // Handle Resetting Fuel on Context Change
  useEffect(() => {
    setFormData((prev) => ({ ...prev, fuel: "" }));
  }, [processType]);

  useEffect(() => {
    // If switching to Custom, clear fuel (IDs don't match default keys)
    // If switching from Custom to Default/Specific, clear fuel
    // If switching between Default and Specific, KEEP fuel (shared options)
    setFormData((prev) => {
      const isCustomId = !isNaN(parseInt(prev.fuel)); // Rough check, assuming default keys are strings
      if (sourceType === "custom" && !isCustomId) return { ...prev, fuel: "" };
      if (
        (sourceType === "default" || sourceType === "specific") &&
        isCustomId &&
        prev.fuel
      )
        return { ...prev, fuel: "" };
      return prev;
    });
  }, [sourceType]);

  // Auto-populate Specific Factors
  useEffect(() => {
    if (
      sourceType === "specific" &&
      formData.fuel &&
      API_FACTORS[formData.fuel]
    ) {
      const f = API_FACTORS[formData.fuel];
      setSpecFactors({
        co2: f.co2 || 0,
        co2Unit: f.unit || "kg/m3",
        ch4: f.ch4 || 0,
        ch4Unit: f.unit || "kg/m3",
        n2o: f.n2o || 0,
        n2oUnit: f.unit || "kg/m3",
        co: f.co || 0,
        coUnit: f.unit || "kg/m3",
      });
    }

    // Auto-populate Uncertainty
    let factorToUse = null;

    // 1. Combustion / General Fuel / Any selected from main dropdown
    if (formData.fuel) {
      // Try direct key match first
      if (API_FACTORS[formData.fuel]) {
        factorToUse = API_FACTORS[formData.fuel];
      }
      // Fallback: Try matching by 'code' property for custom forms (Completions/Unloading)
      else {
        const found = Object.values(API_FACTORS).find(
          (f) => f.code === formData.fuel,
        );
        if (found) factorToUse = found;
      }
    }
    // 2. Drilling (Mud Degassing) - implicit factor based on mud type
    else if (processType === "drilling") {
      const mudType = formData.mud_type || "water";
      const mudKey =
        mudType === "oil"
          ? "Drilling - Mud Degassing (Oil Based)"
          : "Drilling - Mud Degassing (Water Based)";
      if (API_FACTORS[mudKey]) {
        factorToUse = API_FACTORS[mudKey];
      }
    }

    updateUncertaintyFromFactor(factorToUse);
  }, [sourceType, formData.fuel, processType, formData.mud_type]);

  const updateUncertaintyFromFactor = (f) => {
    if (!f || !f.uncertainty) {
      setUncertainty({ co2: null, ch4: null, n2o: null });
      return;
    }
    setUncertainty({
      co2: f.uncertainty.co2 || null,
      ch4: f.uncertainty.ch4 || null,
      n2o: f.uncertainty.n2o || null,
    });
  };

  useEffect(() => {
    loadEntries();
  }, [currentPage]);

  // Reset specific form data when process type changes
  useEffect(() => {
    setFormData({});
  }, [processType]);

  const loadFacilities = async () => {
    try {
      const res = await api.get("/facilities/");
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setFacilities(data);
    } catch (error) {
      console.error("Failed to load facilities:", error);
      toast.error("Failed to load regions");
    }
  };

  const loadEmissionSources = async () => {
    try {
      const res = await api.get("/sources");
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setEmissionSources(data);
    } catch (error) {
      console.error("Failed to load emission sources:", error);
    }
  };

  const exportToCSV = (data, filename) => {
    if (!data || data.length === 0) {
      toast.error("No data to export");
      return;
    }
    const headers = [
      "Date",
      "Activity",
      "Division",
      "Field",
      "Group",
      "Equipment ID",
      "Process",
      "Fuel/Activity",
      "Factor Type",
      "Quantity",
      "Unit",
      "CO2 (t)",
      "CH4 (t)",
      "N2O (t)",
      "Total (tCO2e)",
      "Status",
    ];
    const rows = data.map((e) => [
      `${e.year}-${String(e.month).padStart(2, "0")}`,
      e.activity || "",
      e.division || "",
      e.field || "",
      e.group || "",
      e.equipment_id || "",
      PROCESS_TYPES[e.process || e.process_type]?.label ||
        e.process ||
        e.process_type ||
        "",
      e.fuel || e.fuel_type || e.activity_data_label || "",
      e.factor_source === "default" ? "Default" : "Specific",
      e.amount || e.quantity || "",
      e.unit || "",
      e.co2_emissions || 0,
      e.ch4_emissions || 0,
      e.n2o_emissions || 0,
      e.co2e_total || 0,
      e.status || "",
    ]);
    const csv = [headers, ...rows]
      .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${data.length} records`);
  };

  const getEmissionSourceOptions = () => {
    const opts = [{ value: "", label: "Select Emission Source..." }];
    // Filter sources by selected facility if one is chosen
    const filtered = facilityId
      ? emissionSources.filter(
          (s) => s.facility_id && s.facility_id.toString() === facilityId,
        )
      : emissionSources;
    filtered.forEach((s) => {
      opts.push({
        value: s.id.toString(),
        label: s.name || s.equipment_id || `Source #${s.id}`,
        subLabel: [s.type, s.equipment_id].filter(Boolean).join(" · "),
      });
    });
    return opts;
  };

  const loadEntries = async () => {
    setLoading(true);
    try {
      // BUG-UI-07 FIX: Include all active filter params in the API request
      const filterParams = new URLSearchParams({
        scope: 1,
        limit: RECORDS_PER_PAGE,
        offset: (currentPage - 1) * RECORDS_PER_PAGE,
        ...(filterYear && { year: filterYear }),
        ...(filterProcess && { process: filterProcess }),
        ...(filterSearch && { search: filterSearch }),
      });
      const res = await api.get(`/emissions?${filterParams}`);

      // Safe handling of response data
      let allEntries = [];
      if (Array.isArray(res.data)) {
        allEntries = res.data;
      } else if (res.data && Array.isArray(res.data.data)) {
        allEntries = res.data.data;
      } else if (res.data && Array.isArray(res.data.emissions)) {
        allEntries = res.data.emissions;
      } else if (res.data && typeof res.data === "object") {
        const possibleArray = Object.values(res.data).find((val) =>
          Array.isArray(val),
        );
        allEntries = possibleArray || [];
      }

      setEntries(allEntries);

      const totalCount =
        res.headers["x-total-count"] || (res.data && res.data.total) || 0;
      if (totalCount) {
        setTotalPages(Math.ceil(parseInt(totalCount) / RECORDS_PER_PAGE));
      } else {
        setTotalPages(Math.ceil(allEntries.length / RECORDS_PER_PAGE) || 1);
      }
    } catch (error) {
      console.error("Failed to load entries:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFormChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddEntry = async (status = "Verified") => {
    // Validate identity fields
    if (!year || !month || !facilityId || !processType) {
      toast.warning(
        "Please fill in all identity fields (Year, Month, Region, Process)",
      );
      return;
    }

    // Validate fuel/factor selection
    if (
      (sourceType === "default" || sourceType === "custom") &&
      !formData.fuel
    ) {
      toast.warning("Please select a fuel or emission factor");
      return;
    }

    // Validate activity data (amount/quantity)
    const amount = formData.amount || formData.quantity;
    const isUpstreamEng =
      sourceType === "specific" &&
      [
        "drilling",
        "completions",
        "unloading",
        "agr",
        "dehydrator",
        "venting",
        "blowdown",
      ].includes(processType);

    if (!isUpstreamEng && (!amount || parseFloat(amount) <= 0)) {
      toast.warning(
        "Please enter a valid activity amount/quantity greater than 0",
      );
      return;
    }

    // Strict validation for Tier 3 (Engineering / Specific) inputs
    if (sourceType === "specific") {
      if (
        ["combustion", "stationary_combustion", "flaring"].includes(processType)
      ) {
        if (!formData.hhv || parseFloat(formData.hhv) <= 0) {
          toast.warning(
            "Higher Heating Value (HHV) is required and must be > 0 for specific factor mode",
          );
          return;
        }
        if (
          ["combustion", "stationary_combustion"].includes(processType) &&
          (formData.combustion_efficiency === undefined ||
            formData.combustion_efficiency === null ||
            formData.combustion_efficiency === "")
        ) {
          toast.warning(
            "Combustion efficiency (%) is required for stationary combustion",
          );
          return;
        }
      } else if (processType === "unloading") {
        if (
          !formData.unload_depth ||
          !formData.unload_diameter ||
          !formData.unload_pressure ||
          !formData.unload_time ||
          !formData.unload_events
        ) {
          toast.warning(
            "All well unloading parameters (depth, diameter, pressure, time, events) are required",
          );
          return;
        }
        if (
          formData.ch4_content === undefined ||
          formData.ch4_content === null ||
          formData.ch4_content === ""
        ) {
          toast.warning("Gas CH4 content (%) is required for well unloading");
          return;
        }
      } else if (processType === "completions") {
        if (
          !formData.comp_volume ||
          !formData.comp_pressure ||
          !formData.comp_events
        ) {
          toast.warning(
            "Well completions parameters (volume, pressure, events) are required",
          );
          return;
        }
        if (
          formData.comp_ch4_content === undefined &&
          formData.ch4_content === undefined
        ) {
          toast.warning("Gas CH4 content (%) is required for well completions");
          return;
        }
      } else if (processType === "blowdown" || processType === "venting") {
        if (
          !formData.blowdown_volume ||
          !formData.blowdown_pressure ||
          !formData.blowdown_events
        ) {
          toast.warning(
            "Blowdown parameters (volume, pressure, events) are required",
          );
          return;
        }
        if (
          formData.ch4_content === undefined ||
          formData.ch4_content === null ||
          formData.ch4_content === ""
        ) {
          toast.warning("Gas CH4 content (%) is required for blowdown");
          return;
        }
      } else if (processType === "pneumatic") {
        if (
          !formData.amount ||
          !formData.pneu_bleed_rate ||
          !formData.pneu_hours
        ) {
          toast.warning(
            "Pneumatic device count, bleed rate, and operating hours are required",
          );
          return;
        }
        if (
          formData.pneu_ch4_content === undefined ||
          formData.pneu_ch4_content === null ||
          formData.pneu_ch4_content === ""
        ) {
          toast.warning(
            "Gas CH4 content (%) is required for pneumatic devices",
          );
          return;
        }
      } else if (
        ["tank", "tank_flashing", "storage_tanks"].includes(processType)
      ) {
        if (!formData.amount || !formData.tank_gor) {
          toast.warning("Tank throughput and Gas-Oil Ratio (GOR) are required");
          return;
        }
        if (
          formData.tank_ch4_content === undefined ||
          formData.tank_ch4_content === null ||
          formData.tank_ch4_content === ""
        ) {
          toast.warning("Gas CH4 content (%) is required for storage tanks");
          return;
        }
      } else if (processType === "agr") {
        if (
          !formData.agr_throughput ||
          formData.agr_co2_in === undefined ||
          formData.agr_co2_out === undefined ||
          formData.agr_co2_in === "" ||
          formData.agr_co2_out === ""
        ) {
          toast.warning(
            "AGR throughput, inlet CO2 (%), and outlet CO2 (%) are required",
          );
          return;
        }
      } else if (processType === "dehydrator") {
        if (
          !formData.dehy_throughput ||
          !formData.dehy_pump_rate ||
          !formData.dehy_hours
        ) {
          toast.warning(
            "Dehydrator throughput, pump rate, and operating hours are required",
          );
          return;
        }
        if (
          formData.dehy_ch4_content === undefined ||
          formData.dehy_ch4_content === null ||
          formData.dehy_ch4_content === ""
        ) {
          toast.warning("Gas CH4 content (%) is required for dehydrators");
          return;
        }
      }
    }

    try {
      // Construct calc_inputs based on process type
      // This wraps all process-specific parameters as backend expects
      const processInputs = {};

      // Copy all formData into process-specific object
      Object.keys(formData).forEach((key) => {
        const value = formData[key];
        // Parse numeric fields
        if (value !== undefined && value !== null && value !== "") {
          if (
            typeof value === "string" &&
            !isNaN(value) &&
            value.trim() !== ""
          ) {
            processInputs[key] = parseFloat(value);
          } else {
            processInputs[key] = value;
          }
        }
      });

      // Unit Conversion Logic
      let finalAmount = formData.amount ? parseFloat(formData.amount) : 0;
      let finalUnit = formData.unit || "m3";

      // payload debug logging removed — do not log emission data in production

      // Auto-convert if factor has a baseUnit (e.g., Diesel in BBL -> Gal)
      if (
        sourceType === "default" &&
        formData.fuel &&
        API_FACTORS[formData.fuel]
      ) {
        const factor = API_FACTORS[formData.fuel];
        if (factor.baseUnit && factor.baseUnit !== finalUnit) {
          const converted = convertActivityData(
            finalAmount,
            finalUnit,
            factor.baseUnit,
          );
          if (converted !== finalAmount) {
            if (import.meta.env.DEV)
              console.log(
                `Converting ${finalAmount} ${finalUnit} to ${converted} ${factor.baseUnit}`,
              );
            finalAmount = converted;
            finalUnit = factor.baseUnit;
          }
        }
      }

      // --- PROCESS-SPECIFIC UNIT STANDARDIZATION ---

      // 1. Drilling Mud
      // Tier 3 (specific): convert mud_vol to m3 for engineering calculator
      // Tier 1 (default/custom): keep in bbl to match the kg CH4/bbl factor unit
      if (processType === "drilling" && formData.mud_vol) {
        const vol = parseFloat(formData.mud_vol);
        const unit = formData.mud_unit || "bbl";
        if (sourceType === "specific") {
          // Engineering calc needs m3
          processInputs.mud_volume =
            unit !== "m3" ? convertActivityData(vol, unit, "m3") : vol;
          finalAmount = processInputs.mud_volume;
          finalUnit = "m3";
        } else {
          // Tier 1 factor is kg/bbl — keep in bbl
          processInputs.mud_volume =
            unit !== "bbl" ? convertActivityData(vol, unit, "bbl") : vol;
          finalAmount = processInputs.mud_volume;
          finalUnit = "bbl";
        }
      } else if (processType === "drilling" && sourceType !== "specific") {
        // Tier 1 without mud_vol: use amount field in bbl
        const vol = parseFloat(formData.amount || 0);
        const unit = formData.unit || "bbl";
        finalAmount =
          unit !== "bbl" ? convertActivityData(vol, unit, "bbl") : vol;
        finalUnit = "bbl";
      }

      // 2. Storage Tanks (must be bbl)
      if (processType === "storage_tanks" || processType.startsWith("tank")) {
        const amt = parseFloat(formData.amount || 0);
        const unit = formData.tank_unit || formData.unit || "bbl";
        if (unit !== "bbl") {
          finalAmount = convertActivityData(amt, unit, "bbl");
          finalUnit = "bbl";
        } else {
          finalAmount = amt;
          finalUnit = "bbl";
        }
      }

      // 3. Pneumatics
      if (processType === "pneumatic") {
        if (sourceType === "specific") {
          const rate = parseFloat(formData.pneu_bleed_rate || 0);
          const unit = formData.pneu_bleed_unit || "scf";
          if (rate > 0 && unit !== "scf") {
            processInputs.pneu_bleed_rate = convertActivityData(
              rate,
              unit,
              "scf",
            );
          }
        }
        finalAmount = parseFloat(formData.amount || 0);
        finalUnit = formData.unit || "devices";
      }

      // 4. Completions
      if (processType === "completions" && sourceType === "specific") {
        const rateMcfHr = parseFloat(formData.comp_rate || 0);
        const durationHr = parseFloat(formData.comp_duration || 0);
        if (rateMcfHr > 0 && durationHr > 0) {
          finalAmount = rateMcfHr * durationHr * 28.3168; // Mcf to m3
          finalUnit = "m3";
        }
      }

      // 5. Unloading
      if (processType === "unloading" && sourceType === "specific") {
        finalAmount = parseFloat(formData.unload_events || 1);
        finalUnit = "events";
      }

      // 6. Blowdown / Venting
      if (
        (processType === "blowdown" || processType === "venting") &&
        sourceType === "specific"
      ) {
        const vol = parseFloat(formData.blowdown_volume || 0);
        const unit = formData.blowdown_unit || "scf";
        if (unit !== "m3") {
          finalAmount = convertActivityData(vol, unit, "m3");
        } else {
          finalAmount = vol;
        }
        finalUnit = "m3";
      }

      // 7. AGR — always normalize to MMscf for backend
      if (processType === "agr") {
        let throughput = parseFloat(formData.agr_throughput || 0);
        const agrUnit = formData.agr_unit || "MMscf/yr";
        if (agrUnit === "MMscf/day") throughput *= 365;
        else if (agrUnit === "Mcf/day") throughput = (throughput / 1000) * 365;
        else if (agrUnit === "m3/yr") throughput = throughput / 28316.8 / 1000;
        finalAmount = throughput;
        finalUnit = "MMscf";
      }

      // 8. Dehydrator
      if (processType === "dehydrator" && sourceType === "specific") {
        finalAmount = parseFloat(
          formData.dehy_throughput || formData.amount || 0,
        );
        finalUnit = formData.dehy_unit || formData.unit || "MMscf/day";
      }

      // Construct Backend-Compliant Payload
      const finalPayload = {
        // Identity
        facility_id: parseInt(facilityId),
        year: parseInt(year),
        month: parseInt(month),
        activity: activity,
        division: division,
        field: field,
        process_type: processType,
        group_name: groupName || "",
        equipment_id: equipmentId || "",

        // Activity Data (top-level for compatibility)
        quantity: finalAmount,
        amount: finalAmount,
        unit: finalUnit,

        // Factor Selection
        factor_source: sourceType, // 'default', 'custom', 'specific'
        // Always send fuel so backend can look up the factor (needed for HHV & defaults)
        fuel_type: formData.fuel || undefined,
        fuel: formData.fuel || undefined,
        custom_factor_id:
          sourceType === "custom" ? parseInt(formData.fuel) : undefined,

        // HHV & Combustion Parameters — only for specific factor mode (API Compendium 2021 §5)
        // Convert user-entered HHV to BTU/unit matching the fuel quantity unit
        ...(() => {
          if (sourceType !== "specific" || !formData.hhv) return {};
          const rawHHV = parseFloat(formData.hhv);
          const hhvUnit = formData.hhv_unit || "BTU/scf";
          const fuelUnit = (formData.unit || finalUnit || "scf").toLowerCase();

          // All conversions normalise to BTU per the same unit as the fuel quantity:
          // Gas-volume fuels → BTU/scf  (1 scf = 1 ft³ at standard conditions)
          // Liquid fuels     → BTU/gal
          // Mass fuels       → BTU/lb
          let hhvBtu = rawHHV;
          switch (hhvUnit) {
            case "BTU/scf":
            case "BTU/ft3":
              hhvBtu = rawHHV; // already correct for scf/ft3 gas
              break;
            case "MJ/m3":
              // 1 MJ/m3 × (947.817 BTU/MJ) / (35.3147 scf/m3) = 26.839 BTU/scf
              hhvBtu = (rawHHV * 947.817) / 35.3147;
              break;
            case "kcal/m3":
              // 1 kcal/m3 × (3.96567 BTU/kcal) / (35.3147 scf/m3) = 0.11231 BTU/scf
              hhvBtu = (rawHHV * 3.96567) / 35.3147;
              break;
            case "BTU/gal":
              hhvBtu = rawHHV; // already correct for liquid-gal fuels
              break;
            case "BTU/lb":
              hhvBtu = rawHHV; // already correct for mass-based fuels
              break;
            case "MJ/kg":
              // 1 MJ/kg × (947.817 BTU/MJ) / (2.20462 lb/kg) = 430.0 BTU/lb
              hhvBtu = (rawHHV * 947.817) / 2.20462;
              break;
            default:
              hhvBtu = rawHHV;
          }

          return {
            hhv: hhvBtu, // always in BTU/unit after conversion
            hhv_unit: "BTU/unit", // signal to backend that conversion is done
            hhv_original: rawHHV, // preserve original for audit trail
            hhv_original_unit: hhvUnit,
            combustion_efficiency: formData.combustion_efficiency
              ? parseFloat(formData.combustion_efficiency) / 100.0
              : undefined,
            flare_type: formData.flare_type || undefined,
          };
        })(),

        // Specific Factors (for combustion/flaring/venting in specific mode)
        specific_factors: sourceType === "specific" ? specFactors : undefined,
        specificFactors: sourceType === "specific" ? specFactors : undefined,
        user_uncertainty:
          sourceType === "specific" ? userUncertainty : undefined,
        meter_uncertainty_pct:
          sourceType === "specific" ? meterUncertaintyPct : undefined,
        gc_uncertainty_pct:
          sourceType === "specific" ? gcUncertaintyPct : undefined,

        // Process-Specific Inputs (NESTED as backend expects)
        calc_inputs: {
          [processType]: processInputs,
        },
        status: status,
      };

      // payload logging removed — do not log emission data in production

      await api.post("/emissions", finalPayload);
      toast.success(
        status === "Draft"
          ? "Entry saved as draft"
          : "Scope 1 entry added successfully",
      );

      // Reset Form (keep identity)
      setFormData({});
      setGroupName("");
      setEquipmentId("");
      setUncertainty({ co2: null, ch4: null, n2o: null });
      setSpecFactors({
        co2: "",
        co2Unit: "kg/m3",
        ch4: "",
        ch4Unit: "kg/m3",
        n2o: "",
        n2oUnit: "kg/m3",
        co: "",
        coUnit: "kg/m3",
      });
      setUserUncertainty({ co2: "", ch4: "", n2o: "" });
      setMeterUncertaintyPct("2.0");
      setGcUncertaintyPct("");

      loadEntries();
    } catch (error) {
      console.error("Failed to add entry:", error);
      const msg = error.response?.data?.error || "Failed to add entry";
      toast.error(msg);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this entry?")) return;
    try {
      // Strip prefix (e.g. "s1_17" -> "17")
      const realId = id.toString().replace(/^[s]\d+_/, "");
      await api.delete(`/emissions/${realId}`);
      toast.success("Entry deleted");
      loadEntries();
    } catch (error) {
      console.error("Failed to delete:", error);
      toast.error("Failed to delete entry");
    }
  };

  // --- RENDER HELPERS ---

  const renderSpecificForm = () => {
    const props = {
      data: { ...formData, process_type: processType },
      onChange: handleFormChange,
      // Pass down hoisted props for forms that might need them (though we are moving logic up)
      sourceType,
      setSourceType,
    };

    // Fallback to generic form for Tier 1 / Custom on upstream processes
    if (
      sourceType !== "specific" &&
      [
        "drilling",
        "completions",
        "unloading",
        "blowdown",
        "agr",
        "dehydrator",
      ].includes(processType)
    ) {
      return <CombustionForm {...props} />;
    }

    switch (processType) {
      case "combustion":
      case "mobile":
      case "flaring":
      case "loading":
      case "separation":
        return <CombustionForm {...props} />;
      case "venting":
        return sourceType === "specific" ? (
          <BlowdownForm {...props} />
        ) : (
          <CombustionForm {...props} />
        );
      case "drilling":
        return <DrillingForm {...props} />;
      case "completions":
        return <CompletionsForm {...props} />;
      case "unloading":
        return <UnloadingForm {...props} />;
      case "blowdown":
        return <BlowdownForm {...props} />;
      case "agr":
        return <AGRForm {...props} />;
      case "dehydrator":
        return <DehydratorForm {...props} />;
      case "pneumatic":
        return <PneumaticsForm {...props} />;
      case "tank":
      case "tank_flashing":
      case "tank_working":
      case "tank_breathing":
        return <TankForm {...props} />;
      case "fugitive":
        return <FugitivesForm {...props} />;
      default:
        return <div>Select a process type</div>;
    }
  };

  const getFacilityOptions = () => [
    { value: "", label: "Select Region..." },
    ...facilities.map((f) => ({
      value: f.id.toString(),
      label: f.name,
      subLabel: f.field,
    })),
  ];

  const getProcessOptions = () => {
    const options = [];
    PROCESS_GROUPS.forEach((group) => {
      options.push({
        label: group.label,
        value: `header-${group.label}`,
        isHeader: true,
      });
      group.options.forEach((optKey) => {
        if (PROCESS_TYPES[optKey]) {
          // Unique value per group to avoid cross-highlighting
          // value: "Upstream|combustion"
          options.push({
            value: `${group.id}|${optKey}`,
            label: PROCESS_TYPES[optKey],
          });
        }
      });
    });
    return options;
  };

  const handleProcessChange = (val) => {
    if (!val) return;
    // val format: "StreamID|processKey"
    const [stream, process] = val.split("|");
    if (stream && process) {
      setStreamType(stream);
      setProcessType(process);
      if (
        [
          "drilling",
          "completions",
          "unloading",
          "blowdown",
          "agr",
          "dehydrator",
        ].includes(process)
      ) {
        setSourceType("specific");
      }
    }
  };

  // Compute current dropdown value from state
  const currentProcessValue = `${streamType}|${processType}`;

  const handleGasApply = (res) => {
    setSpecFactors((prev) => ({
      ...prev,
      co2: res.co2,
      co2Unit: res.unit,
      ch4: res.ch4, // Usually 0 or low for pure analysis
      ch4Unit: res.unit,
    }));

    // Auto-map composition to engineering forms if raw_composition is provided
    if (
      res.raw_composition &&
      ["drilling", "completions", "unloading"].includes(processType)
    ) {
      if (res.raw_composition.CH4)
        handleFormChange("ch4_content", res.raw_composition.CH4);
      if (res.raw_composition.CO2)
        handleFormChange("co2_content", res.raw_composition.CO2);
    }

    setShowGasCalc(false);
    toast.show("success", "Factors updated from Gas Analysis");
  };

  return (
    <div className="scope-form">
      <div
        className="calc-panel"
        style={{
          background: "white",
          borderRadius: "8px",
          padding: "25px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.05)",
        }}
      >
        <h2
          style={{
            fontSize: "1.2rem",
            fontWeight: "bold",
            marginBottom: "25px",
            color: "#333",
          }}
        >
          New Activity Entry
        </h2>

        {/* 1. IDENTITY & LOCATION */}
        <div style={{ marginBottom: "30px" }}>
          <h4 className="section-title">1. IDENTITY &amp; LOCATION</h4>
          <div className="form-grid-4">
            <div className="input-group">
              <label>Activity</label>
              <input
                type="text"
                className="mole-input readonly"
                value={activity || "Auto-filled"}
                disabled
              />
            </div>
            <div className="input-group">
              <label>Division</label>
              <input
                type="text"
                className="mole-input readonly"
                value={division || "Auto-filled"}
                disabled
              />
            </div>
            <div className="input-group">
              <label>Region</label>
              <CustomDropdown
                options={getFacilityOptions()}
                value={facilityId || ""}
                onChange={setFacilityId}
                placeholder="Select Region..."
              />
            </div>
            <div className="input-group">
              <label>Field</label>
              <input
                type="text"
                className="mole-input readonly"
                value={field || "Auto-filled"}
                disabled
              />
            </div>
          </div>
          <div className="form-grid-3">
            <div className="input-group">
              <label>Year</label>
              <input
                type="number"
                className="mole-input"
                value={year || ""}
                onChange={(e) => setYear(e.target.value)}
              />
            </div>
            <div className="input-group">
              <label>Month</label>
              <select
                className="component-select"
                value={month || 1}
                onChange={(e) => setMonth(e.target.value)}
              >
                {[...Array(12)].map((_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {String(i + 1).padStart(2, "0")}
                  </option>
                ))}
              </select>
            </div>
            <div className="input-group">
              <label>Group Name</label>
              <input
                type="text"
                className="mole-input"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="e.g. West Facility"
              />
            </div>
          </div>
          <div className="form-grid-3">
            <div className="input-group">
              <label>
                Emission Source
                <span
                  style={{
                    marginLeft: "6px",
                    fontSize: "0.7rem",
                    color: "#6b7280",
                    fontWeight: 400,
                  }}
                >
                  (from inventory)
                </span>
              </label>
              <CustomDropdown
                options={getEmissionSourceOptions()}
                value={emissionSourceId}
                onChange={setEmissionSourceId}
                placeholder="Select Emission Source..."
              />
            </div>
            <div className="input-group">
              <label>Equipment ID/Name</label>
              <input
                type="text"
                className="mole-input"
                value={equipmentId}
                onChange={(e) => setEquipmentId(e.target.value)}
                placeholder="e.g. Turbine T-101"
              />
            </div>
          </div>
        </div>

        {/* 2. PROCESS & SOURCE DETAILS */}
        <div style={{ marginBottom: "30px" }}>
          <h4 className="section-title">2. PROCESS & SOURCE DETAILS</h4>
          <div className="form-grid-2">
            <div className="input-group">
              <label>Process Type</label>
              <CustomDropdown
                options={getProcessOptions()}
                value={currentProcessValue}
                onChange={handleProcessChange}
              />
            </div>

            {/* Hoisted Emission Factor Selection — hidden for stoichiometry */}
            {processType !== "stoichiometry" && (
              <div className="input-group">
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <label style={{ margin: 0 }}>Emission Factor</label>
                  <div
                    className="toggle-container"
                    style={{
                      background: "#f3f4f6",
                      padding: "2px",
                      borderRadius: "4px",
                      display: "flex",
                      gap: "2px",
                    }}
                  >
                    {["default", "custom", "specific"]
                      .filter((type) => {
                        if (processType === "mobile" && type === "specific")
                          return false;
                        if (processType === "fugitive" && type === "specific")
                          return false;
                        if (processType === "loading" && type === "specific")
                          return false;
                        if (processType === "separation" && type === "specific")
                          return false;
                        return true;
                      })
                      .map((type) => (
                        <button
                          key={type}
                          className={`btn-toggle-sm ${sourceType === type ? "active" : ""}`}
                          onClick={() => {
                            setSourceType(type);
                            if (
                              type === "default" &&
                              [
                                "drilling",
                                "completions",
                                "unloading",
                                "blowdown",
                                "agr",
                                "dehydrator",
                              ].includes(processType)
                            ) {
                              toast.warning(
                                "Tier 1 calculations are not recommended for this process (OGMP 2.0).",
                                { duration: 8000 },
                              );
                            }
                          }}
                          style={{
                            padding: "2px 8px",
                            borderRadius: "4px",
                            border: "none",
                            background:
                              sourceType === type ? "#fff" : "transparent",
                            color:
                              sourceType === type
                                ? "var(--accent-color)"
                                : "#6b7280",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            cursor: "pointer",
                            boxShadow:
                              sourceType === type
                                ? "0 1px 2px rgba(0,0,0,0.1)"
                                : "none",
                            textTransform: "capitalize",
                          }}
                        >
                          {type}
                        </button>
                      ))}
                  </div>
                </div>
                {sourceType === "default" && (
                  <CustomDropdown
                    options={fuelOptions}
                    value={formData.fuel || ""}
                    onChange={(val) => handleFormChange("fuel", val)}
                    placeholder="Select Emission Factor..."
                    renderOption={renderFactorOption}
                  />
                )}
                {sourceType === "custom" && (
                  <CustomDropdown
                    options={fuelOptions}
                    value={formData.fuel || ""}
                    onChange={(val) => handleFormChange("fuel", val)}
                    placeholder="Select Custom Factor..."
                  />
                )}
                {sourceType === "specific" &&
                  ![
                    "tank",
                    "tank_flashing",
                    "tank_working",
                    "tank_breathing",
                    "agr",
                    "dehydrator",
                    "pneumatic",
                    "mobile",
                    "fugitive",
                    "venting",
                    "drilling",
                    "completions",
                    "unloading",
                    "blowdown",
                  ].includes(processType) && (
                    <>
                      <CustomDropdown
                        options={fuelOptions}
                        value={formData.fuel || ""}
                        onChange={(val) => handleFormChange("fuel", val)}
                        placeholder="Select Base Factor (Optional)..."
                        renderOption={renderFactorOption}
                      />
                      <div style={{ marginTop: "10px", marginBottom: "10px" }}>
                        <button
                          className="gas-calc-btn btn-secondary"
                          onClick={() => setShowGasCalc(true)}
                          style={{
                            display: processType === "agr" ? "none" : "flex",
                          }}
                        >
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <rect
                              x="4"
                              y="2"
                              width="16"
                              height="20"
                              rx="2"
                              ry="2"
                            ></rect>
                            <line x1="8" y1="6" x2="16" y2="6"></line>
                            <line x1="16" y1="14" x2="16" y2="18"></line>
                            <path d="M16 10h.01"></path>
                            <path d="M12 10h.01"></path>
                            <path d="M8 10h.01"></path>
                            <path d="M12 14h.01"></path>
                            <path d="M8 14h.01"></path>
                            <path d="M12 18h.01"></path>
                            <path d="M8 18h.01"></path>
                          </svg>
                          Calculate from Analysis
                        </button>
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: "10px",
                          marginTop: "10px",
                        }}
                      >
                        {["co2", "ch4", "n2o"]
                          .filter((gas) =>
                            processType === "agr" ? gas !== "n2o" : true,
                          )
                          .map((gas) => (
                            <div
                              key={gas}
                              className="input-group"
                              style={{ marginBottom: 0 }}
                            >
                              <label style={{ fontSize: "0.75rem" }}>
                                {gas.toUpperCase()} Factor
                              </label>
                              <div style={{ display: "flex", gap: "5px" }}>
                                <input
                                  type="number"
                                  className="mole-input"
                                  placeholder="Value"
                                  value={specFactors[gas] || ""}
                                  onChange={(e) =>
                                    setSpecFactors((p) => ({
                                      ...p,
                                      [gas]: e.target.value,
                                    }))
                                  }
                                  style={{ flex: 1 }}
                                />
                                <select
                                  className="component-select"
                                  value={specFactors[`${gas}Unit`] || ""}
                                  onChange={(e) =>
                                    setSpecFactors((p) => ({
                                      ...p,
                                      [`${gas}Unit`]: e.target.value,
                                    }))
                                  }
                                  style={{ width: "80px", padding: "4px" }}
                                >
                                  <option value="kg/m3">kg/m³</option>
                                  <option value="kg/scf">kg/scf</option>
                                  <option value="kg/gal">kg/gal</option>
                                  <option value="lb/scf">lb/scf</option>
                                  <option value="tonne/m3">t/m³</option>
                                  <option value="kg/MMBtu">kg/MMBtu</option>
                                </select>
                              </div>
                            </div>
                          ))}
                      </div>
                    </>
                  )}
              </div>
            )}
          </div>
        </div>

        {/* 3. ACTIVITY DATA */}
        <div style={{ marginBottom: "30px" }}>
          <h4 className="section-title">3. ACTIVITY DATA</h4>
          {renderSpecificForm()}
        </div>

        {/* 4. COMPLIANCE & UNCERTAINTY */}
        <div style={{ marginBottom: "30px" }}>
          <h4 className="section-title">4. COMPLIANCE & UNCERTAINTY</h4>
          <div className="form-grid-3">
            {sourceType === "specific" && (
              <div
                className="input-group"
                style={{ gridColumn: "span 3", marginBottom: "8px" }}
              >
                <label>Measurement Instrumentation Precision</label>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <div
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      background: "#f3f4f6",
                      borderRadius: "6px",
                      border: "1px solid #e5e7eb",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: "#374151",
                      }}
                    >
                      Meter Calibration Tolerance
                    </span>
                    <div style={{ display: "flex", alignItems: "center" }}>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <input
                        type="number"
                        className="mole-input"
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="2.0"
                        value={meterUncertaintyPct}
                        onChange={(e) => setMeterUncertaintyPct(e.target.value)}
                        step="0.1"
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  </div>
                  <div
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      background: "#f3f4f6",
                      borderRadius: "6px",
                      border: "1px solid #e5e7eb",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: "#374151",
                      }}
                    >
                      GC Analytical Precision
                    </span>
                    <div style={{ display: "flex", alignItems: "center" }}>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <input
                        type="number"
                        className="mole-input"
                        style={{
                          width: "55px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="Opt."
                        value={gcUncertaintyPct}
                        onChange={(e) => setGcUncertaintyPct(e.target.value)}
                        step="0.1"
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  </div>
                  <div style={{ flex: 1 }}></div>
                </div>
              </div>
            )}
            <div className="input-group" style={{ gridColumn: "span 3" }}>
              <label>
                Emission Factor / Direct Measurement Uncertainty Override (±%)
              </label>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <div
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    background: "#f3f4f6",
                    borderRadius: "6px",
                    border: "1px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#374151",
                    }}
                  >
                    CO₂
                  </span>
                  {sourceType === "specific" ? (
                    <div style={{ display: "flex", alignItems: "center" }}>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <input
                        type="number"
                        className="mole-input"
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="—"
                        value={userUncertainty.co2}
                        onChange={(e) =>
                          setUserUncertainty({
                            ...userUncertainty,
                            co2: e.target.value,
                          })
                        }
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.co2 != null ? "#10b981" : "#9ca3af",
                      }}
                    >
                      {uncertainty.co2 != null
                        ? `±${(uncertainty.co2 * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    background: "#f3f4f6",
                    borderRadius: "6px",
                    border: "1px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#374151",
                    }}
                  >
                    CH₄
                  </span>
                  {sourceType === "specific" ? (
                    <div style={{ display: "flex", alignItems: "center" }}>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <input
                        type="number"
                        className="mole-input"
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="—"
                        value={userUncertainty.ch4}
                        onChange={(e) =>
                          setUserUncertainty({
                            ...userUncertainty,
                            ch4: e.target.value,
                          })
                        }
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.ch4 != null ? "#3b82f6" : "#9ca3af",
                      }}
                    >
                      {uncertainty.ch4 != null
                        ? `±${(uncertainty.ch4 * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    background: "#f3f4f6",
                    borderRadius: "6px",
                    border: "1px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#374151",
                    }}
                  >
                    N₂O
                  </span>
                  {sourceType === "specific" ? (
                    <div style={{ display: "flex", alignItems: "center" }}>
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <input
                        type="number"
                        className="mole-input"
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="—"
                        value={userUncertainty.n2o}
                        onChange={(e) =>
                          setUserUncertainty({
                            ...userUncertainty,
                            n2o: e.target.value,
                          })
                        }
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.n2o != null ? "#8b5cf6" : "#9ca3af",
                      }}
                    >
                      {uncertainty.n2o != null
                        ? `±${(uncertainty.n2o * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
              </div>
              <span
                style={{
                  fontSize: "0.7rem",
                  color: "var(--text-secondary)",
                  marginTop: "6px",
                }}
              >
                {sourceType === "default"
                  ? "Automatically populated from EPA/IPCC catalogs"
                  : "Enter specific uncertainties if known, otherwise leave blank to omit (—)"}
              </span>
            </div>
          </div>
        </div>

        <div
          className="formula-inspector-card"
          style={{
            background: "rgba(255, 247, 237, 0.7)",
            border: "1px solid rgba(255, 102, 0, 0.25)",
            borderRadius: "14px",
            padding: "16px 20px",
            marginBottom: "24px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--accent-color, #ff6600)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                📐 Live Equation Inspector (Tier 2/3 GHG Protocol)
              </span>
            </div>
            <span style={{ fontSize: "0.78rem", color: "#64748b", fontWeight: 600 }}>
              GWP Standard: IPCC AR6 (CO₂:1, CH₄:28, N₂O:265)
            </span>
          </div>

          <div
            style={{
              fontFamily: "monospace",
              fontSize: "0.88rem",
              background: "#ffffff",
              padding: "10px 14px",
              borderRadius: "8px",
              border: "1px solid #fed7aa",
              color: "#0f172a",
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "6px",
            }}
          >
            <span style={{ color: "#ea580c", fontWeight: 700 }}>
              {formData.amount || formData.quantity ? `${formData.amount || formData.quantity} ${formData.unit || "units"}` : "[Activity Data]"}
            </span>
            <span style={{ color: "#94a3b8" }}>×</span>
            <span style={{ color: "#2563eb", fontWeight: 600 }}>
              {formData.fuel ? `${formData.fuel} Factor` : "[Emission Factor]"}
            </span>
            <span style={{ color: "#94a3b8" }}>×</span>
            <span style={{ color: "#16a34a", fontWeight: 600 }}>
              {formData.hhv ? `${formData.hhv} HHV` : "1.0 HHV"}
            </span>
            <span style={{ color: "#94a3b8" }}>×</span>
            <span style={{ color: "#9333ea", fontWeight: 600 }}>GWP</span>
            <span style={{ color: "#94a3b8" }}>=</span>
            <span style={{ color: "#0f172a", fontWeight: 800, background: "#fef08a", padding: "2px 6px", borderRadius: "4px" }}>
              CO₂e Total (tCO₂e)
            </span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            className="btn-add-draft"
            onClick={() => handleAddEntry("Pending")}
            style={{
              flex: 1,
              background: "rgba(255, 255, 255, 0.9)",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
              fontWeight: 600,
              padding: "10px 16px",
              borderRadius: "10px",
              cursor: "pointer",
            }}
          >
            Save as Draft (Maker Mode)
          </button>
          <button
            className="btn-add-activity"
            onClick={() => handleAddEntry("Verified")}
            style={{ flex: 1.5 }}
          >
            + Calculate & Submit for Review
          </button>
        </div>
      </div>

      {importModal.isOpen && (
        <Scope1ImportWizard
          onClose={() => setImportModal({ ...importModal, isOpen: false })}
          onUploadSuccess={() => {
            loadEntries();
            toast.success("Records imported and calculated successfully!");
          }}
        />
      )}

      <div className="calculator-grid-container" style={{ marginTop: "30px" }}>
        {/* Filter bar */}
        <div
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            alignItems: "center",
            marginBottom: "14px",
          }}
        >
          <strong style={{ fontSize: "0.95rem", marginRight: "4px" }}>
            Recent Activity (Scope 1)
          </strong>
          <div style={{ flex: 1 }} />
          <input
            type="text"
            placeholder="Search..."
            value={filterSearch}
            onChange={(e) => {
              setFilterSearch(e.target.value);
              setCurrentPage(1);
            }}
            className="mole-input"
            style={{ width: "160px", padding: "6px 10px", fontSize: "0.82rem" }}
          />
          <select
            value={filterYear}
            onChange={(e) => {
              setFilterYear(e.target.value);
              setCurrentPage(1);
            }}
            className="component-select"
            style={{ width: "100px", fontSize: "0.82rem" }}
          >
            <option value="">All Years</option>
            {[...new Set(entries.map((e) => e.year))]
              .sort((a, b) => b - a)
              .map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
          </select>
          <select
            value={filterProcess}
            onChange={(e) => {
              setFilterProcess(e.target.value);
              setCurrentPage(1);
            }}
            className="component-select"
            style={{ width: "140px", fontSize: "0.82rem" }}
          >
            <option value="">All Processes</option>
            {[
              ...new Set(
                entries.map((e) => e.process || e.process_type).filter(Boolean),
              ),
            ].map((p) => (
              <option key={p} value={p}>
                {PROCESS_TYPES[p]?.label || p}
              </option>
            ))}
          </select>
          {(filterYear || filterProcess || filterSearch) && (
            <button
              className="btn-ghost"
              onClick={() => {
                setFilterYear("");
                setFilterProcess("");
                setFilterSearch("");
                setCurrentPage(1);
              }}
              style={{
                fontSize: "0.8rem",
                padding: "5px 10px",
                color: "var(--text-secondary)",
              }}
            >
              Clear
            </button>
          )}
          <button
            className="action-btn"
            onClick={() =>
              exportToCSV(
                entries.filter((e) => {
                  const s = filterSearch.toLowerCase();
                  const matchSearch =
                    !s ||
                    (e.activity || "").toLowerCase().includes(s) ||
                    (e.equipment_id || "").toLowerCase().includes(s) ||
                    (e.fuel || e.fuel_type || "").toLowerCase().includes(s) ||
                    (e.group || "").toLowerCase().includes(s);
                  return (
                    matchSearch &&
                    (!filterYear || e.year?.toString() === filterYear) &&
                    (!filterProcess ||
                      (e.process || e.process_type) === filterProcess)
                  );
                }),
                "scope1_export.csv",
              )
            }
            style={{
              background: "#10b981",
              padding: "6px 14px",
              fontSize: "0.82rem",
              whiteSpace: "nowrap",
            }}
          >
            ↓ Export CSV
          </button>
          <button
            className="action-btn"
            onClick={() => setImportModal({ isOpen: true, type: "activity" })}
            style={{
              background: "#10b981",
              padding: "6px 14px",
              fontSize: "0.82rem",
              whiteSpace: "nowrap",
            }}
          >
            ↑ Bulk Import (Wizard)
          </button>
        </div>
        <div className="table-scroll-container">
          <table className="excel-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Activity</th>
                <th>Region</th>
                <th>Division</th>
                <th>Field</th>
                <th>Emission Source</th>
                <th>Equipment ID</th>
                <th>Process</th>
                <th>Activity/Fuel</th>
                <th>Factor Type</th>
                <th>Quantity</th>
                <th>CO₂ (t)</th>
                <th>CH₄ (t)</th>
                <th>N₂O (t)</th>
                <th>Total (tCO₂e)</th>
                <th
                  style={{ textAlign: "center" }}
                  title="Standard Combined Uncertainty (1σ)"
                >
                  CO₂ 1σ (±%)
                </th>
                <th
                  style={{ textAlign: "center" }}
                  title="Standard Combined Uncertainty (1σ)"
                >
                  CH₄ 1σ (±%)
                </th>
                <th
                  style={{ textAlign: "center" }}
                  title="Standard Combined Uncertainty (1σ)"
                >
                  N₂O 1σ (±%)
                </th>
                <th
                  style={{ textAlign: "center" }}
                  title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                >
                  CO₂ 95%CI (±%)
                </th>
                <th
                  style={{ textAlign: "center" }}
                  title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                >
                  CH₄ 95%CI (±%)
                </th>
                <th
                  style={{ textAlign: "center" }}
                  title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                >
                  N₂O 95%CI (±%)
                </th>
                <th style={{ textAlign: "center" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const filteredEntries = entries.filter((entry) => {
                  const s = filterSearch.toLowerCase();
                  const matchSearch =
                    !s ||
                    (entry.activity || "").toLowerCase().includes(s) ||
                    (entry.equipment_id || "").toLowerCase().includes(s) ||
                    (entry.fuel || entry.fuel_type || "")
                      .toLowerCase()
                      .includes(s) ||
                    (entry.group || "").toLowerCase().includes(s) ||
                    (entry.division || "").toLowerCase().includes(s);
                  const matchYear =
                    !filterYear || entry.year?.toString() === filterYear;
                  const matchProcess =
                    !filterProcess ||
                    (entry.process || entry.process_type) === filterProcess;
                  return matchSearch && matchYear && matchProcess;
                });
                if (filteredEntries.length === 0)
                  return (
                    <tr>
                      <td
                        colSpan="19"
                        style={{
                          textAlign: "center",
                          color: "var(--text-secondary)",
                          padding: "30px",
                        }}
                      >
                        {entries.length === 0
                          ? "No entries yet"
                          : "No results match your filters"}
                      </td>
                    </tr>
                  );
                return filteredEntries.map((entry) => {
                  let factorType = "-";
                  if (entry.factor_source === "default") {
                    factorType = "Default";
                  } else if (
                    entry.factor_source === "custom" ||
                    entry.factor_source === "specific"
                  ) {
                    factorType = "Specific";
                  }
                  return (
                    <tr key={entry.id}>
                      <td>{entry.year}</td>
                      <td>{entry.activity || "-"}</td>
                      <td>{entry.facility_name || entry.region || "-"}</td>
                      <td>{entry.division || "-"}</td>
                      <td>{entry.field || "-"}</td>
                      <td>{entry.group_name || entry.group || "-"}</td>
                      <td>{entry.equipment_id || "-"}</td>
                      <td>
                        {PROCESS_TYPES[entry.process || entry.process_type]
                          ?.label ||
                          entry.process ||
                          entry.process_type}
                      </td>
                      <td>
                        {entry.fuel ||
                          entry.fuel_type ||
                          entry.activity_data_label ||
                          "-"}
                      </td>
                      <td
                        style={{
                          fontWeight: 500,
                          color:
                            factorType === "Default" ? "#10b981" : "#3b82f6",
                        }}
                      >
                        {factorType}
                      </td>
                      <td>
                        {entry.amount || entry.quantity
                          ? `${formatNumber(entry.amount || entry.quantity, 2)} ${entry.unit}`
                          : "-"}
                      </td>
                      <td>{formatNumber(entry.co2_emissions || 0, 3)}</td>
                      <td>{formatNumber(entry.ch4_emissions || 0, 5)}</td>
                      <td>{formatNumber(entry.n2o_emissions || 0, 5)}</td>
                      <td
                        style={{
                          color: "var(--accent-color)",
                          fontWeight: 600,
                        }}
                      >
                        {formatNumber(entry.co2e_total, 3)}
                        {entry.status === "Draft" && (
                          <span
                            style={{
                              marginLeft: "8px",
                              fontSize: "0.65rem",
                              background: "#fee2e2",
                              color: "#b91c1c",
                              padding: "1px 5px",
                              borderRadius: "4px",
                            }}
                          >
                            Draft
                          </span>
                        )}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            entry.uncertainty_co2 != null
                              ? "#10b981"
                              : "var(--text-muted)",
                        }}
                        title="Standard Combined Uncertainty (1σ)"
                      >
                        {entry.uncertainty_co2 != null
                          ? `±${(entry.uncertainty_co2 * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            entry.uncertainty_ch4 != null
                              ? "#3b82f6"
                              : "var(--text-muted)",
                        }}
                        title="Standard Combined Uncertainty (1σ)"
                      >
                        {entry.uncertainty_ch4 != null
                          ? `±${(entry.uncertainty_ch4 * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            entry.uncertainty_n2o != null
                              ? "#8b5cf6"
                              : "var(--text-muted)",
                        }}
                        title="Standard Combined Uncertainty (1σ)"
                      >
                        {entry.uncertainty_n2o != null
                          ? `±${(entry.uncertainty_n2o * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            entry.uncertainty_co2 != null
                              ? "#10b981"
                              : "var(--text-muted)",
                        }}
                        title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                      >
                        {entry.uncertainty_co2 != null
                          ? `±${(entry.uncertainty_co2 * 200).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            entry.uncertainty_ch4 != null
                              ? "#3b82f6"
                              : "var(--text-muted)",
                        }}
                        title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                      >
                        {entry.uncertainty_ch4 != null
                          ? `±${(entry.uncertainty_ch4 * 200).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            entry.uncertainty_n2o != null
                              ? "#8b5cf6"
                              : "var(--text-muted)",
                        }}
                        title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                      >
                        {entry.uncertainty_n2o != null
                          ? `±${(entry.uncertainty_n2o * 200).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button
                          className="icon-button"
                          onClick={() => handleDelete(entry.id)}
                          style={{ color: "#ef4444" }}
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                });
              })()}
            </tbody>
            <tfoot>
              <tr style={{ backgroundColor: "#f9fafb", fontWeight: "bold" }}>
                <td
                  colSpan="18"
                  style={{ textAlign: "right", paddingRight: "15px" }}
                >
                  Total (
                  {filterYear || filterProcess || filterSearch
                    ? "Filtered"
                    : "Page"}
                  ):
                </td>
                <td style={{ color: "var(--accent-color)" }}>
                  {formatNumber(
                    entries
                      .filter((entry) => {
                        const s = filterSearch.toLowerCase();
                        const matchSearch =
                          !s ||
                          (entry.activity || "").toLowerCase().includes(s) ||
                          (entry.equipment_id || "")
                            .toLowerCase()
                            .includes(s) ||
                          (entry.fuel || entry.fuel_type || "")
                            .toLowerCase()
                            .includes(s) ||
                          (entry.group || "").toLowerCase().includes(s);
                        return (
                          matchSearch &&
                          (!filterYear ||
                            entry.year?.toString() === filterYear) &&
                          (!filterProcess ||
                            (entry.process || entry.process_type) ===
                              filterProcess)
                        );
                      })
                      .reduce((sum, e) => sum + (e.co2e_total || 0), 0),
                    3,
                  )}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        {/* Simplified Pagination */}
        <div className="pagination-controls">
          <button
            className="action-btn secondary"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <span style={{ color: "var(--text-secondary)" }}>
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="action-btn secondary"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      </div>

      <GasCompositionCalculator
        isOpen={showGasCalc}
        onClose={() => setShowGasCalc(false)}
        onApply={handleGasApply}
        processType={processType}
      />
    </div>
  );
};

export default Scope1Form;
