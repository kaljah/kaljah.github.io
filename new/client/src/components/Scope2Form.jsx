import React, { useState, useEffect } from "react";
import api from "../api";
import CustomDropdown from "./CustomDropdown";
import { useToast } from "./Toast";
import LoadingSpinner from "./LoadingSpinner";
import { formatNumber } from "../utils/formatters";
import ColumnMappingWizard from "./ColumnMappingWizard";
import Scope2ImportWizard from "./Scope2ImportWizard";
import { Upload, Copy, Trash2 } from "lucide-react";
import "./ScopeTables.css";

const Scope2Form = () => {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [showWizard, setShowWizard] = useState(false);

  // Identity State (Hoisted to match Scope 1)
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [facilityId, setFacilityId] = useState("");
  const [activity, setActivity] = useState("");
  const [division, setDivision] = useState("");
  const [field, setField] = useState("");

  // Process/Source State
  const [gridRegion, setGridRegion] = useState("");
  const [amount, setAmount] = useState("");
  const [unit, setUnit] = useState("kWh");
  const [groupName, setGroupName] = useState("");
  const [equipmentId, setEquipmentId] = useState("");
  const [sourceType, setSourceType] = useState("electricity");

  // Section 8 specific state
  const [boilerEff, setBoilerEff] = useState(0.8);
  const [transLoss, setTransLoss] = useState(0.0);
  const [heatOutput, setHeatOutput] = useState("");
  const [powerOutput, setPowerOutput] = useState("");
  const [allocationMethod, setAllocationMethod] = useState("wri_efficiency");
  const [cogenResults, setCogenResults] = useState(null);

  const [facilities, setFacilities] = useState([]);
  const [gridFactors, setGridFactors] = useState([]);
  const [entries, setEntries] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [importModal, setImportModal] = useState({
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
      const fac = facilities.find(
        (f) => f.id.toString() === facilityId.toString(),
      );
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
    } catch (error) {
      console.error("Failed to load regions:", error);
      toast.error("Failed to load regions");
    }
  };

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
      const res = await api.get("/scope2");
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      const sorted = data.sort((a, b) => b.id - a.id);
      const start = (currentPage - 1) * RECORDS_PER_PAGE;
      setEntries(sorted.slice(start, start + RECORDS_PER_PAGE));
      setTotalPages(Math.ceil(sorted.length / RECORDS_PER_PAGE));
    } catch (error) {
      console.error("Failed to load entries:", error);
      toast.error("Failed to load Scope 2 data");
    } finally {
      setLoading(false);
    }
  };

  const handleAddEntry = async (status = "Verified") => {
    if (
      !year ||
      !month ||
      !facilityId ||
      (sourceType === "electricity" && !gridRegion) ||
      !amount
    ) {
      toast.warning("Please fill in all required fields");
      return;
    }

    try {
      const val = parseFloat(amount);
      if (val <= 0 && sourceType !== "cogen_allocation") {
        toast.warning("Please enter a valid usage amount");
        return;
      }

      let payload = {
        year: parseInt(year),
        month: parseInt(month),
        facility_id: parseInt(facilityId),
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

        const factorObj = gridFactors.find((f) => f.region === gridRegion);
        const ef = factorObj ? factorObj.factor : 0;
        const totalEmissions = (electricityKwh * ef) / 1000;

        payload = {
          ...payload,
          grid_region: gridRegion,
          source_type: "electricity",
          electricity_kwh: electricityKwh,
          emission_factor: ef,
          co2e: totalEmissions,
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
              boiler_eff: parseFloat(boilerEff),
              trans_loss: parseFloat(transLoss),
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
            },
          },
        };
      }

      await api.post("/scope2", payload);
      toast.success(
        status === "Draft"
          ? "Entry saved as draft"
          : "Scope 2 entry added successfully",
      );
      setAmount("");
      setCurrentPage(1);
      loadEntries();
    } catch (error) {
      console.error("Failed to add entry:", error);
      toast.error("Failed to add Scope 2 entry");
    }
  };

  const handleImportSuccess = () => {
    loadEntries();
    toast.success("Records imported successfully!");
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this entry?")) return;
    try {
      await api.delete(`/scope2/${id}`);
      toast.success("Entry deleted");
      loadEntries();
    } catch (error) {
      console.error("Failed to delete:", error);
      toast.error("Failed to delete entry");
    }
  };

  const handleDuplicate = (entry) => {
    setYear(entry.year);
    setMonth(entry.month);
    setFacilityId(entry.facility_id.toString());
    setGridRegion(entry.grid_region);
    setAmount(entry.electricity_kwh.toString());
    setUnit("kWh");
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
          New Electricity Entry
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
                value={activity || ""}
                disabled
              />
            </div>
            <div className="input-group">
              <label>Division</label>
              <input
                type="text"
                className="mole-input readonly"
                value={division || ""}
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
                value={field || ""}
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
          </div>
        </div>

        {/* 2. GRID & SOURCE DETAILS */}
        <div style={{ marginBottom: "30px" }}>
          <h4 className="section-title">2. GRID &amp; SOURCE DETAILS</h4>
          <div className="form-grid-2">
            <div className="input-group">
              <label>Source Type</label>
              <CustomDropdown
                options={[
                  {
                    value: "electricity",
                    label: "Purchased Electricity (Grid)",
                  },
                  { value: "indirect_steam", label: "Indirect Steam / Heat" },
                  {
                    value: "cogen_allocation",
                    label: "CHP / Cogeneration Allocation",
                  },
                ]}
                value={sourceType}
                onChange={setSourceType}
              />
            </div>
            {sourceType === "electricity" && (
              <div className="input-group">
                <label>Grid Region</label>
                <CustomDropdown
                  options={getGridOptions()}
                  value={gridRegion}
                  onChange={setGridRegion}
                  placeholder="Select Grid..."
                />
              </div>
            )}
            {sourceType === "indirect_steam" && (
              <div className="form-grid-2" style={{ gridColumn: "span 2" }}>
                <div className="input-group">
                  <label>Boiler Efficiency (0.0 - 1.0)</label>
                  <input
                    type="number"
                    className="mole-input"
                    value={boilerEff}
                    onChange={(e) => setBoilerEff(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label>Transmission Loss (0.0 - 1.0)</label>
                  <input
                    type="number"
                    className="mole-input"
                    value={transLoss}
                    onChange={(e) => setTransLoss(e.target.value)}
                  />
                </div>
              </div>
            )}
            {sourceType === "cogen_allocation" && (
              <div className="form-grid-3" style={{ gridColumn: "span 2" }}>
                <div className="input-group">
                  <label>Heat Output (MMBtu)</label>
                  <input
                    type="number"
                    className="mole-input"
                    value={heatOutput}
                    onChange={(e) => setHeatOutput(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label>Power Output (MWh)</label>
                  <input
                    type="number"
                    className="mole-input"
                    value={powerOutput}
                    onChange={(e) => setPowerOutput(e.target.value)}
                  />
                </div>
                <div className="input-group">
                  <label>Method</label>
                  <select
                    className="component-select"
                    value={allocationMethod}
                    onChange={(e) => setAllocationMethod(e.target.value)}
                  >
                    <option value="wri_efficiency">WRI Efficiency</option>
                    <option value="energy_content">Energy Content</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 3. ACTIVITY DATA */}
        <div style={{ marginBottom: "10px" }}>
          <h4 className="section-title">3. ACTIVITY DATA</h4>
          <div className="form-grid-3">
            <div className="input-group">
              <label>
                {sourceType === "cogen_allocation"
                  ? "Total Facility Emissions (tCO2e)"
                  : "Usage Amount"}
              </label>
              <input
                type="number"
                className="mole-input"
                value={amount || ""}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <div className="input-group">
              <label>Unit</label>
              <CustomDropdown
                options={
                  sourceType === "electricity"
                    ? [
                        { value: "kWh", label: "kWh" },
                        { value: "MWh", label: "MWh" },
                        { value: "GWh", label: "GWh" },
                      ]
                    : sourceType === "indirect_steam"
                      ? [
                          { value: "btu", label: "Btu" },
                          { value: "mmbtu", label: "MMBtu" },
                          { value: "mj", label: "MJ" },
                        ]
                      : [{ value: "tonnes", label: "Tonnes CO2e" }]
                }
                value={unit || "kWh"}
                onChange={setUnit}
              />
            </div>
            <div className="input-group">
              <label style={{ visibility: "hidden" }}>Align</label>
              <button
                className="btn-add-activity"
                onClick={() => handleAddEntry("Verified")}
                style={{
                  width: "100%",
                  height: "38px",
                  borderRadius: "6px",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                Calculate
              </button>
            </div>
          </div>
        </div>
      </div>

      {importModal.isOpen && (
        <ColumnMappingWizard
          onClose={() => setImportModal({ ...importModal, isOpen: false })}
          onUploadSuccess={handleImportSuccess}
          type={importModal.type}
        />
      )}

      <div className="calculator-grid-container" style={{ marginTop: "30px" }}>
        <div
          className="table-controls"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "15px",
          }}
        >
          <strong style={{ fontSize: "1rem", color: "#374151" }}>
            Recent Scope 2 (Electricity) Entries
          </strong>
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
        <div
          className="table-scroll-container"
          style={{ maxHeight: "600px", overflowY: "auto" }}
        >
          <table className="excel-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Facility</th>
                <th>Source Type</th>
                <th>Grid / Region</th>
                <th>Division / Field</th>
                <th>Consumption / Input</th>
                <th>EF</th>
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
              {loading ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center" }}>
                    <LoadingSpinner />
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td
                    colSpan="11"
                    style={{
                      textAlign: "center",
                      padding: "40px",
                      color: "#9ca3af",
                    }}
                  >
                    No entries found
                  </td>
                </tr>
              ) : (
                entries.map((entry) => {
                  const srcLabel =
                    {
                      electricity: "Grid Electricity",
                      indirect_steam: "Indirect Steam / Heat",
                      cogen_allocation: "CHP / Cogen Allocation",
                    }[entry.source_type] || entry.source_type;

                  let consumptionDisplay = "-";
                  if (entry.source_type === "electricity") {
                    consumptionDisplay = `${formatNumber(entry.electricity_kwh, 0)} kWh`;
                  } else if (entry.source_type === "indirect_steam") {
                    consumptionDisplay = entry.heat_mmbtu
                      ? `${formatNumber(entry.heat_mmbtu, 2)} MMBtu`
                      : "-";
                  } else if (entry.source_type === "cogen_allocation") {
                    consumptionDisplay = `${formatNumber(entry.co2e, 3)} tCO₂e allocated`;
                  }

                  const efDisplay = entry.emission_factor
                    ? formatNumber(entry.emission_factor, 4)
                    : "—";

                  return (
                    <tr key={entry.id}>
                      <td>{entry.year}</td>
                      <td style={{ fontWeight: 500 }}>
                        {facilities.find((f) => f.id === entry.facility_id)
                          ?.name || "Unknown"}
                      </td>
                      <td
                        style={{
                          fontSize: "0.8rem",
                          color:
                            entry.source_type === "electricity"
                              ? "#10b981"
                              : entry.source_type === "indirect_steam"
                                ? "#f59e0b"
                                : "#8b5cf6",
                          fontWeight: 600,
                        }}
                      >
                        {srcLabel}
                      </td>
                      <td>{entry.grid_region || "—"}</td>
                      <td style={{ fontSize: "0.8rem", color: "#6b7280" }}>
                        {entry.division} / {entry.field}
                      </td>
                      <td>{consumptionDisplay}</td>
                      <td>{efDisplay}</td>
                      <td style={{ color: "#3b82f6", fontWeight: 600 }}>
                        {formatNumber(entry.co2e, 3)}
                      </td>
                      <td style={{ color: "#6b7280", fontSize: "0.85rem" }}>
                        {entry.uncertainty != null
                          ? `${formatNumber(entry.uncertainty * 100, 1)}%`
                          : "—"}
                      </td>
                      <td style={{ color: "#6b7280", fontSize: "0.85rem" }}>
                        {entry.uncertainty != null
                          ? `${formatNumber(entry.uncertainty * 1.96 * 100, 1)}%`
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
                      <td style={{ textAlign: "center" }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "center",
                            gap: "8px",
                          }}
                        >
                          <button
                            className="icon-button"
                            onClick={() => handleDuplicate(entry)}
                            title="Duplicate"
                          >
                            <Copy size={16} />
                          </button>
                          <button
                            className="icon-button delete"
                            onClick={() => handleDelete(entry.id)}
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
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
                <td style={{ color: "#3b82f6" }}>
                  {formatNumber(
                    entries.reduce((sum, e) => sum + (e.co2e || 0), 0),
                    3,
                  )}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div
          className="pagination-controls"
          style={{
            padding: "15px",
            borderTop: "1px solid #e5e7eb",
            display: "flex",
            justifyContent: "center",
            gap: "20px",
            alignItems: "center",
          }}
        >
          <button
            className="action-btn secondary"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <span style={{ fontSize: "0.9rem", color: "#4b5563" }}>
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
        <Scope2ImportWizard
          onClose={() => setShowWizard(false)}
          onUploadSuccess={() => {
            setShowWizard(false);
            loadEntries();
            toast.success("Bulk import completed successfully");
          }}
        />
      )}
    </div>
  );
};

export default Scope2Form;
