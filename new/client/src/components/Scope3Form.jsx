import React, { useState, useEffect } from "react";
import { activateOnKey } from "../utils/a11yKeys";
import { CATEGORY_ACTIVITIES } from "../utils/scope3Factors";
import api from "../api";
import CustomDropdown from "./CustomDropdown";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { formatNumber, formatEmission } from "../utils/formatters";
import ColumnMappingWizard from "./ColumnMappingWizard";
import Scope3ImportWizard from "./Scope3ImportWizard";
import { Upload, Trash2, Eye } from "lucide-react";
import CalculationDetails from "./CalculationDetails";
import ConfirmModal from "./ConfirmModal";
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
    day: { day: 1, week: 5, month: 20, year: 240 },
  };

  const [facilities, setFacilities] = useState([]);
  const [entries, setEntries] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loadError, setLoadError] = useState(false);
  const [importModal, setImportModal] = useState({
    isOpen: false,
    type: "activity_scope3",
  });
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
    15: { name: "Investments", type: "downstream" },
  };


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
        status: status,
      };

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
        n2o: 0,
      },
      factors: {
        co2: entry.emission_factor || 0,
        ch4: 0,
        n2o: 0,
      },
      method: entry.calculation_method || "Activity Data × Emission Factor",
      steps: [
        {
          name: "Activity Normalization",
          desc: `Recorded activity quantity: ${entry.activity_data || entry.volume || 0} ${entry.unit}`,
        },
        {
          name: "Emission Factor Application",
          desc: `Applied factor: ${entry.emission_factor} kg CO₂e / ${entry.unit}`,
        },
        {
          name: "CO₂e Calculation",
          desc: `(${entry.activity_data || entry.volume || 0} × ${entry.emission_factor}) ÷ 1,000 = ${formatNumber(entry.co2e || entry.emissions_tco2e, 3)} tCO₂e`,
        },
      ],
    });
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
      subLabel: f.field,
    })),
  ];

  return (
    <div className="scope-form">
      <div className="calc-panel">

        {/* EEIO Quick Spend Calculator */}
        <div style={{ marginTop: "20px", marginBottom: "10px", padding: "16px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
          <div role="button" tabIndex={0} onKeyDown={activateOnKey} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }} onClick={() => setShowEeioCalc(!showEeioCalc)}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "1.2rem" }}>💰</span>
              <strong style={{ color: "#334155" }}>EEIO Quick Spend Calculator</strong>
              <span style={{ fontSize: "0.8rem", color: "#64748b", marginLeft: "10px" }}>Convert financial spend to CO₂e using NAICS factors</span>
            </div>
            <span>{showEeioCalc ? "▲" : "▼"}</span>
          </div>
          
          {showEeioCalc && (
            <div style={{ marginTop: "16px", display: "flex", gap: "16px", alignItems: "flex-end" }}>
              <div className="input-group" style={{ flex: 1 }}>
                <label>NAICS Code (6 digits)</label>
                <input
                  type="text"
                  className="mole-input"
                  placeholder="e.g. 331110 or steel"
                  value={eeioNaics}
                  list="eeio-naics-options"
                  onChange={(e) => {
                    setEeioNaics(e.target.value);
                    searchNaics(e.target.value);
                  }}
                />
                <datalist id="eeio-naics-options">
                  {naicsOptions.map((o) => (
                    <option key={o.naics} value={o.naics}>{`${o.name} (${o.kg_co2e_per_usd} kg CO2e/USD)`}</option>
                  ))}
                </datalist>
              </div>
              <div className="input-group" style={{ flex: 1 }}>
                <label>Spend Amount (USD)</label>
                <input
                  type="number"
                  className="mole-input"
                  placeholder="0.00"
                  value={eeioSpend}
                  onChange={(e) => setEeioSpend(e.target.value)}
                />
              </div>
              <button 
                className="action-btn" 
                style={{ height: "38px", padding: "0 16px", background: "#3b82f6", color: "white" }}
                onClick={handleCalculateEeio}
              >
                Calculate & Auto-fill
              </button>
            </div>
          )}
          {eeioResult && showEeioCalc && (
            <div style={{ marginTop: "12px", padding: "12px", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.85rem", color: "#1e3a8a" }}>
                <strong>Industry:</strong> {eeioResult.industry_name} <br/>
                <strong>Factor:</strong> {eeioResult.emission_factor} {eeioResult.ef_unit} <br/>
                <strong>Estimated Emissions:</strong> <span style={{ fontSize: "1.1rem", fontWeight: "bold" }}>{eeioResult.co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span> tCO₂e
              </div>
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ margin: 0 }}>New Scope 3 Entry</h3>
          <div style={{ textAlign: "right" }}>
            <span
              style={{ color: "#8b5cf6", fontWeight: 600, fontSize: "0.9rem" }}
            >
              Scope 3: Other Indirect
            </span>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
            marginBottom: "20px",
          }}
        >
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
                  {new Date(0, i).toLocaleString("default", { month: "long" })}
                </option>
              ))}
            </select>
          </div>
          <div className="input-group">
            <label>Facility</label>
            <CustomDropdown
              options={getFacilityOptions()}
              value={facilityId || ""}
              onChange={setFacilityId}
            />
          </div>
          <div className="input-group">
            <label>Category</label>
            <CustomDropdown
              options={getCategoryOptions()}
              value={category}
              onChange={setCategory}
            />
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
          }}
        >
          <div className="input-group">
            <label>Activity Type</label>
            <CustomDropdown
              options={getActivityOptions()}
              value={activityType}
              onChange={setActivityType}
            />
          </div>
          <div className="input-group">
            <label>Amount</label>
            <input
              type="number"
              className="mole-input"
              value={amount || ""}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              step="0.01"
            />
          </div>
          <div className="input-group">
            <label>Unit</label>
            {UNIT_MULTIPLIERS[baseUnit] ? (
              <select
                className="component-select"
                value={unit}
                onChange={(e) => handleUnitChange(e.target.value)}
              >
                {Object.keys(UNIT_MULTIPLIERS[baseUnit]).map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                className="mole-input"
                value={unit}
                readOnly
                style={{
                  background: "rgba(255,255,255,0.03)",
                  cursor: "not-allowed",
                }}
              />
            )}
          </div>
          <div className="input-group">
            <label>EF (kg CO₂e/unit)</label>
            <input
              type="number"
              className="mole-input"
              value={emissionFactor || ""}
              onChange={(e) => setEmissionFactor(e.target.value)}
              step="0.01"
            />
          </div>
        </div>


        <div
          style={{
            display: "flex",
            gap: "12px",
            marginTop: "30px",
            justifyContent: "flex-end",
          }}
        >
          <button
            className="action-btn secondary"
            disabled={submitting}
            onClick={() => handleAddEntry("Draft")}
            style={{
              padding: "12px 20px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Saving..." : "Save as Draft (Maker Mode)"}
          </button>
          <button
            className="btn-add-activity"
            disabled={submitting}
            onClick={() => handleAddEntry("Verified")}
            style={{
              flex: 1.5,
              padding: "12px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Processing..." : "+ Calculate & Submit for Review"}
          </button>
        </div>

        {importModal.isOpen && (
          <ColumnMappingWizard
            onClose={() => setImportModal({ ...importModal, isOpen: false })}
            onUploadSuccess={handleImportSuccess}
            type={importModal.type}
          />
        )}
      </div>

      <div className="calculator-grid-container" style={{ marginTop: "30px" }}>
        <div 
          className="table-controls"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "15px"
          }}
        >
          <strong style={{ fontSize: "1rem", color: "#374151" }}>Documented Scope 3 Emissions</strong>
          <button
            className="action-btn secondary"
            onClick={() => setShowWizard(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
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
                <th>Facility</th>
                <th>Category</th>
                <th>Activity/Product</th>
                <th>Volume</th>
                <th>EF (kg/unit)</th>
                <th>Total (tCO₂e)</th>
                <th
                  title="Standard Combined Uncertainty (1σ)"
                  style={{ cursor: "help" }}
                >
                  CO₂e 1σ (±%)
                </th>
                <th
                  title="Expanded Uncertainty (95% Confidence Interval)"
                  style={{ cursor: "help" }}
                >
                  CO₂e 95% CI (±%)
                </th>
                <th style={{ textAlign: "center" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loadError ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: "center", color: "var(--danger, #dc2626)" }}>
                    Could not load the records.{" "}
                    <button type="button" className="btn-ghost" onClick={loadEntries}>Retry</button>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td
                    colSpan="10"
                    style={{
                      textAlign: "center",
                      color: "var(--text-secondary)",
                    }}
                  >
                    No entries yet
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.month ? `${entry.year}-${String(entry.month).padStart(2, "0")}` : entry.year}</td>
                    <td>
                      {facilities.find((f) => f.id === entry.facility_id)
                        ?.name || "Unknown"}
                    </td>
                    <td>{entry.category}</td>
                    <td>{entry.sub_category || entry.product_type}</td>
                    <td>
                      {formatNumber(entry.activity_data || entry.volume, 2)}{" "}
                      {entry.unit}
                    </td>
                    <td>
                      {/* kg CO2e per activity unit; a supplier-reported total has no factor */}
                      {Number(entry.emission_factor) > 0 ? formatEmission(entry.emission_factor, 4) : "—"}
                    </td>
                    <td style={{ color: "#8b5cf6", fontWeight: 600 }}>
                      {formatEmission(entry.co2e || entry.emissions_tco2e, 3)}
                    </td>
                    <td style={{ color: "#6b7280", fontSize: "0.85rem" }}>
                      {entry.uncertainty != null
                        ? `${formatNumber(entry.uncertainty * 100, 1)}%`
                        : "—"}
                    </td>
                    <td style={{ color: "#6b7280", fontSize: "0.85rem" }}>
                      {entry.uncertainty != null
                        ? `${formatNumber(entry.uncertainty * UNCERTAINTY_COVERAGE_K * 100, 1)}%`
                        : "—"}
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
                    <td style={{ textAlign: "center", whiteSpace: "nowrap" }}>
                      <button
                        className="icon-button"
                        onClick={() => handleInspect(entry)}
                        style={{ color: "#3b82f6", marginRight: "8px" }}
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
                ))
              )}
            </tbody>
            <tfoot>
              <tr style={{ backgroundColor: "#f9fafb", fontWeight: "bold" }}>
                <td
                  colSpan="6"
                  style={{ textAlign: "right", paddingRight: "15px" }}
                >
                  Total (Page):
                </td>
                <td style={{ color: "#8b5cf6" }}>
                  {formatNumber(
                    entries.reduce(
                      (sum, e) => sum + (e.co2e || e.emissions_tco2e || 0),
                      0,
                    ),
                    3,
                  )}
                </td>
                <td></td>
                <td></td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
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
