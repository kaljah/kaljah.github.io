import React, { useState, useEffect } from "react";
import api from "../api";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { formatNumber } from "../utils/formatters";
import ColumnMappingWizard from "./ColumnMappingWizard";
import Scope2ImportWizard from "./Scope2ImportWizard";
import CalculationDetails from "./CalculationDetails";
import ConfirmModal from "./ConfirmModal";
import Scope2FormNewElectricityEntry from "./scope2-form/Scope2FormNewElectricityEntry";
import Scope2FormCalculatorGridContainer, {
  Scope2GridEntry,
} from "./scope2-form/Scope2FormCalculatorGridContainer";
import "./ScopeTables.css";

export const Scope2Form: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Identity State (Hoisted to match Scope 1)
  const [year, setYear] = useState<number | string>(new Date().getFullYear());
  const [month, setMonth] = useState<number | string>(new Date().getMonth() + 1);
  const [facilityId, setFacilityId] = useState<string>("");
  const [activity, setActivity] = useState<string>("");
  const [division, setDivision] = useState<string>("");
  const [field, setField] = useState<string>("");

  // Process/Source State
  const [gridRegion, setGridRegion] = useState<string>("");
  const [amount, setAmount] = useState<string>("");
  const [unit, setUnit] = useState<string>("kWh");
  const [sourceType, setSourceType] = useState<string>("electricity");

  // Section 8 specific state
  const [boilerEff, setBoilerEff] = useState<number | string>(0.8);
  const [transLoss, setTransLoss] = useState<number | string>(0.0);
  const [heatOutput, setHeatOutput] = useState<string>("");
  // plant efficiencies for the WRI efficiency method; blank = Compendium defaults (80 % heat, 35 % power)
  const [heatEff, setHeatEff] = useState<string>("");
  const [powerEff, setPowerEff] = useState<string>("");
  const [powerOutput, setPowerOutput] = useState<string>("");
  const [allocationMethod, setAllocationMethod] = useState<string>("wri_efficiency");

  // Result and Inspect Modals
  const [inspectRecord, setInspectRecord] = useState<any>(null);

  const [facilities, setFacilities] = useState<any[]>([]);
  const [gridFactors, setGridFactors] = useState<any[]>([]);
  const [entries, setEntries] = useState<Scope2GridEntry[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loadError, setLoadError] = useState<boolean>(false);
  const [importModal, setImportModal] = useState<{ isOpen: boolean; type?: string }>({
    isOpen: false,
    type: "activity",
  });
  const RECORDS_PER_PAGE = 10;

  useEffect(() => {
    loadFacilities();
    loadEntries();
    loadGridFactors();
  }, []);

  useEffect(() => {
    loadEntries();
  }, [currentPage]);

  // Auto-populate identity fields when facility changes
  useEffect(() => {
    if (facilityId) {
      const fac = facilities.find((f) => f.id.toString() === facilityId.toString());
      if (fac) {
        setActivity(fac.activity || "");
        setDivision(fac.division || "");
        setField(fac.field || "");
      }
    } else {
      setActivity("");
      setDivision("");
      setField("");
    }
  }, [facilityId, facilities]);

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
      console.error("Failed to load regions:", error);
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

  const loadGridFactors = async () => {
    try {
      const res = await api.get("/scope2/emission-factors");
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setGridFactors(data);
    } catch (error) {
      console.error("Failed to load grid factors:", error);
    }
  };

  const loadEntries = async () => {
    setLoading(true);
    try {
      // one page from the server (the whole list used to be downloaded on every page change)
      const res = await api.get("/scope2", {
        params: { limit: RECORDS_PER_PAGE, offset: (currentPage - 1) * RECORDS_PER_PAGE },
      });
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      const total = Array.isArray(res.data) ? data.length : Number(res.data?.total) || 0;
      setEntries(data);
      setTotalPages(Math.max(1, Math.ceil(total / RECORDS_PER_PAGE)));
      setLoadError(false);
    } catch (error) {
      console.error("Failed to load entries:", error);
      setLoadError(true);
      toast.error("Failed to load Scope 2 data");
    } finally {
      setLoading(false);
    }
  };

  // BUG-096: one list of units per source type; the unit is reset when the source type changes
  // and submit is blocked when it is not one of the displayed options
  const UNIT_OPTIONS: Record<string, Array<{ value: string; label: string }>> = {
    electricity: [
      { value: "kWh", label: "kWh" },
      { value: "MWh", label: "MWh" },
      { value: "GWh", label: "GWh" },
    ],
    indirect_steam: [
      { value: "btu", label: "Btu" },
      { value: "mmbtu", label: "MMBtu" },
      { value: "mj", label: "MJ" },
    ],
    cogen_allocation: [{ value: "tonnes", label: "Tonnes CO2e" }],
  };
  const DEFAULT_UNIT: Record<string, string> = {
    electricity: "kWh",
    indirect_steam: "mmbtu",
    cogen_allocation: "tonnes",
  };
  const unitOptions = UNIT_OPTIONS[sourceType] || UNIT_OPTIONS.electricity;
  const handleSourceTypeChange = (val: string) => {
    setSourceType(val);
    setUnit(DEFAULT_UNIT[val] || "kWh");
  };

  const handleAddEntry = async (status = "Verified") => {
    if (!year || !month || !facilityId || (sourceType === "electricity" && !gridRegion) || !amount) {
      toast.warning("Please fill in all required fields");
      return;
    }

    if (!unitOptions.some((o) => o.value === unit)) {
      toast.warning("Please select a unit");
      return;
    }

    try {
      setSubmitting(true);
      const val = parseFloat(amount);
      if (val <= 0 && sourceType !== "cogen_allocation") {
        toast.warning("Please enter a valid usage amount");
        return;
      }

      let payload: Record<string, any> = {
        year: parseInt(String(year), 10),
        month: parseInt(String(month), 10),
        facility_id: parseInt(facilityId, 10),
        activity,
        division,
        field,
        status: status,
      };

      if (sourceType === "electricity") {
        // Centralized Unit Conversion to kWh
        let electricityKwh = val;
        if (unit === "MWh") electricityKwh = val * 1000;
        else if (unit === "GWh") electricityKwh = val * 1000000;

        // BUG-099: the server resolves the grid factor and computes CO2e; no client result is sent
        payload = {
          ...payload,
          grid_region: gridRegion,
          source_type: "electricity",
          electricity_kwh: electricityKwh,
          location: gridRegion,
        };
      } else if (sourceType === "indirect_steam") {
        // We'll call the engine directly or simulate the API call structure
        // Assuming the backend /scope2 endpoint can handle generic process_type
        payload = {
          ...payload,
          source_type: "indirect_steam",
          amount: val,
          unit: unit,
          calc_inputs: {
            indirect_steam: {
              boiler_eff: parseFloat(String(boilerEff)),
              trans_loss: parseFloat(String(transLoss)),
            },
          },
        };
      } else if (sourceType === "cogen_allocation") {
        payload = {
          ...payload,
          source_type: "cogen_allocation",
          calc_inputs: {
            cogen_allocation: {
              total_emissions: val,
              heat_output: parseFloat(heatOutput),
              power_output: parseFloat(powerOutput),
              allocation_method: allocationMethod,
              ...(allocationMethod === "wri_efficiency" && heatEff !== "" ? { heat_efficiency: parseFloat(heatEff) } : {}),
              ...(allocationMethod === "wri_efficiency" && powerEff !== "" ? { power_efficiency: parseFloat(powerEff) } : {}),
            },
          },
        };
      }

      await api.post("/scope2", payload);
      toast.success(status === "Draft" ? "Entry saved as draft" : "Scope 2 entry added successfully");
      setAmount("");
      setCurrentPage(1);
      loadEntries();
    } catch (error) {
      console.error("Failed to add entry:", error);
      toast.error("Failed to add Scope 2 entry");
    } finally {
      setSubmitting(false);
    }
  };

  const handleInspect = (entry: Scope2GridEntry) => {
    const isElectricity = entry.source_type === "electricity";
    const amountVal = isElectricity ? entry.electricity_kwh : entry.heat_mmbtu || entry.co2e || 0;
    const unitVal = isElectricity ? "kWh" : entry.source_type === "indirect_steam" ? "MMBtu" : "tCO₂e";

    setInspectRecord({
      process_type: `Scope 2 - ${
        entry.source_type === "electricity"
          ? "Purchased Electricity"
          : entry.source_type === "indirect_steam"
          ? "Indirect Steam / Heat"
          : "CHP / Cogen Allocation"
      }`,
      fuel: entry.grid_region || entry.source_type || "Grid Electricity",
      amount: amountVal,
      unit: unitVal,
      emissions: {
        totalCo2e: entry.co2e || 0,
        co2: entry.co2e || 0,
        ch4: 0,
        n2o: 0,
      },
      factors: {
        co2: entry.emission_factor || 0,
        ch4: 0,
        n2o: 0,
      },
      method: entry.calculation_method || (isElectricity ? "Location-Based Grid EF" : "Energy Allocation"),
      steps: [
        {
          name: "Activity Normalization",
          desc: `Input: ${formatNumber(amountVal, 2)} ${unitVal} (${entry.grid_region || "Facility Level"})`,
        },
        {
          name: "Grid / Steam Emission Factor",
          desc: `Applied Factor: ${entry.emission_factor || 0} kg CO₂e / ${unitVal}`,
        },
        {
          name: "Emissions Calculation",
          desc: isElectricity
            ? `(${formatNumber(amountVal, 2)} kWh × ${entry.emission_factor}) ÷ 1,000 = ${formatNumber(entry.co2e, 3)} tCO₂e`
            : `Total Calculated Emissions = ${formatNumber(entry.co2e, 3)} tCO₂e`,
        },
      ],
    });
  };

  const handleImportSuccess = () => {
    loadEntries();
    toast.success("Records imported successfully!");
  };

  const handleDelete = (id: string | number) => {
    setDeleteTargetId(id);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    try {
      await api.delete(`/scope2/${deleteTargetId}`);
      toast.success("Entry deleted");
      setDeleteTargetId(null);
      loadEntries();
    } catch (error) {
      console.error("Failed to delete:", error);
      toast.error("Failed to delete entry");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDuplicate = (entry: Scope2GridEntry) => {
    if (entry.year !== undefined) setYear(entry.year);
    if (entry.month !== undefined) setMonth(entry.month);
    setFacilityId(entry.facility_id ? entry.facility_id.toString() : "");
    setGridRegion(entry.grid_region || "");
    const val = entry.electricity_kwh ?? entry.heat_mmbtu ?? entry.co2e;
    setAmount(val != null ? String(val) : "");
    setUnit(entry.source_type === "indirect_steam" ? "mmbtu" : "kWh");
    setSourceType(entry.source_type || "electricity");
    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const getFacilityOptions = () => [
    { value: "", label: "Select Region..." },
    ...facilities.map((f) => ({
      value: f.id.toString(),
      label: f.name,
      subLabel: f.field,
    })),
  ];

  const getGridOptions = () => [
    { value: "", label: "Select Grid Region..." },
    ...gridFactors.map((f) => ({ value: f.region, label: f.region })),
  ];

  return (
    <div className="scope-form">
      <Scope2FormNewElectricityEntry
        activity={activity}
        allocationMethod={allocationMethod}
        amount={amount}
        boilerEff={boilerEff}
        division={division}
        facilityId={facilityId}
        field={field}
        getFacilityOptions={getFacilityOptions}
        getGridOptions={getGridOptions}
        gridRegion={gridRegion}
        handleAddEntry={handleAddEntry}
        handleSourceTypeChange={handleSourceTypeChange}
        heatEff={heatEff}
        heatOutput={heatOutput}
        month={month}
        powerEff={powerEff}
        powerOutput={powerOutput}
        setAllocationMethod={setAllocationMethod}
        setAmount={setAmount}
        setBoilerEff={setBoilerEff}
        setFacilityId={setFacilityId}
        setGridRegion={setGridRegion}
        setHeatEff={setHeatEff}
        setHeatOutput={setHeatOutput}
        setMonth={setMonth}
        setPowerEff={setPowerEff}
        setPowerOutput={setPowerOutput}
        setTransLoss={setTransLoss}
        setUnit={setUnit}
        setYear={setYear}
        sourceType={sourceType}
        submitting={submitting}
        transLoss={transLoss}
        unit={unit}
        unitOptions={unitOptions}
        year={year}
      />

      {importModal.isOpen && (
        <ColumnMappingWizard
          onClose={() => setImportModal({ ...importModal, isOpen: false })}
          onUploadSuccess={handleImportSuccess}
          type={importModal.type}
        />
      )}

      <Scope2FormCalculatorGridContainer
        currentPage={currentPage}
        entries={entries}
        facilities={facilities}
        handleDelete={handleDelete}
        handleDuplicate={handleDuplicate}
        handleInspect={handleInspect}
        loadEntries={loadEntries}
        loadError={loadError}
        loading={loading}
        setCurrentPage={setCurrentPage}
        setShowWizard={setShowWizard}
        totalPages={totalPages}
      />

      {showWizard && (
        <Scope2ImportWizard
          onClose={() => setShowWizard(false)}
          onUploadSuccess={() => {
            setShowWizard(false);
            loadEntries();
            toast.success("Bulk import completed successfully");
          }}
        />
      )}

      {inspectRecord && (
        <CalculationDetails
          calculation={inspectRecord}
          onClose={() => setInspectRecord(null)}
        />
      )}

      <ConfirmModal
        isOpen={!!deleteTargetId}
        title="Delete Scope 2 Entry"
        message="Are you sure you want to delete this Scope 2 entry? This calculation record will be permanently removed."
        confirmLabel="Delete Record"
        confirmVariant="danger"
        loading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />
    </div>
  );
};

export default Scope2Form;
