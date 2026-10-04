import React, { useState, useEffect } from "react";
import { NativeSelect } from "../ui/NativeSelect";
import { CATEGORY_ACTIVITIES } from "../utils/scope3Factors";
import api from "../api";
import CustomDropdown from "./CustomDropdown";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { formatNumber } from "../utils/formatters";
import ColumnMappingWizard from "./ColumnMappingWizard";
import Scope3ImportWizard from "./Scope3ImportWizard";
import { Upload, Trash2, Eye } from "lucide-react";
import CalculationDetails from "./CalculationDetails";
import ConfirmModal from "./ConfirmModal";
import Scope3FormNewScope3 from "./scope3-form/Scope3FormNewScope3";
import Scope3FormCalculatorGridContainer from "./scope3-form/Scope3FormCalculatorGridContainer";
import "./ScopeTables.css";
import { UNCERTAINTY_COVERAGE_K } from "../constants";

const Scope3Form = () => {
  const { user } = useAuth();
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [facilityId, setFacilityId] = useState("");
  const [category, setCategory] = useState("11");
  const [activityType, setActivityType] = useState("");
  const [amount, setAmount] = useState("");
  const [unit, setUnit] = useState("");
  const [emissionFactor, setEmissionFactor] = useState("");
  const [baseUnit, setBaseUnit] = useState("");
  const [baseFactor, setBaseFactor] = useState(0);

  // Result and Inspect Modals
  const [inspectRecord, setInspectRecord] = useState(null);

  // EEIO Quick Calculator State
  const [showEeioCalc, setShowEeioCalc] = useState(false);
  const [eeioNaics, setEeioNaics] = useState("");
  const [eeioSpend, setEeioSpend] = useState("");
  const [eeioResult, setEeioResult] = useState(null);
  const [naicsOptions, setNaicsOptions] = useState([]);
  // six-digit NAICS codes of the EPA supply chain factor dataset matching the typed code or title
  const searchNaics = async (q) => {
    if (!q || q.trim().length < 2) return setNaicsOptions([]);
    try {
      const res = await api.get("/scope3/eeio-factors", { params: { q } });
      setNaicsOptions(Array.isArray(res.data) ? res.data : []);
    } catch {
      setNaicsOptions([]);
    }
  };
  
  const handleCalculateEeio = async () => {
    if (!eeioNaics || !eeioSpend) return;
    try {
      const res = await api.post("/scope3/eeio-calculate", {
        naics_code: eeioNaics,
        spend_usd: eeioSpend
      });
      setEeioResult(res.data);
      // Auto-fill the form
      setCategory("1");
      setActivityType(`Spend: ${res.data.industry_name}`);
      setAmount(eeioSpend);
      setUnit("USD");
      // res.data.emission_factor is per $1000 spend; convert to per $1 spend to prevent 1000x overstatement
      const normalizedEf = (parseFloat(res.data.emission_factor) / 1000.0).toFixed(6);
      setEmissionFactor(normalizedEf);
      setBaseFactor(parseFloat(normalizedEf));
      setBaseUnit("USD");
    } catch (err) {
      toast.show(err?.response?.data?.error || "Error calculating EEIO emissions", "error");
    }
  };

  const UNIT_MULTIPLIERS = {
    kg: { kg: 1, tonne: 1000, ton: 907.185, lb: 0.453592 },
    bbl: { bbl: 1, gal: 1 / 42, m3: 6.2898, L: 0.0062898 },
    gal: { gal: 1, bbl: 42, L: 0.264172, m3: 264.172 },
    mcf: { mcf: 1, scf: 0.001, m3: 0.0353147 },
    kWh: { kWh: 1, MWh: 1000 },
    "ton-km": { "ton-km": 1, "ton-mile": 1.45997 },
    "passenger-km": { "passenger-km": 1, "passenger-mile": 1.60934 },
    km: { km: 1, mile: 1.60934 },
    "sq ft": { "sq ft": 1, "sq m": 10.7639 },
    USD: { USD: 1, EUR: 1.1, DZD: 0.0074 },
    day: { day: 1, week: 5, month: 20, year: 240 } };

  const [facilities, setFacilities] = useState([]);
  const [entries, setEntries] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loadError, setLoadError] = useState(false);
  const [importModal, setImportModal] = useState({
    isOpen: false,
    type: "activity_scope3" });
  const RECORDS_PER_PAGE = 10;

  const SCOPE3_CATEGORIES = {
    1: { name: "Purchased Goods & Services", type: "upstream" },
    2: { name: "Capital Goods", type: "upstream" },
    3: { name: "Fuel & Energy-Related", type: "upstream" },
    4: { name: "Upstream Transportation", type: "upstream" },
    5: { name: "Waste Generated", type: "upstream" },
    6: { name: "Business Travel", type: "upstream" },
    7: { name: "Employee Commuting", type: "upstream" },
    8: { name: "Upstream Leased Assets", type: "upstream" },
    9: { name: "Downstream Transportation", type: "downstream" },
    10: { name: "Processing of Sold Products", type: "downstream" },
    11: { name: "Use of Sold Products", type: "downstream" },
    12: { name: "End-of-Life Treatment", type: "downstream" },
    13: { name: "Downstream Leased Assets", type: "downstream" },
    14: { name: "Franchises", type: "downstream" },
    15: { name: "Investments", type: "downstream" } };


  useEffect(() => {
    loadFacilities();
    loadEntries();
  }, []);

  useEffect(() => {
    loadEntries();
  }, [currentPage]);

  useEffect(() => {
    const activities = CATEGORY_ACTIVITIES[category];
    if (activities && activities.length > 0) {
      setActivityType(activities[0].value);
      setBaseUnit(activities[0].unit);
      setBaseFactor(activities[0].factor);
      setUnit(activities[0].unit);
      // factor null: no published default, the user enters the supplier / site factor
      setEmissionFactor(activities[0].factor == null ? "" : activities[0].factor.toString());
    } else {
      setActivityType("");
      setUnit("");
      setEmissionFactor("");
    }
  }, [category]);

  useEffect(() => {
    const activities = CATEGORY_ACTIVITIES[category];
    if (activities) {
      const activity = activities.find((a) => a.value === activityType);
      if (activity) {
        setBaseUnit(activity.unit);
        setBaseFactor(activity.factor);
        setUnit(activity.unit);
        setEmissionFactor(activity.factor == null ? "" : activity.factor.toString());
      }
    }
  }, [activityType, category]);

  const handleUnitChange = (newUnit) => {
    setUnit(newUnit);
    if (baseFactor != null && UNIT_MULTIPLIERS[baseUnit] && UNIT_MULTIPLIERS[baseUnit][newUnit]) {
      const multiplier = UNIT_MULTIPLIERS[baseUnit][newUnit];
      const newFactor = baseFactor * multiplier;
      // Round to 5 decimal places to avoid floating point weirdness
      setEmissionFactor(parseFloat(newFactor.toFixed(5)).toString());
    }
  };

  const loadFacilities = async () => {
    try {
      const res = await api.get("/facilities");
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

  const loadEntries = async () => {
    try {
      // one page from the server (the whole list used to be downloaded on every page change)
      const res = await api.get("/scope3", {
        params: { limit: RECORDS_PER_PAGE, offset: (currentPage - 1) * RECORDS_PER_PAGE } });
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      const total = Array.isArray(res.data) ? data.length : Number(res.data?.total) || 0;
      setEntries(data);
      setTotalPages(Math.max(1, Math.ceil(total / RECORDS_PER_PAGE)));
      setLoadError(false);
    } catch (error) {
      console.error("Failed to load entries:", error);
      setLoadError(true);
      toast.error("Failed to load Scope 3 data");
    }
  };

  const handleAddEntry = async (status = "Verified") => {
    if (
      !year ||
      !month ||
      !facilityId ||
      !category ||
      !activityType ||
      !amount ||
      !emissionFactor
    ) {
      toast.warning("Please fill in all required fields");
      return;
    }

    try {
      setSubmitting(true);
      const amt = parseFloat(amount);
      const ef = parseFloat(emissionFactor);
      const totalEmissions = (amt * ef) / 1000;

      const payload = {
        year: parseInt(year),
        month: parseInt(month),
        facility_id: parseInt(facilityId),
        category: parseInt(category), // or string
        sub_category: activityType,
        activity_data: amt,
        unit: unit,
        emission_factor: ef,
        co2e: totalEmissions,
        notes: SCOPE3_CATEGORIES[category].name,
        status: status };

      await api.post("/scope3", payload);
      toast.success(
        status === "Draft"
          ? "Entry saved as draft"
          : "Scope 3 entry added successfully",
      );
      setAmount("");
      setCurrentPage(1);
      loadEntries();
    } catch (error) {
      console.error("Failed to add entry:", error);
      toast.error("Failed to add entry");
    } finally {
      setSubmitting(false);
    }
  };

  const handleInspect = (entry) => {
    setInspectRecord({
      process_type: `Scope 3 - Category ${entry.category}`,
      fuel: entry.sub_category || entry.product_type || "N/A",
      amount: entry.activity_data || entry.volume || 0,
      unit: entry.unit || "unit",
      emissions: {
        totalCo2e: entry.co2e || entry.emissions_tco2e || 0,
        co2: entry.co2e || entry.emissions_tco2e || 0,
        ch4: 0,
        n2o: 0 },
      factors: {
        co2: entry.emission_factor || 0,
        ch4: 0,
        n2o: 0 },
      method: entry.calculation_method || "Activity Data × Emission Factor",
      steps: [
        {
          name: "Activity Normalization",
          desc: `Recorded activity quantity: ${entry.activity_data || entry.volume || 0} ${entry.unit}` },
        {
          name: "Emission Factor Application",
          desc: `Applied factor: ${entry.emission_factor} kg CO₂e / ${entry.unit}` },
        {
          name: "CO₂e Calculation",
          desc: `(${entry.activity_data || entry.volume || 0} × ${entry.emission_factor}) ÷ 1,000 = ${formatNumber(entry.co2e || entry.emissions_tco2e, 3)} tCO₂e` },
      ] });
  };

  const handleImportSuccess = () => {
    loadEntries();
    toast.success("Records imported successfully!");
  };

  const handleDelete = (id) => {
    setDeleteTargetId(id);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    setIsDeleting(true);
    try {
      await api.delete(`/scope3/${deleteTargetId}`);
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

  const getCategoryOptions = () => [
    { value: "", label: "Select Category...", disabled: true },
    { value: "1", label: "Cat 1: Purchased Goods & Services" },
    { value: "2", label: "Cat 2: Capital Goods" },
    { value: "3", label: "Cat 3: Fuel & Energy-Related" },
    { value: "4", label: "Cat 4: Upstream Transportation" },
    { value: "5", label: "Cat 5: Waste Generated" },
    { value: "6", label: "Cat 6: Business Travel" },
    { value: "7", label: "Cat 7: Employee Commuting" },
    { value: "8", label: "Cat 8: Upstream Leased Assets" },
    { value: "9", label: "Cat 9: Downstream Transportation" },
    { value: "10", label: "Cat 10: Processing of Sold Products" },
    { value: "11", label: "Cat 11: Use of Sold Products" },
    { value: "12", label: "Cat 12: End-of-Life Treatment" },
    { value: "13", label: "Cat 13: Downstream Leased Assets" },
    { value: "14", label: "Cat 14: Franchises" },
    { value: "15", label: "Cat 15: Investments" },
  ];

  const getActivityOptions = () => {
    const activities = CATEGORY_ACTIVITIES[category];
    if (!activities)
      return [{ value: "", label: "Select category first...", disabled: true }];
    return activities.map((a) => ({ value: a.value, label: a.value }));
  };

  const getFacilityOptions = () => [
    { value: "", label: "Select Facility..." },
    ...facilities.map((f) => ({
      value: f.id.toString(),
      label: f.name,
      subLabel: f.field })),
  ];

  return (
    <div className="scope-form">
      <Scope3FormNewScope3
        UNIT_MULTIPLIERS={UNIT_MULTIPLIERS}
        activityType={activityType}
        amount={amount}
        baseUnit={baseUnit}
        category={category}
        eeioNaics={eeioNaics}
        eeioResult={eeioResult}
        eeioSpend={eeioSpend}
        emissionFactor={emissionFactor}
        facilityId={facilityId}
        getActivityOptions={getActivityOptions}
        getCategoryOptions={getCategoryOptions}
        getFacilityOptions={getFacilityOptions}
        handleAddEntry={handleAddEntry}
        handleCalculateEeio={handleCalculateEeio}
        handleImportSuccess={handleImportSuccess}
        handleUnitChange={handleUnitChange}
        importModal={importModal}
        month={month}
        naicsOptions={naicsOptions}
        searchNaics={searchNaics}
        setActivityType={setActivityType}
        setAmount={setAmount}
        setCategory={setCategory}
        setEeioNaics={setEeioNaics}
        setEeioSpend={setEeioSpend}
        setEmissionFactor={setEmissionFactor}
        setFacilityId={setFacilityId}
        setImportModal={setImportModal}
        setMonth={setMonth}
        setShowEeioCalc={setShowEeioCalc}
        setYear={setYear}
        showEeioCalc={showEeioCalc}
        submitting={submitting}
        unit={unit}
        year={year}
      />

      <Scope3FormCalculatorGridContainer
        currentPage={currentPage}
        entries={entries}
        facilities={facilities}
        handleDelete={handleDelete}
        handleInspect={handleInspect}
        loadEntries={loadEntries}
        loadError={loadError}
        setCurrentPage={setCurrentPage}
        setShowWizard={setShowWizard}
        totalPages={totalPages}
      />
      
      {showWizard && (
        <Scope3ImportWizard
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
        title="Delete Scope 3 Entry"
        message="Are you sure you want to delete this Scope 3 entry? This calculation record will be permanently removed."
        confirmLabel="Delete Record"
        confirmVariant="danger"
        loading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />
    </div>
  );
};

export default Scope3Form;
