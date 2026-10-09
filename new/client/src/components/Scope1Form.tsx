import React, { useState, useEffect, useRef } from "react";
import { toCsv } from "../utils/chartExport";
import { Input, Field } from "../ui";
import { NativeSelect } from "../ui/NativeSelect";
import api from "../api";
import CustomDropdown from "./CustomDropdown";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { PROCESS_TYPES, hideApiCitation, factorTypeLabel, processLabel } from "./scope1-form/shared";
import Scope1ProcessSection from "./scope1-form/Scope1ProcessSection";
import Scope1OptionsSection from "./scope1-form/Scope1OptionsSection";
import Scope1History, { Scope1HistoryEntry } from "./scope1-form/Scope1History";
import "./ScopeTables.css";
import "./Scope1Form.css";

// Sub-components
import Scope1ImportWizard from "./Scope1ImportWizard";
import ConfirmModal from "./ConfirmModal";
import QuickAddCustomFactorModal from "./QuickAddCustomFactorModal";
import CalculationDetails, { CalculationRecord } from "./CalculationDetails";
import { Section, FieldGrid } from "./scope1/ui";
import CombustionForm from "./scope1/CombustionForm";
import DrillingForm from "./scope1/DrillingForm";
import CompletionsForm from "./scope1/CompletionsForm";
import UnloadingForm from "./scope1/UnloadingForm";
import BlowdownForm from "./scope1/BlowdownForm";
import AGRForm from "./scope1/AGRForm";
import DehydratorForm from "./scope1/DehydratorForm";
import PneumaticsForm from "./scope1/PneumaticsForm";
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
} from "../utils/EmissionFactors";
import {
  formatUncertainty,
  getSegmentColor,
  getSegmentBgColor,
  convertActivityData,
} from "../utils/emissionFactorsAPI";
import { hhvToBtu } from "../utils/hhv";

interface FacilityItem {
  id: string | number;
  name: string;
  activity?: string;
  division?: string;
  field?: string;
  [key: string]: any;
}

interface EmissionSourceItem {
  id: string | number;
  name?: string;
  equipment_id?: string;
  type?: string;
  facility_id?: string | number;
  [key: string]: any;
}

export const Scope1Form: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();
  // BUG-082: the inspector label reflects the org's active GWP standard
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Core Identity State
  const [year, setYear] = useState<string | number>(new Date().getFullYear());
  const [month, setMonth] = useState<string | number>(new Date().getMonth() + 1);
  const [facilityId, setFacilityId] = useState<string>("");
  const [activity, setActivity] = useState<string>("");
  const [division, setDivision] = useState<string>("");
  const [field, setField] = useState<string>("");

  const [processType, setProcessType] = useState<string>("combustion");
  const [streamType, setStreamType] = useState<string>("Upstream"); // 'Upstream', 'Midstream', 'Downstream'
  const [groupName, setGroupName] = useState<string>("");
  const [equipmentId, setEquipmentId] = useState<string>("");
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | number | null>(null);

  // Dynamic Form Data State
  const [formData, setFormData] = useState<Record<string, any>>({});

  // Hoisted State for Factor Selection
  const [sourceType, setSourceType] = useState<string>("default"); // 'default', 'custom', 'specific'
  const [fuelOptions, setFuelOptions] = useState<Array<{ value: string; label: string; factor?: any }>>([]);
  const [customFactors, setCustomFactors] = useState<any[]>([]);

  // Specific Factors State
  const [specFactors, setSpecFactors] = useState<Record<string, string>>({
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
  const [uncertainty, setUncertainty] = useState<{
    co2?: number | null;
    ch4?: number | null;
    n2o?: number | null;
    [key: string]: any;
  }>({
    co2: null,
    ch4: null,
    n2o: null,
  });
  const [userUncertainty, setUserUncertainty] = useState<{
    co2?: string | number;
    ch4?: string | number;
    n2o?: string | number;
    [key: string]: any;
  }>({
    co2: "",
    ch4: "",
    n2o: "",
  });
  const [meterUncertaintyPct, setMeterUncertaintyPct] = useState<string | number>("2.0"); // Default Tier 3 ±2.0%
  const [gcUncertaintyPct, setGcUncertaintyPct] = useState<string | number>("");

  // Tier 2 Enhanced State
  const tier2Mode = "override"; // Tier 2 (API Compendium) = measured fuel properties; library factors are separate
  const [activePresetId, setActivePresetId] = useState<string>("");
  const [fuelDensity, setFuelDensity] = useState<string | number>("");
  const [dataSourceRef, setDataSourceRef] = useState<string>("");
  const [isQuickAddModalOpen, setIsQuickAddModalOpen] = useState<boolean>(false);

  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [emissionSources, setEmissionSources] = useState<EmissionSourceItem[]>([]);
  const [emissionSourceId, setEmissionSourceId] = useState<string>("");
  const [entries, setEntries] = useState<Scope1HistoryEntry[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);

  const [showGasCalc, setShowGasCalc] = useState<boolean>(false);
  // the six uncertainty columns are hidden by default (the table is 22 columns wide)
  const [showUncertainty, setShowUncertainty] = useState<boolean>(false);
  const [inspectRecord, setInspectRecord] = useState<CalculationRecord | null>(null);
  const [importModal, setImportModal] = useState<{
    isOpen: boolean;
    type?: string;
  }>({
    isOpen: false,
    type: "activity",
  });
  const RECORDS_PER_PAGE = 10;

  // Table filter state
  const [filterYear, setFilterYear] = useState<string>("");
  const [facetYears, setFacetYears] = useState<Array<string | number>>([]);
  useEffect(() => {
    api.get("/filters/available")
      .then((r) => setFacetYears(Array.isArray(r.data?.years) ? r.data.years : []))
      .catch(() => setFacetYears([]));
  }, []);
  const [filterProcess, setFilterProcess] = useState<string>("");
  const [filterSearch, setFilterSearch] = useState<string>("");

  useEffect(() => {
    loadFacilities();
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
          const factor = (API_FACTORS as Record<string, any>)[key];

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
          factor: (API_FACTORS as Record<string, any>)[k],
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
  const renderFactorOption = (option: any) => {
    if (!option.factor) return option.label;

    const factor = option.factor;
    const segment = factor.segment || factor.stream;
    const factorUnc = factor.uncertainty;
    const maxUncertainty = factorUnc
      ? Math.max(
          factorUnc.co2 || 0,
          factorUnc.ch4 || 0,
          factorUnc.n2o || 0,
        )
      : 0;

    return (
      <div className="flex! items-center! justify-between! w-full! gap-[8px]!">
        <div className="flex! items-center! gap-[6px]! flex-1! min-w-0!">
          <span className="overflow-hidden! [text-overflow:ellipsis]! whitespace-nowrap!">
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
        {factorUnc && maxUncertainty > 0 && (
          <span
            className="text-[length:0.65rem]! text-[color:var(--color-legacy-9ca3af)]! font-medium! shrink-0!"
            title={`Uncertainty: CO₂ ${formatUncertainty(factorUnc.co2)}, CH₄ ${formatUncertainty(factorUnc.ch4)}, N₂O ${formatUncertainty(factorUnc.n2o)}`}
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

  useEffect(() => {
    setFormData((prev) => {
      const isCustomId = !isNaN(parseInt(prev.fuel)) && String(parseInt(prev.fuel)) === String(prev.fuel);
      if (sourceType === "library" && !isCustomId) return { ...prev, fuel: "" };
      if (sourceType !== "library" && isCustomId && prev.fuel) return { ...prev, fuel: "" };
      return prev;
    });
  }, [sourceType, tier2Mode]);

  const handleApplyPreset = (preset: any) => {
    setActivePresetId(preset.id);
    const matched = fuelOptions.find(
      (opt) => opt.value.toLowerCase() === preset.defaultMatchingFuel.toLowerCase(),
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

  const handleFactorCreated = (newFactor: any) => {
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
      (API_FACTORS as Record<string, any>)[formData.fuel]
    ) {
      const f = (API_FACTORS as Record<string, any>)[formData.fuel];
      setSpecFactors({
        co2: String(f.co2 || 0),
        co2Unit: f.unit || "kg/m3",
        ch4: String(f.ch4 || 0),
        ch4Unit: f.unit || "kg/m3",
        n2o: String(f.n2o || 0),
        n2oUnit: f.unit || "kg/m3",
        co: String(f.co || 0),
        coUnit: f.unit || "kg/m3",
      });
    }

    // Auto-populate Uncertainty
    let factorToUse: any = null;

    // 1. Combustion / General Fuel / Any selected from main dropdown
    if (formData.fuel) {
      if (sourceType === "custom") {
        const found = customFactors.find(
          (f) => f.id.toString() === formData.fuel?.toString(),
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
        if ((API_FACTORS as Record<string, any>)[formData.fuel]) {
          factorToUse = (API_FACTORS as Record<string, any>)[formData.fuel];
        }
        // Fallback: Try matching by 'code' property for custom forms (Completions/Unloading)
        else {
          const found = Object.values(API_FACTORS).find(
            (f: any) => f.code === formData.fuel,
          );
          if (found) factorToUse = found;
        }
      }
    }
    // 2. Drilling (Mud Degassing) - Table 6-3 well default or API onshore mud defaults
    else if (processType === "drilling") {
      if (sourceType === "default") {
        factorToUse =
          (API_FACTORS as Record<string, any>)["Drilling - Gas Well Drilling (Simplified Default)"];
      } else if (sourceType === "tier2_plus") {
        const mudType = formData.mud_type || "water_based";
        const mudKey =
          mudType === "oil" || mudType === "oil_based"
            ? "Drilling - Mud Degassing (Oil Based)"
            : "Drilling - Mud Degassing (Water Based)";
        if ((API_FACTORS as Record<string, any>)[mudKey]) {
          factorToUse = (API_FACTORS as Record<string, any>)[mudKey];
        }
      }
    }

    updateUncertaintyFromFactor(factorToUse);
  }, [sourceType, formData.fuel, processType, formData.mud_type]);

  const updateUncertaintyFromFactor = (f: any) => {
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

  // Form data (fuel included) is reset when the process changes in handleProcessChange
  // (resetProcessInputs), before its defaults are set. Reset effects on processType also ran after the
  // new section's own default effects (child effects run first) and wiped them: fugitive Tier 1 then
  // submitted without facility_type (422) or fuel, and drilling lost its "well" unit.

  const loadFacilities = async () => {
    try {
      const res = await api.get("/facilities/");
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setFacilities(data);
      const opDefaults = getUserOperationalDefaults(user, data);
      if (opDefaults.defaultFacilityId) {
        setFacilityId((prev) => prev || String(opDefaults.defaultFacilityId));
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
        setFacilityId(String(opDefaults.defaultFacilityId));
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

  const exportToCSV = (data: any[], filename: string) => {
    if (!data || data.length === 0) {
      toast.error("No data to export");
      return;
    }
    const headers = [
      "Date",
      "Activity",
      "Region / Facility",
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
      e.facility_name || e.region || "",
      e.division || "",
      e.field || "",
      e.group_name || e.group || "",
      e.equipment_id || "",
      processLabel(e),
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
    // shared CSV writer: also neutralises cells that a spreadsheet would run as a formula (=, +, -, @)
    const blob = new Blob(["\uFEFF" + toCsv(headers, rows)], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${data.length} records`);
  };

  const getEmissionSourceOptions = () => {
    const opts: Array<{ value: string; label: string; subLabel?: string }> = [
      { value: "", label: "Select Emission Source..." },
    ];
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

  // S1K-F14: one request per page / filter change, and only the latest response is rendered (several
  // effects fired duplicate requests and a late response could show another page's rows)
  const entriesRequestSeq = useRef(0);
  const loadEntries = async () => {
    const seq = ++entriesRequestSeq.current;
    setLoading(true);
    try {
      // BUG-UI-07 FIX: Include all active filter params in the API request
      const filterParams = new URLSearchParams({
        scope: "1",
        limit: String(RECORDS_PER_PAGE),
        offset: String((currentPage - 1) * RECORDS_PER_PAGE),
        ...(filterYear && { year: filterYear }),
        ...(filterProcess && { process: filterProcess }),
        ...(filterSearch && { search: filterSearch }),
      });
      const res = await api.get(`/emissions?${filterParams}`);
      if (seq !== entriesRequestSeq.current) return; // a newer request was sent meanwhile

      // Safe handling of response data
      let allEntries: Scope1HistoryEntry[] = [];
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
        allEntries = (possibleArray as Scope1HistoryEntry[]) || [];
      }

      setEntries(allEntries);

      const totalCount =
        res.headers["x-total-count"] || (res.data && res.data.total) || 0;
      if (totalCount) {
        setTotalPages(Math.max(1, Math.ceil(parseInt(String(totalCount)) / RECORDS_PER_PAGE)));
      } else {
        setTotalPages(Math.max(1, Math.ceil(allEntries.length / RECORDS_PER_PAGE)));
      }
    } catch (error) {
      console.error("Failed to load entries:", error);
    } finally {
      if (seq === entriesRequestSeq.current) setLoading(false);
    }
  };

  const handleFormChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Keep the calculation-method keys (activity_key / vent_method / combustion_method) in step
  // with the process and tier, including after the form is reset
  const sectionChoice = currentChoice(formData);
  useEffect(() => {
    // processes whose tiers are these methods: move off a tier the process does not offer
    const tiers = SECTION_TIERS[processType];
    if (tiers && sourceType !== "library" && !tiers.some((t: any) => t.key === sourceType)) {
      setSourceType(tiers[0].key);
      return;
    }
    syncSectionChoice(processType, sourceType, formData, handleFormChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processType, sourceType, sectionChoice]);

  const handleAddEntry = async (status: "Draft" | "Verified" = "Verified") => {
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
        if (tier === "tier1" || (sourceType as string) === "default") {
          const wells = parseFloat(formData.well_count || formData.wells || formData.amount || 0);
          if (wells <= 0) {
            toast.warning("Number of wells must be greater than zero for Tier 1 liquids unloading");
            return;
          }
        } else if (tier === "tier2" || (sourceType as string) === "custom") {
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
        if (tier === "tier1" || (sourceType as string) === "default") {
          const events = parseFloat(formData.amount || formData.events || 0);
          if (events <= 0 || isNaN(events)) {
            toast.warning("Number of completion events must be greater than zero for Tier 1 completions");
            return;
          }
        } else if (tier === "tier2" || (sourceType as string) === "custom") {
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
        if (!formData.vent_method) {
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
      const processInputs: Record<string, any> = {};

      // Copy all formData into process-specific object
      Object.keys(formData).forEach((key) => {
        const value = formData[key];
        // Parse numeric fields
        if (value !== undefined && value !== null && value !== "") {
          if (
            typeof value === "string" &&
            !isNaN(Number(value)) &&
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
        const u = formData.tank_unit || formData.unit || "bbl";
        if (u !== "bbl") {
          finalAmount = convertActivityData(amt, u, "bbl");
          finalUnit = "bbl";
        } else {
          finalAmount = amt;
          finalUnit = "bbl";
        }
        // one activity representation: the method inputs carry the converted bbl too (the server
        // refuses a row whose unit and tank_unit disagree, S1K-F9)
        processInputs.amount = finalAmount;
        processInputs.quantity = finalAmount;
        processInputs.tank_unit = "bbl";
      }

      // 3. Pneumatics
      if (processType === "pneumatic") {
        if (sourceType === "specific") {
          const rate = parseFloat(formData.pneu_bleed_rate || 0);
          const u = formData.pneu_bleed_unit || "scf";
          if (rate > 0 && u !== "scf") {
            processInputs.pneu_bleed_rate = convertActivityData(
              rate,
              u,
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
          // the lift-type select displays "Plunger lift" until changed: send what is displayed (the server
          // requires it; it used to assume non-plunger)
          processInputs.unloading_type = formData.unloading_type || formData.unload_type || "plunger";
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
            const per: Record<string, [number, string]> = {
              scfh: [1, "scf"],
              "scf/day": [1 / 24, "scf"],
              scfm: [60, "scf"],
              "m3/hr": [1, "m3"],
              "m3/day": [1 / 24, "m3"],
            };
            const multiplier = per[formData.vent_rate_unit || "scfh"] || [1, "scf"];
            finalAmount = parseFloat(formData.vent_rate || 0) * multiplier[0] * parseFloat(formData.venting_duration || 0);
            finalUnit = multiplier[1];
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
        const num = (k: string) => parseFloat(formData[k] || 0) || 0;
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
        finalAmount = formData.amount ? parseFloat(formData.amount) : undefined as any;
        finalUnit = formData.amount ? formData.unit || "count" : undefined as any;
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
      const finalPayload: Record<string, any> = {
        // Identity
        facility_id: parseInt(facilityId),
        year: parseInt(String(year)),
        month: parseInt(String(month)),
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
        density: fuelDensity ? parseFloat(String(fuelDensity)) : undefined,
        fuel_density: fuelDensity ? parseFloat(String(fuelDensity)) : undefined,
        data_source_ref: dataSourceRef || undefined,

        // HHV & Combustion Parameters — for Tier 2 custom fuel properties or Tier 3 specific factor mode.
        // The HHV is sent in Btu with its real basis (Btu/scf, Btu/gal or Btu/lb); the server converts it
        // to the fuel's basis (with the density when that crosses volume / mass). It used to be sent as
        // "BTU/unit", which the server reads in the catalog basis: an MJ/kg value for diesel (Btu/gal
        // basis) was taken as Btu/gal, ~7x off.
        ...(() => {
          const isTier2Override = sourceType === "custom" && tier2Mode === "override";
          if ((sourceType !== "specific" && !isTier2Override) || !formData.hhv) return {};
          const { hhv, hhvUnit } = hhvToBtu(parseFloat(formData.hhv), formData.hhv_unit || "BTU/scf");
          return {
            hhv,
            hhv_unit: hhvUnit,
            hhv_original: parseFloat(formData.hhv), // audit trail
            hhv_original_unit: formData.hhv_unit || "BTU/scf",
            combustion_efficiency: formData.combustion_efficiency
              ? parseFloat(formData.combustion_efficiency) / 100.0
              : undefined,
            // flaring: CH4 destroyed (eta_d), separate from the carbon conversion (eta_c)
            destruction_efficiency: formData.destruction_efficiency
              ? parseFloat(formData.destruction_efficiency) / 100.0
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
    } catch (error: any) {
      console.error("Failed to add entry:", error);
      const msg = error.response?.data?.error || "Failed to add entry";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleInspect = (entry: Scope1HistoryEntry) => {
    const pType = entry.process || entry.process_type || "Scope 1";
    const fuelVal = entry.fuel || entry.fuel_type || "N/A";
    const qty = entry.amount || entry.quantity || 0;
    const unitVal = entry.unit || "unit";

    let payload: Record<string, any> = {};
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
    const pDef = (PROCESS_TYPES as Record<string, any>)[entry.process || entry.process_type || ""];
    const pLabel = (typeof pDef === "string" ? pDef : pDef?.label) || pType;

    setInspectRecord({
      process_type: `Scope 1 - ${pLabel}`,
      fuel: fuelVal,
      amount: Number(qty),
      unit: unitVal,
      facility: facName,
      year: entry.year ? Number(entry.year) : undefined,
      month: entry.month ? Number(entry.month) : undefined,
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
        co2: efCo2 != null ? Number(efCo2) : undefined,
        ch4: efCh4 != null ? Number(efCh4) : undefined,
        n2o: efN2o != null ? Number(efN2o) : undefined,
      },
      uncertainty: {
        co2: entry.uncertainty_co2 != null ? Number(entry.uncertainty_co2) : undefined,
        ch4: entry.uncertainty_ch4 != null ? Number(entry.uncertainty_ch4) : undefined,
        n2o: entry.uncertainty_n2o != null ? Number(entry.uncertainty_n2o) : undefined,
      },
    });
  };

  const handleDelete = (id: string | number) => {
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

  const renderProcessForm = (props: any) => {
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

  const getFacilityOptions = () => [
    { value: "", label: "Select Region..." },
    ...facilities.map((f) => ({
      value: f.id.toString(),
      label: f.name,
      subLabel: f.field,
    })),
  ];

  const getProcessOptions = () => {
    const options: any[] = [];
    PROCESS_GROUPS.forEach((group: any) => {
      options.push({
        label: group.label,
        value: `header-${group.label}`,
        isHeader: true,
      });
      group.options.forEach((optKey: string) => {
        if ((PROCESS_TYPES as Record<string, any>)[optKey]) {
          const pDef = (PROCESS_TYPES as Record<string, any>)[optKey];
          const pLabel = typeof pDef === "string" ? pDef : pDef?.label || optKey;
          options.push({
            value: `${group.id}|${optKey}`,
            label: pLabel,
          });
        }
      });
    });
    return options;
  };

  const handleProcessChange = (val: string) => {
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

  const handleGasApply = (res: any) => {
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
      const pct = (...keys: string[]) => keys.reduce((t, k) => t + (parseFloat(rc[k]) || 0), 0);
      const set = (fName: string, v?: number) => handleFormChange(fName, v && v > 0 ? v : undefined);
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
    toast.show("Factors updated from Gas Analysis", "success");
  };

  return (
    <div className="scope-form">
      <div className="calc-panel s1-form">
        <h2 className="[font-size:var(--text-md)] [font-weight:700] [color:var(--s1-ink)] [margin:0_0_18px]">New entry</h2>

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
            <Field className="input-group" label="Year">
              <Input
                type="number"
                value={year || ""}
                onChange={(e) => setYear(e.target.value)}
              />
            </Field>
            <Field className="input-group" label="Month">
              <NativeSelect
                className="component-select"
                value={month || 1}
                onChange={(e) => setMonth(e.target.value)}
              >
                {[...Array(12)].map((_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {new Date(2000, i, 1).toLocaleString(undefined, { month: "short" })}
                  </option>
                ))}
              </NativeSelect>
            </Field>
          </FieldGrid>
          {(activity || division || field) && (
            <div className="[margin-top:6px] [font-size:var(--text-sm)] [color:var(--s1-muted)]">{[activity, division, field].filter(Boolean).join(" · ")}</div>
          )}
          <div className="[margin-top:16px]">
            <div className="[font-size:var(--text-sm)] [font-weight:600] [color:var(--s1-muted)] [text-transform:uppercase] [letter-spacing:0.04em] [margin-bottom:10px]">Source details</div>
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
              <Field className="input-group" label="Equipment ID">
                <Input
                  type="text"
                  value={equipmentId}
                  onChange={(e) => setEquipmentId(e.target.value)}
                  placeholder="e.g. T-101"
                />
              </Field>
              <Field className="input-group" label="Group">
                <Input
                  type="text"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  placeholder="e.g. West facility"
                />
              </Field>
            </FieldGrid>
          </div>
        </Section>

        <Scope1ProcessSection
          activePresetId={activePresetId}
          currentProcessValue={currentProcessValue}
          dataSourceRef={dataSourceRef}
          formData={formData}
          fuelDensity={fuelDensity}
          fuelOptions={fuelOptions}
          getProcessOptions={getProcessOptions}
          handleApplyPreset={handleApplyPreset}
          handleFormChange={handleFormChange}
          handleProcessChange={handleProcessChange}
          processType={processType}
          renderFactorOption={renderFactorOption}
          resetProcessInputs={resetProcessInputs}
          setActivePresetId={setActivePresetId}
          setDataSourceRef={setDataSourceRef}
          setFuelDensity={setFuelDensity}
          setIsQuickAddModalOpen={setIsQuickAddModalOpen}
          setShowGasCalc={setShowGasCalc}
          setSourceType={setSourceType}
          setSpecFactors={setSpecFactors}
          showsTier3Factors={showsTier3Factors}
          sourceType={sourceType}
          specFactors={specFactors}
          streamType={streamType}
          tier2Mode={tier2Mode}
        />

        <Scope1OptionsSection
          gcUncertaintyPct={gcUncertaintyPct}
          meterUncertaintyPct={meterUncertaintyPct}
          renderSpecificForm={renderSpecificForm}
          setGcUncertaintyPct={setGcUncertaintyPct}
          setMeterUncertaintyPct={setMeterUncertaintyPct}
          setUserUncertainty={setUserUncertainty}
          sourceType={sourceType}
          uncertainty={uncertainty}
          userUncertainty={userUncertainty}
        />

        <div className="s1-actions">
          <button
            className="btn-add-draft flex-1"
            disabled={submitting}
            onClick={() => handleAddEntry("Draft")}
            style={{
              background: "rgba(255, 255, 255, 0.9)",
              border: "1px solid var(--border-color)",
              color: "var(--text-primary)",
              fontWeight: 600,
              padding: "0 16px",
              borderRadius: "10px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Saving..." : "Save draft"}
          </button>
          <button
            className="btn-add-activity flex-[1.5]"
            disabled={submitting}
            onClick={() => handleAddEntry("Verified")}
            style={{
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

      <Scope1History
        currentPage={currentPage}
        entries={entries}
        exportToCSV={exportToCSV}
        facetYears={facetYears}
        filterProcess={filterProcess}
        filterSearch={filterSearch}
        filterYear={filterYear}
        handleDelete={handleDelete}
        handleInspect={handleInspect}
        loading={loading}
        setCurrentPage={setCurrentPage}
        setFilterProcess={setFilterProcess}
        setFilterSearch={setFilterSearch}
        setFilterYear={setFilterYear}
        setImportModal={setImportModal}
        setShowUncertainty={setShowUncertainty}
        showUncertainty={showUncertainty}
        toast={toast}
        totalPages={totalPages}
      />

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
