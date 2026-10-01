import React, { useState, useEffect } from "react";
import api from "../api";
import CustomDropdown from "./CustomDropdown";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { formatNumber, formatEmission } from "../utils/formatters";
import "./ScopeTables.css";
import "./Scope1Form.css";

// Sub-components
import Scope1ImportWizard from "./Scope1ImportWizard";
import ConfirmModal from "./ConfirmModal";
import { Upload, Trash2, Eye, Sliders, Sparkles, BookOpen, Layers, PlusCircle, CheckCircle, Info } from "lucide-react";
import { OFFICIAL_FUEL_PRESETS, getPresetsForFuel } from "../constants/officialFuelPresets";
import QuickAddCustomFactorModal from "./QuickAddCustomFactorModal";
import CalculationDetails from "./CalculationDetails";
import { Section, FieldGrid, MoreOptions } from "./scope1/ui";
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
import ChemicalProductionForm from "./scope1/ChemicalProductionForm";
import NitricAcidForm from "./scope1/NitricAcidForm";
import AdipicAcidForm from "./scope1/AdipicAcidForm";
import AsphaltBlowingForm from "./scope1/AsphaltBlowingForm";
import AssociatedGasVentingForm from "./scope1/AssociatedGasVentingForm";
import { SectionMethodPanel } from "./scope1/SectionMethods";
import {
  SECTION_PROCESSES,
  SECTION_TIERS,
  currentChoice,
  sectionMethodActive,
  syncSectionChoice,
} from "./scope1/methodChoices";
import GasCompositionCalculator from "./GasCompositionCalculator";
import {
  API_FACTORS,
  PROCESS_GROUPS,
  PROCESS_TYPES as PROCESS_TYPES_MAP,
} from "../utils/EmissionFactors";
import {
  formatUncertainty,
  getSegmentColor,
  getSegmentBgColor,
  convertActivityData,
} from "../utils/emissionFactorsAPI";

const PROCESS_TYPES = PROCESS_TYPES_MAP;

// Emission UI shows no API Compendium / table citations (user request); legal references stay
const hideApiCitation = (t) => (t && /\bAPI\b|Compendium|\bTables?\s*\d/.test(t) ? null : t);

// Tier shown in the table and CSV: a saved library / custom factor is "Custom", a Tier 2 site
// property override is "Tier 2" (browser test #13: both were shown as "Specific")
function factorTypeLabel(entry) {
  if (entry.factor_source === "default") return "Default";
  if (entry.factor_source === "custom") return entry.custom_factor_id ? "Custom" : "Tier 2";
  if (entry.factor_source === "specific") return "Specific";
  return "-";
}

const Scope1Form = () => {
  const { user } = useAuth();
  const toast = useToast();
  // BUG-082: the inspector label reflects the org's active GWP standard
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

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

  // Tier 2 Enhanced State
  const tier2Mode = "override"; // Tier 2 (API Compendium) = measured fuel properties; library factors are separate
  const [activePresetId, setActivePresetId] = useState("");
  const [fuelDensity, setFuelDensity] = useState("");
  const [dataSourceRef, setDataSourceRef] = useState("");
  const [isQuickAddModalOpen, setIsQuickAddModalOpen] = useState(false);

  const [facilities, setFacilities] = useState([]);
  const [emissionSources, setEmissionSources] = useState([]);
  const [emissionSourceId, setEmissionSourceId] = useState("");
  const [entries, setEntries] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [showGasCalc, setShowGasCalc] = useState(false);
  const [inspectRecord, setInspectRecord] = useState(null);
  const [importModal, setImportModal] = useState({
    isOpen: false,
    type: "activity",
  });
  const RECORDS_PER_PAGE = 10;

  // Table filter state
  const [filterYear, setFilterYear] = useState("");
  const [facetYears, setFacetYears] = useState([]);
  useEffect(() => {
    api.get("/filters/available")
      .then((r) => setFacetYears(Array.isArray(r.data?.years) ? r.data.years : []))
      .catch(() => setFacetYears([]));
  }, []);
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

    const isCombustion = [
      "combustion",
      "stationary_combustion",
      "mobile_combustion",
      "mobile",
      "flaring",
      "routine_flaring",
      "non_routine_flaring",
      "safety_flaring",
      "flare",
    ].includes(processType);

    if (
      sourceType === "default" ||
      (sourceType === "tier2_plus" && processType === "drilling") ||
      sourceType === "specific" ||
      (sourceType === "custom" && isCombustion && tier2Mode === "override")
    ) {
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

          // Standard usage check for other processes; the flaring variants use the flaring factors
          const usageKey = ["routine_flaring", "non_routine_flaring", "safety_flaring", "flare"].includes(processType)
            ? "flaring"
            : processType;
          const usageMatch = factor.usage && factor.usage.includes(usageKey);
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
          (f) =>
            !f.usage ||
            f.usage === "Custom" ||
            f.usage === "All" ||
            f.usage.includes(processType) ||
            f.usage.toLowerCase().includes(processType.toLowerCase()) ||
            (processType === "drilling" &&
              (String(f.usage || "").toLowerCase().includes("drill") ||
                String(f.usage || "").toLowerCase().includes("mud") ||
                String(f.factor_name || f.name || "").toLowerCase().includes("drill") ||
                String(f.factor_name || f.name || "").toLowerCase().includes("mud"))),
        )
        .map((f) => ({
          value: f.id.toString(),
          label: f.factor_name || f.name || `Custom Factor #${f.id}`,
          factor: f,
        }));
      setFuelOptions(options);
    }
  }, [
    processType,
    sourceType,
    tier2Mode,
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

  const BLANK_SPEC = {
    co2: "", co2Unit: "kg/m3", ch4: "", ch4Unit: "kg/m3", n2o: "", n2oUnit: "kg/m3", co: "", coUnit: "kg/m3",
  };
  // Form inputs belong to one process and tier: switching either starts from a clean form, so no
  // value typed for another process / method is submitted with this record (Tier 3 test #17, #20)
  const resetProcessInputs = () => {
    setFormData({});
    setSpecFactors(BLANK_SPEC);
  };
  // Tier 3 "fuel analysis" factor fields (base factor, gas analysis, CO2/CH4/N2O factors)
  const showsTier3Factors =
    sourceType === "specific" &&
    !sectionMethodActive(formData) &&
    !SECTION_PROCESSES[processType] &&
    ![
      "tank", "tank_flashing", "tank_working", "tank_breathing", "agr", "dehydrator", "pneumatic", "mobile",
      "fugitive", "venting", "drilling", "completions", "unloading", "blowdown", "associated_gas_venting",
    ].includes(processType);

  // Handle Resetting Fuel on Context Change
  useEffect(() => {
    setFormData((prev) => ({ ...prev, fuel: "" }));
  }, [processType]);

  useEffect(() => {
    setFormData((prev) => {
      const isCustomId = !isNaN(parseInt(prev.fuel)) && String(parseInt(prev.fuel)) === String(prev.fuel);
      if (sourceType === "library" && !isCustomId) return { ...prev, fuel: "" };
      if (sourceType !== "library" && isCustomId && prev.fuel) return { ...prev, fuel: "" };
      return prev;
    });
  }, [sourceType, tier2Mode]);

  const handleApplyPreset = (preset) => {
    setActivePresetId(preset.id);
    const matched = fuelOptions.find(
      (opt) => opt.value.toLowerCase() === preset.defaultMatchingFuel.toLowerCase()
    );
    const fuelVal = matched ? matched.value : preset.defaultMatchingFuel;

    setFormData((prev) => ({
      ...prev,
      fuel: fuelVal,
      hhv: preset.hhv ? preset.hhv.toString() : prev.hhv,
      hhv_unit: preset.hhvUnit || prev.hhv_unit || "BTU/scf",
    }));

    if (preset.densityKgM3) {
      setFuelDensity(preset.densityKgM3.toString());
    }
    if (preset.citation) {
      setDataSourceRef(hideApiCitation(preset.citation) || "");
    }
    toast.success(`Preset applied: ${preset.shortLabel || preset.name}`);
  };

  const handleFactorCreated = (newFactor) => {
    loadCustomFactors();
    if (newFactor?.id) {
      setSourceType("library");
      setFormData((prev) => ({ ...prev, fuel: newFactor.id.toString() }));
    }
  };

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
      if (sourceType === "custom") {
        const found = customFactors.find(
          (f) => f.id.toString() === formData.fuel?.toString()
        );
        if (found) {
          factorToUse = {
            ...found,
            ch4: found.ch4_factor,
            co2: found.co2_factor,
            n2o: found.n2o_factor,
            uncertainty: {
              ch4: found.ch4_uncertainty || found.uncertainty || 0.2,
              co2: found.co2_uncertainty || 0.1,
              n2o: found.n2o_uncertainty || 0.3,
            },
          };
        }
      }
      if (!factorToUse) {
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
    }
    // 2. Drilling (Mud Degassing) - Table 6-3 well default or API onshore mud defaults
    else if (processType === "drilling") {
      if (sourceType === "default") {
        factorToUse =
          API_FACTORS["Drilling - Gas Well Drilling (Simplified Default)"];
      } else if (sourceType === "tier2_plus") {
        const mudType = formData.mud_type || "water_based";
        const mudKey =
          mudType === "oil" || mudType === "oil_based"
            ? "Drilling - Mud Degassing (Oil Based)"
            : "Drilling - Mud Degassing (Water Based)";
        if (API_FACTORS[mudKey]) {
          factorToUse = API_FACTORS[mudKey];
        }
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
      const opDefaults = getUserOperationalDefaults(user, data);
      if (opDefaults.defaultFacilityId) {
        setFacilityId((prev) => prev || opDefaults.defaultFacilityId);
      }
    } catch (error) {
      console.error("Failed to load facilities:", error);
      toast.error("Failed to load regions");
    }
  };

  useEffect(() => {
    if (!facilityId && facilities.length > 0) {
      const opDefaults = getUserOperationalDefaults(user, facilities);
      if (opDefaults.defaultFacilityId) {
        setFacilityId(opDefaults.defaultFacilityId);
      }
    }
  }, [user, facilities]);

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
      factorTypeLabel(e),
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
        setTotalPages(Math.max(1, Math.ceil(parseInt(totalCount) / RECORDS_PER_PAGE)));
      } else {
        setTotalPages(Math.max(1, Math.ceil(allEntries.length / RECORDS_PER_PAGE)));
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

  // Keep the calculation-method keys (activity_key / vent_method / combustion_method) in step
  // with the process and tier, including after the form is reset
  const sectionChoice = currentChoice(formData);
  useEffect(() => {
    // processes whose tiers are these methods: move off a tier the process does not offer
    const tiers = SECTION_TIERS[processType];
    if (tiers && sourceType !== "library" && !tiers.some((t) => t.key === sourceType)) {
      setSourceType(tiers[0].key);
      return;
    }
    syncSectionChoice(processType, sourceType, formData, handleFormChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processType, sourceType, sectionChoice]);

  const handleAddEntry = async (status = "Verified") => {
    // Validate identity fields
    if (!year || !month || !facilityId || !processType) {
      toast.warning(
        "Please fill in all identity fields (Year, Month, Region, Process)",
      );
      return;
    }

    // API Compendium activity tables, gas-volume and combustion methods: the server validates
    // their inputs (SectionMethods); only the activity-table choice is checked here
    const sectionActive =
      sourceType !== "library" && (sectionMethodActive(formData) || Boolean(SECTION_PROCESSES[processType]));
    if (sectionActive && currentChoice(formData) === "activity" && !formData.activity_key) {
      toast.warning("Select a source");
      return;
    }

    // Library factor: activity x the selected site factor
    if (sourceType === "library") {
      if (!formData.fuel || isNaN(parseInt(formData.fuel))) {
        toast.warning("Select a library factor");
        return;
      }
    }

    // Validate fuel/factor selection
    if (sourceType !== "library" && !sectionActive &&
      (sourceType === "default" || sourceType === "custom") &&
      // fugitives: Tier 1 / 2B use Compendium tables (7-8, 7-12); Tier 2A sets its catalog key itself
      !["associated_gas_venting", "completions", "unloading", "fugitive"].includes(processType) &&
      !formData.fuel
    ) {
      toast.warning("Please select a fuel or emission factor");
      return;
    }
    if (
      processType === "associated_gas_venting" &&
      sourceType === "default"
    ) {
      if (!formData.fuel && !formData.basin) {
        formData.fuel = "Associated Gas Venting - US Average";
        formData.basin = "Associated Gas Venting - US Average";
      }
    }

    // Validate activity data (amount/quantity)
    const amount = formData.amount || formData.quantity;
    const isUpstreamEng =
      sourceType === "specific" &&
      [
        "completions",
        "unloading",
        "agr",
        "dehydrator",
        "venting",
        "blowdown",
        "associated_gas_venting",
        "fugitive",
      ].includes(processType);

    const needsAmount = !sectionActive || currentChoice(formData) === "activity";
    if (!isUpstreamEng && needsAmount && (!amount || parseFloat(amount) <= 0)) {
      toast.warning(
        "Please enter a valid activity amount/quantity greater than 0",
      );
      return;
    }

    // Strict validation for Tier 3 (Engineering / Specific) inputs
    if (sourceType === "specific" && !sectionActive) {
      if (
        ["combustion", "stationary_combustion", "flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"].includes(processType)
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
        const tier = String(formData.tier || (sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1")).toLowerCase();
        if (tier === "tier1" || sourceType === "default") {
          const wells = parseFloat(formData.well_count || formData.wells || formData.amount || 0);
          if (wells <= 0) {
            toast.warning("Number of wells must be greater than zero for Tier 1 liquids unloading");
            return;
          }
        } else if (tier === "tier2" || sourceType === "custom") {
          const events = parseFloat(formData.events || formData.unload_events || formData.unload_freq || formData.amount || 0);
          if (events < 0 || isNaN(events)) {
            toast.warning("Number of unloading events is required for Tier 2 liquids unloading");
            return;
          }
        } else {
          // Tier 3 Engineering
          const method = String(formData.calc_method || formData.method || "api_equation_6_10").toLowerCase();
          if (method === "api_equation_6_11") {
            if (!formData.p_shut || !formData.p_line || !formData.p_sep || !formData.sfr_p || !formData.t_p) {
              toast.warning("All automated plunger parameters (Pshut, Pline, Psep, SFRp, Tp) are required");
              return;
            }
          } else if (method === "api_equation_6_10") {
            const hasDepth = formData.unload_depth || formData.well_depth;
            const hasDiam = formData.unload_diam || formData.diameter;
            const hasPress = formData.unload_press || formData.pressure;
            const hasEvents = formData.unload_events || formData.unload_freq || formData.events || formData.amount;
            const hasSfr = formData.sfr !== undefined && formData.sfr !== null && formData.sfr !== "";
            const hasHours = formData.hours_open !== undefined && formData.hours_open !== null && formData.hours_open !== "";
            if (!hasDepth || !hasDiam || !hasPress || !hasEvents || !hasSfr || !hasHours) {
              toast.warning("Depth, diameter, pressure, events, SFR and venting hours are required");
              return;
            }
          } else {
            const hasDepth = formData.unload_depth || formData.well_depth;
            const hasDiam = formData.unload_diam || formData.diameter;
            const hasPress = formData.unload_press || formData.pressure;
            const hasEvents = formData.unload_freq || formData.unload_events || formData.events || formData.amount;
            if (!hasDepth || !hasDiam || !hasPress || !hasEvents) {
              toast.warning("Well unloading parameters (depth, diameter, pressure, events) are required");
              return;
            }
          }
          if (
            formData.ch4_content === undefined ||
            formData.ch4_content === null ||
            formData.ch4_content === ""
          ) {
            toast.warning("Gas CH4 content (%) is required for well unloading");
            return;
          }
        }
      } else if (processType === "completions") {
        const tier = String(formData.tier || (sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1")).toLowerCase();
        if (tier === "tier1" || sourceType === "default") {
          const events = parseFloat(formData.amount || formData.events || 0);
          if (events <= 0 || isNaN(events)) {
            toast.warning("Number of completion events must be greater than zero for Tier 1 completions");
            return;
          }
        } else if (tier === "tier2" || sourceType === "custom") {
          const method = String(formData.calc_method || formData.comp_method || "rate_duration").toLowerCase();
          if (method === "gor") {
            if (!formData.comp_liquid_bbl || !formData.comp_gor) {
              toast.warning("Liquid flowback volume (bbl) and GOR (scf/bbl) are required for GOR method");
              return;
            }
          } else if (method === "api_equation_6_7" || method === "pressure_volume") {
            const hasRate = formData.comp_rate || formData.daily_production_rate || formData.comp_daily_prod_rate;
            const hasDur = formData.comp_duration || formData.vent_duration_hours;
            if (!hasRate || !hasDur) {
              toast.warning("Initial production rate and vent duration are required");
              return;
            }
          } else {
            // rate_duration
            if (!formData.comp_rate || !formData.comp_duration) {
              toast.warning("Flowback rate and duration are required for Rate × Duration calculation");
              return;
            }
          }
          if (formData.comp_ch4_content === undefined && formData.ch4_content === undefined) {
            toast.warning("Gas CH4 content (%) is required for Tier 2 completions");
            return;
          }
        } else {
          // Tier 3 Direct Measurement
          const hasVol = formData.comp_volume || formData.flowback_volume || (formData.unit !== "events" && formData.amount);
          if (!hasVol || parseFloat(hasVol) <= 0) {
            toast.warning("Measured flowback gas volume must be greater than zero for Tier 3 completions");
            return;
          }
          if (formData.comp_ch4_content === undefined && formData.ch4_content === undefined) {
            toast.warning("Gas CH4 content (%) is required for Tier 3 completions");
            return;
          }
          const disp = String(formData.comp_disposition || formData.disposition || "vented").toLowerCase();
          if (disp === "split") {
            const fV = parseFloat(formData.comp_frac_vented || formData.frac_vented || 0);
            const fF = parseFloat(formData.comp_frac_flared || formData.frac_flared || 0);
            const fR = parseFloat(formData.comp_frac_recovered || formData.frac_recovered || 0);
            const sumP = Math.round((fV > 1 ? fV : fV * 100) + (fF > 1 ? fF : fF * 100) + (fR > 1 ? fR : fR * 100));
            if (sumP !== 100) {
              toast.warning(`Custom split percentages must sum to 100% (currently ${sumP}%)`);
              return;
            }
          }
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

    // Associated Gas Venting Validations (All Tiers)
    if (processType === "associated_gas_venting") {
      const tier = String(
        formData.tier ||
          (sourceType === "specific"
            ? "tier3"
            : sourceType === "custom"
            ? "tier2"
            : "tier1"),
      ).toLowerCase();

      if (tier === "tier1" || sourceType === "default") {
        const oil = parseFloat(formData.oil_production || formData.amount || 0);
        if (oil <= 0 || isNaN(oil)) {
          toast.warning(
            "Crude oil production throughput must be greater than zero for Tier 1",
          );
          return;
        }
      } else if (tier === "tier2" || sourceType === "custom") {
        const oil = parseFloat(formData.oil_production || formData.amount || 0);
        if (oil <= 0 || isNaN(oil)) {
          toast.warning(
            "Crude oil production throughput must be greater than zero for Tier 2",
          );
          return;
        }
        const gor = parseFloat(formData.gor);
        if (
          formData.gor === undefined ||
          formData.gor === "" ||
          isNaN(gor) ||
          gor < 0
        ) {
          toast.warning("Gas-Oil Ratio (GOR) is required and cannot be negative");
          return;
        }
        const dur = parseFloat(
          formData.venting_duration !== undefined
            ? formData.venting_duration
            : new Date(Number(year), Number(month), 0).getDate() || 365,
        );
        if (dur < 0) {
          toast.warning("Venting duration cannot be negative");
          return;
        }
        if (dur > 366) {
          toast.warning("Venting duration cannot exceed 366 days");
          return;
        }
      } else {
        // Tier 3
        const rate = parseFloat(formData.vent_rate || 0);
        const vol = parseFloat(formData.vent_volume || formData.amount || 0);
        if (rate <= 0 && vol <= 0) {
          toast.warning(
            "Measured vent flow rate or total measured vent volume is required for Tier 3",
          );
          return;
        }
        if (
          rate > 0 &&
          (!formData.venting_duration ||
            parseFloat(formData.venting_duration) <= 0)
        ) {
          toast.warning(
            "Venting duration is required when vent rate is specified for Tier 3",
          );
          return;
        }
      }

      // Composition check if provided
      const ch4 =
        formData.ch4_content !== undefined && formData.ch4_content !== ""
          ? parseFloat(formData.ch4_content)
          : null;
      const co2 =
        formData.co2_content !== undefined && formData.co2_content !== ""
          ? parseFloat(formData.co2_content)
          : null;
      if (ch4 !== null && (ch4 < 0 || ch4 > 100)) {
        toast.warning("Methane (CH4) content must be between 0% and 100%");
        return;
      }
      if (co2 !== null && (co2 < 0 || co2 > 100)) {
        toast.warning(
          "Carbon dioxide (CO2) content must be between 0% and 100%",
        );
        return;
      }
      if (ch4 !== null && co2 !== null && ch4 + co2 > 100.01) {
        toast.warning("Sum of CH4 and CO2 content cannot exceed 100%");
        return;
      }
    }

    try {
      setSubmitting(true);
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
      // BUG-109: no hidden "m3" default and no client-side base-unit rewrite. The entered amount
      // and unit are sent once (top level and calc_inputs agree) and the server converts them.
      let finalUnit = formData.unit || "";

      // --- PROCESS-SPECIFIC UNIT STANDARDIZATION ---

      if (!sectionActive) {
      // 1. Drilling Mud Degassing (Tier 1: Table 6-3 wells or mud defaults; Tier 2: Custom factor from DB; Tier 2+: Table 6-1/6-2 days)
      if (processType === "drilling") {
        const val = parseFloat(formData.amount || formData.quantity || 0);
        if (sourceType === "default" || sourceType === "tier1") {
          const selFuel = String(formData.fuel || "");
          const isWell =
            selFuel.includes("Well") ||
            selFuel === "DrillWellDefault" ||
            !selFuel ||
            formData.unit === "well";
          processInputs.tier = "tier1";
          if (isWell) {
            processInputs.wells = val;
            finalAmount = val;
            finalUnit = "well";
          } else {
            processInputs.drilling_days = val;
            processInputs.mud_type = selFuel.includes("Oil")
              ? "oil_based"
              : "water_based";
            finalAmount = val;
            finalUnit = "days";
          }
        } else if (sourceType === "custom") {
          // Tier 2: Custom Factor populated from database
          processInputs.tier = "tier2";
          processInputs.drilling_days = val;
          processInputs.custom_factor_id = parseInt(formData.fuel);
          finalAmount = val;
          finalUnit = "days";
        } else {
          // Tier 2+: Site Gas Composition
          processInputs.tier = "tier2_plus";
          processInputs.drilling_days = val;
          processInputs.mud_type =
            formData.mud_type ||
            (formData.fuel?.includes("Oil") ? "oil_based" : "water_based");
          if (
            formData.ch4_fraction !== undefined &&
            formData.ch4_fraction !== ""
          ) {
            processInputs.ch4_fraction = parseFloat(formData.ch4_fraction);
          } else {
            processInputs.ch4_fraction = 0.8385;
          }
          if (
            formData.co2_fraction !== undefined &&
            formData.co2_fraction !== ""
          ) {
            processInputs.co2_fraction = parseFloat(formData.co2_fraction);
          }
          finalAmount = val;
          finalUnit = "days";
        }
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
      if (processType === "completions") {
        const tier = String(formData.tier || (sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1")).toLowerCase();
        if (tier === "tier1" || sourceType === "default" || tier === "tier2" || sourceType === "custom") {
          finalAmount = parseFloat(formData.events || formData.amount);
          finalUnit = "events";
        } else {
          // Tier 3 Direct Measurement: metered volume
          const vol = parseFloat(formData.comp_volume || formData.flowback_volume || (formData.unit !== "events" ? formData.amount : 0) || 0);
          finalAmount = vol;
          finalUnit = formData.volume_unit || (formData.unit !== "events" ? formData.unit : "Mcf") || "Mcf";
        }
      }

      // 5. Unloading
      if (processType === "unloading") {
        const tier = String(formData.tier || (sourceType === "specific" ? "tier3" : sourceType === "custom" ? "tier2" : "tier1")).toLowerCase();
        if (tier === "tier1" || sourceType === "default") {
          finalAmount = parseFloat(formData.well_count || formData.wells || formData.amount);
          finalUnit = "wells";
        } else {
          finalAmount = parseFloat(formData.unload_events || formData.unload_freq || formData.events || formData.amount);
          finalUnit = "events";
        }
      }

      // 6. Blowdown / Venting
      if (
        (processType === "blowdown" || processType === "venting") &&
        sourceType === "specific"
      ) {
        // the unit select shows m3 by default: that is the unit of the entered volume
        finalAmount = parseFloat(formData.blowdown_volume || 0);
        finalUnit = formData.blowdown_unit || "m3";
        processInputs.blowdown_unit = finalUnit;
      }

      // 7. AGR — send the entered throughput with its unit; the server converts it (BUG-066: the
      //    old client conversion divided m³/yr by an extra 1000)
      if (processType === "agr") {
        const agrUnit = formData.agr_unit || "MMscf/yr";
        finalAmount = parseFloat(formData.agr_throughput || 0);
        finalUnit = agrUnit;
        processInputs.agr_unit = agrUnit;
      }

      // 8. Dehydrator — the throughput field is labelled MMscf/yr and the server calculator reads
      //    MMscf/yr (BUG-091: it used to be stored as MMscf/day)
      if (processType === "dehydrator" && sourceType === "specific") {
        finalAmount = parseFloat(
          formData.dehy_throughput || formData.amount || 0,
        );
        finalUnit = "MMscf/yr";
      }

      // 9. Associated Gas Venting
      if (processType === "associated_gas_venting") {
        const tier = String(
          formData.tier ||
            (sourceType === "specific"
              ? "tier3"
              : sourceType === "custom"
              ? "tier2"
              : "tier1"),
        ).toLowerCase();
        processInputs.tier = tier;

        if (tier === "tier3" || sourceType === "specific") {
          const rateMode = (formData.tier3_mode || (formData.vent_volume ? "volume" : "rate")) === "rate";
          if (rateMode) {
            // record the vented volume (rate x hours), not the rate (Tier 3 browser re-run)
            const per = { scfh: [1, "scf"], "scf/day": [1 / 24, "scf"], scfm: [60, "scf"], "m3/hr": [1, "m3"], "m3/day": [1 / 24, "m3"] }[
              formData.vent_rate_unit || "scfh"
            ] || [1, "scf"];
            finalAmount = parseFloat(formData.vent_rate || 0) * per[0] * parseFloat(formData.venting_duration || 0);
            finalUnit = per[1];
          } else {
            finalAmount = parseFloat(formData.vent_volume || formData.amount || 0);
            finalUnit = formData.vent_volume_unit || formData.unit || "scf";
          }
        } else {
          finalAmount = parseFloat(
            formData.oil_production !== undefined
              ? formData.oil_production
              : formData.amount || 0,
          );
          finalUnit = formData.oil_unit || formData.unit || "bbl";
        }

        if (sourceType !== "specific") {
          processInputs.oil_production = parseFloat(
            formData.oil_production !== undefined
              ? formData.oil_production
              : formData.amount || 0,
          );
          processInputs.oil_unit = formData.oil_unit || finalUnit || "bbl";
        }

        if (formData.basin || formData.fuel) {
          processInputs.basin = formData.basin || formData.fuel;
        }
        if (formData.gor !== undefined && formData.gor !== "") {
          processInputs.gor = parseFloat(formData.gor);
          processInputs.gor_unit = formData.gor_unit || "scf/bbl";
        }
        if (
          formData.venting_duration !== undefined &&
          formData.venting_duration !== ""
        ) {
          processInputs.venting_duration = parseFloat(formData.venting_duration);
          // Tier 3 "Venting time (h)" is in hours; Tier 2 has its own unit select (default days)
          processInputs.duration_unit =
            sourceType === "specific" ? "hours" : formData.duration_unit || "days";
        }
        if (
          formData.period_duration !== undefined &&
          formData.period_duration !== ""
        ) {
          processInputs.period_duration = parseFloat(formData.period_duration);
        }
        if (
          formData.recovered_gas_volume !== undefined &&
          formData.recovered_gas_volume !== ""
        ) {
          processInputs.recovered_gas_volume = parseFloat(
            formData.recovered_gas_volume,
          );
        }
        if (
          formData.flared_gas_volume !== undefined &&
          formData.flared_gas_volume !== ""
        ) {
          processInputs.flared_gas_volume = parseFloat(
            formData.flared_gas_volume,
          );
        }
        if (formData.gas_volume_unit) {
          processInputs.gas_volume_unit = formData.gas_volume_unit;
        }
        if (formData.vent_rate !== undefined && formData.vent_rate !== "") {
          processInputs.vent_rate = parseFloat(formData.vent_rate);
          processInputs.vent_rate_unit = formData.vent_rate_unit || "scfh";
        }
        if (formData.vent_volume !== undefined && formData.vent_volume !== "") {
          processInputs.vent_volume = parseFloat(formData.vent_volume);
          processInputs.vent_volume_unit = formData.vent_volume_unit || "scf";
        }
        if (formData.ch4_content !== undefined && formData.ch4_content !== "") {
          processInputs.ch4_content = parseFloat(formData.ch4_content);
        }
        if (formData.co2_content !== undefined && formData.co2_content !== "") {
          processInputs.co2_content = parseFloat(formData.co2_content);
        }
      }

      // 10. Fugitives & Equipment Leaks (API Chapter 7 Onshore)
      if (processType === "fugitive") {
        const tier = String(
          formData.fugitive_tier ||
            (sourceType === "specific"
              ? "tier3"
              : sourceType === "custom"
              ? "tier2"
              : "tier1")
        ).toLowerCase();
        processInputs.fugitive_tier = tier;
        processInputs.fugitive_method = formData.fugitive_method || "component";
        processInputs.facility_type = formData.facility_type;
        processInputs.equipment_type = formData.equipment_type;
        processInputs.component_type = formData.component_type;
        processInputs.service_type = formData.service_type || "gas";
        processInputs.operating_hours = formData.operating_hours !== undefined ? parseFloat(formData.operating_hours) : undefined;
        processInputs.operating_days = formData.operating_days !== undefined ? parseFloat(formData.operating_days) : undefined;
        processInputs.time_unit = formData.time_unit || "hours";
        processInputs.duration_unit = formData.duration_unit || formData.time_unit || "hours";
        processInputs.screening_ppm = formData.screening_ppm !== undefined ? parseFloat(formData.screening_ppm) : undefined;
        processInputs.fugitive_ppm = formData.fugitive_ppm !== undefined ? parseFloat(formData.fugitive_ppm) : processInputs.screening_ppm;
        processInputs.leakers_count = formData.leakers_count !== undefined ? parseFloat(formData.leakers_count) : undefined;
        processInputs.non_leakers_count = formData.non_leakers_count !== undefined ? parseFloat(formData.non_leakers_count) : undefined;
        processInputs.measured_rate = formData.measured_rate !== undefined ? parseFloat(formData.measured_rate) : undefined;
        // Tier 3 measurement: the unit must be chosen (kg/h vs scf/h changes the meaning of the rate)
        processInputs.rate_unit = formData.rate_unit || (tier === "tier3" ? undefined : "kg/hr");
        processInputs.ch4_mole_pct = formData.ch4_mole_pct !== undefined ? parseFloat(formData.ch4_mole_pct) : undefined;
        processInputs.co2_mole_pct = formData.co2_mole_pct !== undefined ? parseFloat(formData.co2_mole_pct) : undefined;
        processInputs.gas_stream = formData.gas_stream;
        processInputs.correlation_type = formData.correlation_type;

        // Set top-level finalAmount and finalUnit for backward compatibility & display
        const num = (k) => parseFloat(formData[k] || 0) || 0;
        if (tier === "tier3") {
          const m = formData.fugitive_method;
          if (m === "method21") {
            finalAmount = num("m21_below_count") + num("m21_above_count");
            finalUnit = "components";
          } else if (m === "correlation") {
            finalAmount = num("corr_zero_count") + num("corr_screened_count") + num("corr_pegged_10k_count") + num("corr_pegged_100k_count");
            finalUnit = "components";
          } else if (m === "measurement") {
            finalAmount = num("measured_rate");
            finalUnit = formData.rate_unit || "";
          } else {
            finalAmount = num("leakers_count");
            finalUnit = "leakers";
          }
        } else if (formData.amount !== undefined && formData.amount !== "") {
          finalAmount = parseFloat(formData.amount);
          finalUnit = formData.unit || "count";
        } else if (tier === "tier1") {
          finalAmount = parseFloat(formData.facility_count);
          finalUnit = "facility";
        } else if (formData.fugitive_method === "equipment") {
          finalAmount = parseFloat(formData.equipment_count);
          finalUnit = "equipment";
        } else if (formData.fugitive_method === "ogi") {
          finalAmount = parseFloat(formData.leakers_count);
          finalUnit = "leakers";
        } else if (formData.fugitive_method === "measurement") {
          finalAmount = parseFloat(formData.measured_rate || 0);
          finalUnit = formData.rate_unit || "kg/hr";
        } else {
          finalAmount = parseFloat(formData.component_count);
          finalUnit = "sources";
        }
      }

      } // !sectionActive

      if (sectionActive) {
        // amount/unit only for activity tables; engineered methods carry their own inputs
        finalAmount = formData.amount ? parseFloat(formData.amount) : undefined;
        finalUnit = formData.amount ? formData.unit || "count" : undefined;
      }

      if (sourceType === "library") {
        finalAmount = parseFloat(formData.amount || formData.quantity || 0);
        finalUnit = formData.unit || "";
      }

      // a blank count is never booked as 1 (wells, events, facilities, components ... were defaulted to 1)
      if (finalAmount !== undefined && Number.isNaN(finalAmount)) {
        toast.warning("Please enter the activity amount (count, volume or quantity)");
        setSubmitting(false);
        return;
      }

      if (!finalUnit && sourceType !== "specific" && !sectionActive) {
        toast.warning("Please select a unit");
        setSubmitting(false);
        return;
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
        factor_source: sourceType === "library" ? "custom" : sourceType, // 'default', 'custom', 'specific'
        factor_mode: sourceType === "library" ? "library" : undefined,
        // Always send fuel so backend can look up the factor (needed for HHV & defaults)
        fuel_type: formData.fuel || undefined,
        fuel: formData.fuel || undefined,
        custom_factor_id:
          sourceType === "library" ? parseInt(formData.fuel) : undefined,

        // Tier 2 & Tier 3 Fuel Properties (HHV & Density) & Audit References
        density: fuelDensity ? parseFloat(fuelDensity) : undefined,
        fuel_density: fuelDensity ? parseFloat(fuelDensity) : undefined,
        data_source_ref: dataSourceRef || undefined,

        // HHV & Combustion Parameters — for Tier 2 custom fuel properties or Tier 3 specific factor mode
        // Convert user-entered HHV to BTU/unit matching the fuel quantity unit
        ...(() => {
          const isTier2Override = sourceType === "custom" && tier2Mode === "override";
          if ((sourceType !== "specific" && !isTier2Override) || !formData.hhv) return {};
          const rawHHV = parseFloat(formData.hhv);
          const hhvUnit = formData.hhv_unit || "BTU/scf";

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
        specific_factors:
          showsTier3Factors && (specFactors.co2 || specFactors.ch4 || specFactors.n2o || specFactors.co)
            ? specFactors
            : undefined,
        specificFactors:
          showsTier3Factors && (specFactors.co2 || specFactors.ch4 || specFactors.n2o || specFactors.co)
            ? specFactors
            : undefined,
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
      setFuelDensity("");
      setDataSourceRef("");
      setActivePresetId("");
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
    } finally {
      setSubmitting(false);
    }
  };

  const handleInspect = (entry) => {
    const pType = entry.process || entry.process_type || "Scope 1";
    const fuelVal = entry.fuel || entry.fuel_type || "N/A";
    const qty = entry.amount || entry.quantity || 0;
    const unitVal = entry.unit || "unit";

    let payload = {};
    if (entry.source_payload) {
      try {
        payload =
          typeof entry.source_payload === "string"
            ? JSON.parse(entry.source_payload)
            : entry.source_payload;
      } catch {
        // an unreadable stored payload is shown without its inputs
      }
    }

    const co2Val = Number(entry.co2_emissions || 0);
    const ch4Val = Number(entry.ch4_emissions || 0);
    const n2oVal = Number(entry.n2o_emissions || 0);
    const co2eVal = Number(entry.co2e_total || 0);

    const numQty = Number(qty) || 0;
    const efCo2 =
      entry.ef_used_co2 ??
      payload.ef_used_co2 ??
      payload.factor_co2 ??
      (numQty > 0 ? (co2Val * 1000) / numQty : null);
    const efCh4 =
      entry.ef_used_ch4 ??
      payload.ef_used_ch4 ??
      payload.factor_ch4 ??
      (numQty > 0 ? (ch4Val * 1000) / numQty : null);
    const efN2o =
      entry.ef_used_n2o ??
      payload.ef_used_n2o ??
      payload.factor_n2o ??
      (numQty > 0 ? (n2oVal * 1000) / numQty : null);

    const fSource =
      entry.factor_source ||
      entry.factor_type ||
      payload.factor_source ||
      "default";
    const facName =
      entry.facility_name ||
      facilities.find((f) => f.id === entry.facility_id)?.name ||
      `Facility #${entry.facility_id || "N/A"}`;
    // PROCESS_TYPES values are labels (strings) or { label } objects
    const pDef = PROCESS_TYPES[entry.process || entry.process_type];
    const pLabel = (typeof pDef === "string" ? pDef : pDef?.label) || pType;

    setInspectRecord({
      process_type: `Scope 1 - ${pLabel}`,
      fuel: fuelVal,
      amount: qty,
      unit: unitVal,
      facility: facName,
      year: entry.year,
      month: entry.month,
      equipment_id: entry.equipment_id || "-",
      status: entry.status || "Verified",
      factor_source: fSource,
      method:
        entry.calc_method ||
        entry.calculation_method ||
        (fSource.toLowerCase().includes("specific")
          ? "Tier 3 (site-specific)"
          : "Tier 1-2 (emission factor)"),
      emissions: {
        totalCo2e: co2eVal,
        co2: co2Val,
        ch4: ch4Val,
        n2o: n2oVal,
      },
      factors: {
        co2: efCo2,
        ch4: efCh4,
        n2o: efN2o,
        source: fSource,
      },
      uncertainty: {
        co2: entry.uncertainty_co2,
        ch4: entry.uncertainty_ch4,
        n2o: entry.uncertainty_n2o,
      },
    });
  };

  const handleDelete = (id) => {
    setDeleteConfirmId(id);
  };

  const confirmDelete = async () => {
    if (!deleteConfirmId) return;
    try {
      // Strip prefix (e.g. "s1_17" -> "17")
      const realId = deleteConfirmId.toString().replace(/^[s]\d+_/, "");
      await api.delete(`/emissions/${realId}`);
      toast.success("Entry deleted");
      loadEntries();
    } catch (error) {
      console.error("Failed to delete:", error);
      toast.error("Failed to delete entry");
    } finally {
      setDeleteConfirmId(null);
    }
  };

  // --- RENDER HELPERS ---

  const renderSpecificForm = () => {
    const props = {
      data: { ...formData, process_type: processType },
      onChange: handleFormChange,
      // days in the record's month: the default operating period of a monthly record
      periodDays: new Date(Number(year), Number(month), 0).getDate() || 365,
      // Pass down hoisted props for forms that might need them (though we are moving logic up)
      sourceType,
      setSourceType,
    };

    // Library factor: activity x factor, same inputs for every process
    if (sourceType === "library") {
      return <CombustionForm {...props} sourceType="library" />;
    }

    // Fallback to generic form for Tier 1 / Custom on upstream processes
    if (
      sourceType !== "specific" &&
      [
        "blowdown",
      ].includes(processType)
    ) {
      return <CombustionForm {...props} />;
    }

    return (
      <SectionMethodPanel
        processType={processType}
        sourceType={sourceType}
        data={props.data}
        onChange={handleFormChange}
        legacy={renderProcessForm(props)}
      />
    );
  };

  const renderProcessForm = (props) => {
    switch (processType) {
      case "combustion":
      case "mobile":
      case "flaring":
      case "routine_flaring":
      case "non_routine_flaring":
      case "safety_flaring":
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
      case "chemical_production":
        return <ChemicalProductionForm {...props} />;
      case "nitric_acid_production":
        return <NitricAcidForm {...props} />;
      case "adipic_acid_production":
        return <AdipicAcidForm {...props} />;
      case "asphalt_blowing":
        return <AsphaltBlowingForm {...props} />;
      case "associated_gas_venting":
        return <AssociatedGasVentingForm {...props} />;
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
      if (process !== processType) resetProcessInputs();
      setStreamType(stream);
      setProcessType(process);
      if (process === "drilling") {
        setSourceType("default");
        handleFormChange("unit", "well");
      } else if (
        [
          "completions",
          "unloading",
          "blowdown",
          "agr",
          "dehydrator",
          "tank",
          "tank_flashing",
          "tank_working",
          "tank_breathing",
        ].includes(process)
      ) {
        setSourceType("specific");
      } else if (
        [
          "associated_gas_venting",
          "mobile",
          "fugitive",
          "loading",
          "separation",
          "chemical_production",
          "nitric_acid_production",
          "adipic_acid_production",
          "asphalt_blowing",
        ].includes(process)
      ) {
        setSourceType("default");
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
    // The whole analysis is sent in mol % with an explicit basis: c1 used to go as a fraction while
    // CO2 went as a percent (one analysis, two bases), and C2+ and N2 were dropped
    if (res.raw_composition) {
      const rc = res.raw_composition;
      const pct = (...keys) => keys.reduce((t, k) => t + (parseFloat(rc[k]) || 0), 0);
      const set = (field, v) => handleFormChange(field, v > 0 ? v : undefined);
      handleFormChange("composition_basis", "percent");
      set("c1", pct("CH4"));
      set("c2", pct("C2H6"));
      set("c3", pct("C3H8"));
      set("c4", pct("iC4H10", "nC4H10"));
      set("c5", pct("iC5H12", "nC5H12"));
      set("c6", pct("C6H14"));
      set("n2", pct("N2"));
      set("ch4_content", pct("CH4"));
      set("co2_content", pct("CO2"));
    }

    setShowGasCalc(false);
    toast.show("success", "Factors updated from Gas Analysis");
  };

  return (
    <div className="scope-form">
      <div className="calc-panel s1-form">
        <h2 className="s1-form-title">New entry</h2>

        <Section n={1} title="Identity & Location">
          <FieldGrid min={180}>
            <div className="input-group s1-span-2">
              <label>Region</label>
              <CustomDropdown
                options={getFacilityOptions()}
                value={facilityId || ""}
                onChange={setFacilityId}
                placeholder="Select region"
              />
            </div>
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
                    {new Date(2000, i, 1).toLocaleString(undefined, { month: "short" })}
                  </option>
                ))}
              </select>
            </div>
          </FieldGrid>
          {(activity || division || field) && (
            <div className="s1-meta">{[activity, division, field].filter(Boolean).join(" · ")}</div>
          )}
          <div className="s1-subgroup">
            <div className="s1-subhead">Source details</div>
            <FieldGrid>
              <div className="input-group">
                <label>Emission source</label>
                <CustomDropdown
                  options={getEmissionSourceOptions()}
                  value={emissionSourceId}
                  onChange={setEmissionSourceId}
                  placeholder="From inventory"
                />
              </div>
              <div className="input-group">
                <label>Equipment ID</label>
                <input
                  type="text"
                  className="mole-input"
                  value={equipmentId}
                  onChange={(e) => setEquipmentId(e.target.value)}
                  placeholder="e.g. T-101"
                />
              </div>
              <div className="input-group">
                <label>Group</label>
                <input
                  type="text"
                  className="mole-input"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  placeholder="e.g. West facility"
                />
              </div>
            </FieldGrid>
          </div>
        </Section>

        <Section n={2} title="Process & Source Details">
          <div className="s1-stack">
            <div className="input-group">
              <label>Process</label>
              <CustomDropdown
                options={getProcessOptions()}
                value={currentProcessValue}
                onChange={handleProcessChange}
              />
            </div>

            {/* Hoisted Emission Factor Selection — hidden for stoichiometry and dedicated downstream process forms */}
            {!["stoichiometry", "chemical_production", "nitric_acid_production", "adipic_acid_production", "asphalt_blowing"].includes(processType) && (
              <div className="input-group">
                <div className="s1-method">
                  <label style={{ margin: 0 }}>Method</label>
                  <div className="methodology-toggle">
                    {(SECTION_TIERS[processType]
                      ? SECTION_TIERS[processType]
                      : processType === "drilling"
                      ? [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Standard",
                            sub: "Catalog Defaults",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "Custom Factor",
                            sub: "Saved Database Factors",
                          },
                          {
                            key: "tier2_plus",
                            tier: "Tier 2+",
                            label: "Site Gas Composition",
                            sub: "Onshore EF + Site CH₄/CO₂",
                          },
                        ]
                      : processType === "completions"
                      ? [
                          { key: "default", tier: "Tier 1", label: "Defaults", sub: "Per-event factor" },
                          { key: "custom", tier: "Tier 2", label: "Operational Data", sub: "Rate, GOR or production" },
                          { key: "specific", tier: "Tier 3", label: "Direct Measurement", sub: "Metered flowback" },
                        ]
                      : processType === "unloading"
                      ? [
                          { key: "default", tier: "Tier 1", label: "Per-Well", sub: "Per-well annual factor" },
                          { key: "custom", tier: "Tier 2", label: "Event-Based", sub: "Per-event factor" },
                          { key: "specific", tier: "Tier 3", label: "Engineering", sub: "Wellbore / plunger models" },
                        ]
                      : processType === "associated_gas_venting"
                      ? [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Regional Default",
                            sub: "Basin average factor",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "GOR Balance",
                            sub: "Oil × GOR × duration",
                          },
                          {
                            key: "specific",
                            tier: "Tier 3",
                            label: "Measurement",
                            sub: "Metered vent rate / volume",
                          },
                        ]
                      : processType === "fugitive"
                      ? [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Facility-Level",
                            sub: "Facility average",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "Equipment & Component",
                            sub: "Equipment / component count",
                          },
                          {
                            key: "specific",
                            tier: "Tier 3",
                            label: "Screening / OGI / Meas.",
                            sub: "Method 21, OGI, Direct Rate",
                          },
                        ]
                      : [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Standard",
                            sub: "Catalog Defaults",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "Regional / Lab",
                            sub: "Ticket / Presets / Custom",
                          },
                          {
                            key: "specific",
                            tier: "Tier 3",
                            label: "Measurement / GC",
                            sub: "CEMS / Analysis",
                          },
                        ]
                    )
                      // Library factors (the site factor database: calculated or equipment factors) are a
                      // separate choice from the API Compendium tiers
                      .concat([{ key: "library", tier: "", label: "Library factor", sub: "Site factor database" }])
                      .filter((item) => {
                        const type = item.key;
                        if (SECTION_TIERS[processType]) return true;
                        if (
                          type === "custom" &&
                          ["drilling", "pneumatic", "tank", "tank_flashing", "tank_working", "tank_breathing",
                           "venting", "blowdown", "loading", "separation"].includes(processType)
                        )
                          return false;
                        if (processType === "drilling") return true;
                        if (processType === "loading" && type === "specific")
                          return false;
                        if (processType === "separation" && type === "specific")
                          return false;
                        if (
                          ["agr", "dehydrator"].includes(processType) &&
                          (type === "default" || type === "custom")
                        )
                          return false;
                        return true;
                      })
                      .map((item) => {
                        const type = item.key;
                        const isActive = sourceType === type;
                        return (
                          <button
                            key={type}
                            type="button"
                            className={`tier-selector-btn ${isActive ? "active" : ""}`}
                            onClick={() => {
                              if (type !== sourceType) resetProcessInputs();
                              setSourceType(type);
                              if (processType === "drilling") {
                                if (type === "default") {
                                  handleFormChange("unit", "well");
                                } else {
                                  handleFormChange("unit", "days");
                                }
                              }
                            }}
                          >
                            <span className="tier-tag">{item.tier}</span>
                            <span className="tier-label">{item.label}</span>
                          </button>
                        );
                      })}
                  </div>
                </div>


                {/* TIER 1: Standard API Tabulated Factors */}
                {sourceType === "default" && !sectionMethodActive(formData) && !SECTION_PROCESSES[processType] &&
                  !["associated_gas_venting", "completions", "unloading"].includes(processType) && (
                  <CustomDropdown
                    options={fuelOptions}
                    value={formData.fuel || ""}
                    onChange={(val) => handleFormChange("fuel", val)}
                    placeholder="Select factor"
                    renderOption={renderFactorOption}
                  />
                )}

                {/* TIER 2: Regional / Measured / Supplier Factors */}
                {((sourceType === "custom" && !["associated_gas_venting", "completions", "unloading", "fugitive"].includes(processType)) || sourceType === "library") && (
                  <div className="tier2-mode-container">
                    {sourceType === "custom" ? (
                      <>

                        {tier2Mode === "override" && (
                          <div className="tier2-override-card">
                            {/* Base Fuel Dropdown */}
                            <div>
                              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "#374151", marginBottom: "4px" }}>
                                Fuel
                              </label>
                              <CustomDropdown
                                options={fuelOptions}
                                value={formData.fuel || ""}
                                onChange={(val) => {
                                  handleFormChange("fuel", val);
                                  setActivePresetId("");
                                }}
                                placeholder="Select fuel"
                                renderOption={renderFactorOption}
                              />
                            </div>

                            {/* Presets Section */}
                            <div className="official-presets-section">
                              <div className="official-presets-header">
                                <span className="official-presets-title">
                                  <BookOpen size={14} style={{ color: "var(--accent-color, #ff6600)" }} />
                                  Presets
                                </span>
                              </div>
                              <div className="official-presets-chips">
                                {getPresetsForFuel(formData.fuel, streamType).map((preset) => (
                                  <button
                                    key={preset.id}
                                    type="button"
                                    className={`preset-chip ${activePresetId === preset.id ? "active" : ""}`}
                                    onClick={() => handleApplyPreset(preset)}
                                    title={preset.description}
                                  >
                                    {hideApiCitation(preset.citation) && <span className={`preset-citation-badge ${preset.citationType}`}>
                                      {hideApiCitation(preset.citation)}
                                    </span>}
                                    <span className="preset-name">{preset.shortLabel || preset.name}</span>
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Measured Properties Grid */}
                            <div className="tier2-inputs-grid">
                              <div>
                                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "#374151", marginBottom: "4px" }}>
                                  HHV
                                </label>
                                <div style={{ display: "flex", gap: "6px" }}>
                                  <input
                                    type="number"
                                    step="any"
                                    className="mole-input"
                                    style={{ flex: 1, padding: "6px 8px", fontSize: "0.85rem" }}
                                    placeholder="e.g. 1085"
                                    value={formData.hhv || ""}
                                    onChange={(e) => {
                                      handleFormChange("hhv", e.target.value);
                                      setActivePresetId("");
                                    }}
                                  />
                                  <select
                                    className="mole-input"
                                    style={{ width: "110px", padding: "6px 8px", fontSize: "0.8rem" }}
                                    value={formData.hhv_unit || "BTU/scf"}
                                    onChange={(e) => handleFormChange("hhv_unit", e.target.value)}
                                  >
                                    <option value="BTU/scf">BTU/scf</option>
                                    <option value="MJ/m3">MJ/m³</option>
                                    <option value="kcal/m3">kcal/m³</option>
                                    <option value="BTU/gal">BTU/gal</option>
                                    <option value="BTU/lb">BTU/lb</option>
                                    <option value="MJ/kg">MJ/kg</option>
                                  </select>
                                </div>
                              </div>

                              <div>
                                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "#374151", marginBottom: "4px" }}>
                                  Density (kg/m³)
                                </label>
                                <input
                                  type="number"
                                  step="any"
                                  className="mole-input"
                                  style={{ width: "100%", padding: "6px 8px", fontSize: "0.85rem" }}
                                  placeholder="e.g. 840.0 for Gasoil NA 8110"
                                  value={fuelDensity}
                                  onChange={(e) => {
                                    setFuelDensity(e.target.value);
                                    setActivePresetId("");
                                  }}
                                />
                              </div>
                            </div>

                            {/* Data Source / Audit Reference Field */}
                            <div>
                              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "#374151", marginBottom: "4px" }}>
                                Ticket / lab ref
                              </label>
                              <input
                                type="text"
                                className="mole-input"
                                style={{ width: "100%", padding: "6px 8px", fontSize: "0.85rem" }}
                                placeholder="e.g. Ticket #4902-B"
                                value={dataSourceRef}
                                onChange={(e) => setDataSourceRef(e.target.value)}
                              />
                            </div>

                                                      </div>
                        )}

                      </>
                    ) : (
                      <div>
                        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                          <div style={{ flex: 1 }}>
                            <CustomDropdown
                              options={fuelOptions}
                              value={formData.fuel || ""}
                              onChange={(val) => handleFormChange("fuel", val)}
                              placeholder="Select saved factor"
                            />
                          </div>
                          {user?.role === "admin" && <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setIsQuickAddModalOpen(true)}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "8px 12px",
                              fontSize: "0.8rem",
                              whiteSpace: "nowrap",
                            }}
                          >
                            <PlusCircle size={15} />
                            <span>New library factor</span>
                          </button>}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {showsTier3Factors && (
                    <>
                      <CustomDropdown
                        options={fuelOptions}
                        value={formData.fuel || ""}
                        onChange={(val) => handleFormChange("fuel", val)}
                        placeholder="Base factor (optional)"
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
                          Gas analysis
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
        </Section>

        <Section n={3} title="Activity Data">
          <div className="s1-inputs">{renderSpecificForm()}</div>
          <MoreOptions label="Uncertainty">
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
            </div>
          </div>
          </MoreOptions>
        </Section>

        <div className="s1-actions">
          <button
            className="btn-add-draft"
            disabled={submitting}
            onClick={() => handleAddEntry("Draft")}
            style={{
              flex: 1,
              background: "rgba(255, 255, 255, 0.9)",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
              fontWeight: 600,
              padding: "10px 16px",
              borderRadius: "10px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Saving..." : "Save draft"}
          </button>
          <button
            className="btn-add-activity"
            disabled={submitting}
            onClick={() => handleAddEntry("Verified")}
            style={{
              flex: 1.5,
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Saving..." : "Submit"}
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
            {/* BUG-095: options come from the server facets, not from the 10 rows of the current page */}
            {facetYears
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
            {Object.keys(PROCESS_TYPES).map((p) => (
              <option key={p} value={p}>
                {typeof PROCESS_TYPES[p] === "string" ? PROCESS_TYPES[p] : PROCESS_TYPES[p]?.label || p}
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
            onClick={async () => {
              // BUG-095: export every matching record (server-side filters), not just the visible page
              try {
                const res = await api.get("/emissions/", {
                  params: {
                    scope: "1",
                    limit: "all",
                    ...(filterYear && { year: filterYear }),
                    ...(filterProcess && { process_type: filterProcess }),
                    ...(filterSearch && { search: filterSearch }),
                  },
                });
                const rows = res.data?.emissions || res.data?.data || res.data || [];
                exportToCSV(Array.isArray(rows) ? rows : [], "scope1_export.csv");
              } catch (err) {
                toast.error(err.response?.data?.error || "Export failed");
              }
            }}
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
                <th>Period</th>
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
                        colSpan="22"
                        style={{
                          textAlign: "center",
                          color: "var(--text-secondary)",
                          padding: "30px",
                        }}
                      >
                        {entries.length === 0
                          ? loading
                            ? "Loading…"
                            : "No entries yet"
                          : "No results match your filters"}
                      </td>
                    </tr>
                  );
                return filteredEntries.map((entry) => {
                  const factorType = factorTypeLabel(entry);
                  return (
                    <tr key={entry.id}>
                      <td>{entry.month ? `${entry.year}-${String(entry.month).padStart(2, "0")}` : entry.year}</td>
                      <td>{entry.activity || "-"}</td>
                      <td>{entry.facility_name || entry.region || "-"}</td>
                      <td>{entry.division || "-"}</td>
                      <td>{entry.field || "-"}</td>
                      <td>{entry.group_name || entry.group || "-"}</td>
                      <td>{entry.equipment_id || "-"}</td>
                      <td>
                        {(() => {
                          const k = entry.process || entry.process_type;
                          const v = PROCESS_TYPES[k];
                          // keys the form does not list (e.g. stoichiometry) get a readable label
                          const other = { stoichiometry: "Carbon Mass Balance (Stoichiometry)" };
                          return (typeof v === "string" ? v : v?.label) || other[k] ||
                            String(k || "").replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
                        })()}
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
                        {(entry.amount ?? entry.quantity) != null && (entry.amount ?? entry.quantity) !== ""
                          ? `${formatNumber(entry.amount ?? entry.quantity, 2)} ${entry.unit || ""}`
                          : "-"}
                      </td>
                      <td>{formatEmission(entry.co2_emissions || 0, 3)}</td>
                      <td>{formatEmission(entry.ch4_emissions || 0, 5)}</td>
                      <td>{formatEmission(entry.n2o_emissions || 0, 5)}</td>
                      <td
                        style={{
                          color: "var(--accent-color)",
                          fontWeight: 600,
                        }}
                      >
                        {formatEmission(entry.co2e_total, 3)}
                        {/* BUG-092: every record shows its maker-checker status */}
                        {entry.status && (
                          <span
                            title={`Status: ${entry.status}`}
                            style={{
                              marginLeft: "8px",
                              fontSize: "0.65rem",
                              padding: "1px 5px",
                              borderRadius: "4px",
                              ...({
                                Verified: { background: "#dcfce7", color: "#166534" },
                                Pending: { background: "#fef9c3", color: "#854d0e" },
                                Rejected: { background: "#fee2e2", color: "#b91c1c" },
                                Draft: { background: "#e0e7ff", color: "#3730a3" },
                              }[entry.status] || { background: "#f1f5f9", color: "#334155" }),
                            }}
                          >
                            {entry.status}
                          </span>
                        )}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            (entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0)
                              ? "#10b981"
                              : "var(--text-muted)",
                        }}
                        title="Standard Combined Uncertainty (1σ)"
                      >
                        {(entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0)
                          ? `±${(entry.uncertainty_co2 * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            (entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0)
                              ? "#3b82f6"
                              : "var(--text-muted)",
                        }}
                        title="Standard Combined Uncertainty (1σ)"
                      >
                        {(entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0)
                          ? `±${(entry.uncertainty_ch4 * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            (entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0)
                              ? "#8b5cf6"
                              : "var(--text-muted)",
                        }}
                        title="Standard Combined Uncertainty (1σ)"
                      >
                        {(entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0)
                          ? `±${(entry.uncertainty_n2o * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            (entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0)
                              ? "#10b981"
                              : "var(--text-muted)",
                        }}
                        title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                      >
                        {(entry.uncertainty_co2 != null && Number(entry.co2_emissions) > 0)
                          ? `±${(entry.uncertainty_co2 * 200).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            (entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0)
                              ? "#3b82f6"
                              : "var(--text-muted)",
                        }}
                        title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                      >
                        {(entry.uncertainty_ch4 != null && Number(entry.ch4_emissions) > 0)
                          ? `±${(entry.uncertainty_ch4 * 200).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          textAlign: "center",
                          fontSize: "0.82rem",
                          color:
                            (entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0)
                              ? "#8b5cf6"
                              : "var(--text-muted)",
                        }}
                        title="Expanded Uncertainty (95% Confidence Interval, k=2)"
                      >
                        {(entry.uncertainty_n2o != null && Number(entry.n2o_emissions) > 0)
                          ? `±${(entry.uncertainty_n2o * 200).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td style={{ textAlign: "center", whiteSpace: "nowrap" }}>
                        <button
                          className="icon-button"
                          onClick={() => handleInspect(entry)}
                          style={{ color: "#3b82f6", marginRight: "6px" }}
                          title="Inspect Calculation Details"
                        >
                          <Eye size={16} />
                        </button>
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
                  colSpan="14"
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
                <td colSpan="7"></td>
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

      {inspectRecord && (
        <CalculationDetails
          calculation={inspectRecord}
          onClose={() => setInspectRecord(null)}
        />
      )}

      <ConfirmModal
        isOpen={Boolean(deleteConfirmId)}
        title="Delete Scope 1 Emission"
        message="Are you sure you want to delete this emission entry? This action cannot be undone."
        confirmLabel="Delete"
        confirmVariant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirmId(null)}
      />

      <QuickAddCustomFactorModal
        isOpen={isQuickAddModalOpen}
        onClose={() => setIsQuickAddModalOpen(false)}
        onFactorCreated={handleFactorCreated}
        processType={processType}
        defaultParentFuel={formData.fuel}
      />
    </div>
  );
};

export default Scope1Form;
