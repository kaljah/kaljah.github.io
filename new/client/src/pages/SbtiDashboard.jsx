import React, { useState, useEffect, useMemo, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { LineChart, BarChart } from "../components/charts";
import { formatNumber } from "../utils/formatters";
import {
  Target,
  TrendingDown,
  Activity,
  CheckCircle,
  AlertTriangle,
  Download,
  Sliders,
  Save,
  Globe,
  Layers,
  ArrowRight,
  ShieldCheck,
  Calendar,
} from "lucide-react";
import "./SbtiDashboard.css";

const SbtiDashboard = () => {
  const { user } = useAuth();
  const toast = useToast();

  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const isFirstLoadRef = useRef(true);
  const [sbtiData, setSbtiData] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [savingTarget, setSavingTarget] = useState(false);

  // Editable Target Form State
  const [targetForm, setTargetForm] = useState({
    base_year: 2024,
    base_year_emissions: 0,
    target_year: 2050,
    reduction_rate_pct: 4.2,
    pathway_type: "1.5C",
  });

  const fetchData = async () => {
    if (isFirstLoadRef.current) {
      setLoading(true);
    } else {
      setIsUpdating(true);
    }
    try {
      const [trajRes, manageRes] = await Promise.all([
        api.get("/dashboard/sbti-trajectory"),
        api.get("/manage/sbti").catch(() => ({ data: {} })),
      ]);

      if (trajRes.data && trajRes.data.has_target) {
        setSbtiData(trajRes.data);
      } else {
        setSbtiData(null);
      }

      if (manageRes.data && manageRes.data.has_target) {
        setTargetForm({
          base_year: manageRes.data.base_year || 2024,
          base_year_emissions: manageRes.data.base_year_emissions || 0,
          target_year: manageRes.data.target_year || 2050,
          reduction_rate_pct: manageRes.data.reduction_rate_pct || 4.2,
          pathway_type: manageRes.data.pathway_type || "1.5C",
        });
      }
    } catch (err) {
      console.error("Failed to load SBTi data:", err);
      toast.show("Error loading SBTi progress data", "error");
    } finally {
      setLoading(false);
      setIsUpdating(false);
      isFirstLoadRef.current = false;
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handlePathwayChange = (pathway) => {
    if (pathway === "1.5C") {
      setTargetForm((prev) => ({
        ...prev,
        pathway_type: "1.5C",
        reduction_rate_pct: 4.2,
      }));
    } else if (pathway === "WB2C") {
      setTargetForm((prev) => ({
        ...prev,
        pathway_type: "WB2C",
        reduction_rate_pct: 2.5,
      }));
    }
  };

  const handleSaveTarget = async (e) => {
    e.preventDefault();
    if (!user || (user.role !== "admin" && user.role !== "superuser")) {
      toast.show("Only administrators or superusers can update SBTi targets.", "error");
      return;
    }

    setSavingTarget(true);
    try {
      await api.post("/manage/sbti", targetForm);
      toast.show("SBTi Net-Zero Target saved successfully", "success");
      setShowConfig(false);
      await fetchData();
    } catch (err) {
      toast.show(err.response?.data?.error || "Failed to save SBTi target", "error");
    } finally {
      setSavingTarget(false);
    }
  };

  const exportCsv = () => {
    if (!sbtiData || !sbtiData.trajectory || sbtiData.trajectory.length === 0) {
      toast.show("No trajectory data to export", "warning");
      return;
    }

    const headers = [
      "Year",
      "SBTi Target (tCO2e)",
      "BAU Projection (tCO2e)",
      "Actual Verified Emissions (tCO2e)",
      "Scope 1 (tCO2e)",
      "Scope 2 (tCO2e)",
      "Scope 3 (tCO2e)",
      "Status",
    ];

    const rows = sbtiData.trajectory.map((r) => {
      let status = "Projected";
      if (r.actual !== null && r.actual !== undefined) {
        status = r.actual <= r.sbti_target ? "Achieved" : "Off-Track";
      }
      return [
        r.year,
        r.sbti_target,
        r.bau_projection,
        r.actual !== null ? r.actual : "",
        r.scope1 || 0,
        r.scope2 || 0,
        r.scope3 || 0,
        status,
      ].join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `sbti_netzero_trajectory_${new Date().getFullYear()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Trajectory chart lines (Multi-scenario 1.5C + WB2C + BAU + Actual)
  const trajectoryLines = useMemo(() => [
    {
      dataKey: "actual",
      name: "Actual Verified Emissions",
      color: "#ff6600",
      strokeWidth: 3,
    },
    {
      dataKey: "sbti_15c",
      name: "1.5°C Pathway (-4.2%/yr)",
      color: "#10b981",
      strokeWidth: 2.5,
      strokeDasharray: "4 4",
    },
    {
      dataKey: "sbti_wb2c",
      name: "Well-Below 2°C (-2.5%/yr)",
      color: "#3b82f6",
      strokeWidth: 2,
      strokeDasharray: "3 3",
    },
    {
      dataKey: "bau_projection",
      name: "Business As Usual (+1.5%/yr)",
      color: "#94a3b8",
      strokeWidth: 2,
      strokeDasharray: "5 5",
    },
  ], [sbtiData]);

  // Scope breakdown bars
  const scopeBars = useMemo(() => [
    { dataKey: "scope1", name: "Scope 1 (Direct)", color: "#ff6600", stackId: "a" },
    { dataKey: "scope2", name: "Scope 2 (Indirect)", color: "#3b82f6", stackId: "a" },
    { dataKey: "scope3", name: "Scope 3 (Value Chain)", color: "#8b5cf6", stackId: "a" },
  ], []);


  if (loading && !sbtiData) {
    return <LoadingSpinner fullScreen message="Loading SBTi Net-Zero Trajectory..." />;
  }

  const isConfigured = sbtiData && sbtiData.has_target;
  const currentActual = sbtiData?.current_actual || 0;
  const currentTarget = sbtiData?.current_target || 0;
  const isOnTrack = sbtiData?.on_track ?? true;

  return (
    <div className="sbti-container" style={{ opacity: isUpdating ? 0.8 : 1, transition: "opacity 0.2s ease" }}>
      {/* Top Header */}
      <div className="sbti-header">
        <div className="sbti-title-group">
          <h1>
            <Target size={28} className="text-primary" />
            SBTi & Net-Zero Trajectory Dashboard
          </h1>
          <p>
            Track corporate decarbonization against Science Based Targets initiative (SBTi) 1.5°C & Well-Below 2°C pathways.
          </p>
        </div>

        <div className="sbti-header-actions">
          {user?.role in { admin: 1, superuser: 1 } && (
            <button
              className="btn-secondary"
              onClick={() => setShowConfig(!showConfig)}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Sliders size={16} />
              {showConfig ? "Hide Target Settings" : "Configure Target"}
            </button>
          )}

          {isConfigured && (
            <button
              className="btn-secondary"
              onClick={exportCsv}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <Download size={16} />
              Export Pathway CSV
            </button>
          )}
        </div>
      </div>

      {/* Target Setting Drawer / Form */}
      {showConfig && (
        <div className="sbti-config-panel">
          <div className="sbti-config-header">
            <h3>
              <Globe size={20} className="text-primary" />
              SBTi Corporate Target Setup
            </h3>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Per SBTi Corporate Net-Zero Standard v1.2
            </span>
          </div>

          <form onSubmit={handleSaveTarget}>
            <div className="sbti-form-grid">
              <div className="sbti-form-group">
                <label>Pathway Alignment</label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    type="button"
                    className={`btn-secondary ${targetForm.pathway_type === "1.5C" ? "active" : ""}`}
                    onClick={() => handlePathwayChange("1.5C")}
                    style={{
                      flex: 1,
                      background: targetForm.pathway_type === "1.5C" ? "rgba(16, 185, 129, 0.15)" : "#f8fafc",
                      borderColor: targetForm.pathway_type === "1.5C" ? "#10b981" : "#e2e8f0",
                      color: targetForm.pathway_type === "1.5C" ? "#065f46" : "#475569",
                    }}
                  >
                    1.5°C (4.2% / yr)
                  </button>
                  <button
                    type="button"
                    className={`btn-secondary ${targetForm.pathway_type === "WB2C" ? "active" : ""}`}
                    onClick={() => handlePathwayChange("WB2C")}
                    style={{
                      flex: 1,
                      background: targetForm.pathway_type === "WB2C" ? "rgba(59, 130, 246, 0.15)" : "#f8fafc",
                      borderColor: targetForm.pathway_type === "WB2C" ? "#3b82f6" : "#e2e8f0",
                      color: targetForm.pathway_type === "WB2C" ? "#1e40af" : "#475569",
                    }}
                  >
                    WB-2°C (2.5% / yr)
                  </button>
                </div>
              </div>

              <div className="sbti-form-group">
                <label>Base Year</label>
                <input
                  type="number"
                  className="sbti-input"
                  min="2015"
                  max="2030"
                  value={targetForm.base_year}
                  onChange={(e) => setTargetForm({ ...targetForm, base_year: parseInt(e.target.value) || 2024 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <label>Base Year Baseline Emissions (tCO2e)</label>
                <input
                  type="number"
                  step="0.01"
                  className="sbti-input"
                  min="0"
                  value={targetForm.base_year_emissions}
                  onChange={(e) => setTargetForm({ ...targetForm, base_year_emissions: parseFloat(e.target.value) || 0 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <label>Net-Zero Target Year</label>
                <input
                  type="number"
                  className="sbti-input"
                  min="2030"
                  max="2070"
                  value={targetForm.target_year}
                  onChange={(e) => setTargetForm({ ...targetForm, target_year: parseInt(e.target.value) || 2050 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <label>Annual Reduction Rate (%)</label>
                <input
                  type="number"
                  step="0.1"
                  className="sbti-input"
                  value={targetForm.reduction_rate_pct}
                  onChange={(e) => setTargetForm({ ...targetForm, reduction_rate_pct: parseFloat(e.target.value) || 0 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={savingTarget}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", height: "42px" }}
                >
                  <Save size={16} />
                  {savingTarget ? "Saving Target..." : "Save SBTi Target"}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* KPI Cards */}
      <div className="sbti-kpi-grid">
        <div className="sbti-kpi-card">
          <div className="sbti-kpi-header">
            <span className="sbti-kpi-title">Base Year Baseline</span>
            <div className="sbti-kpi-icon">
              <Calendar size={18} />
            </div>
          </div>
          <div className="sbti-kpi-value">
            {formatNumber(sbtiData?.base_year_emissions || 0, 0)}
            <span className="sbti-kpi-unit">tCO2e</span>
          </div>
          <div className="sbti-kpi-subtitle">
            Base Year: {sbtiData?.base_year || "Not Set"}
          </div>
        </div>

        <div className="sbti-kpi-card info">
          <div className="sbti-kpi-header">
            <span className="sbti-kpi-title">Current Year Target</span>
            <div className="sbti-kpi-icon info">
              <Target size={18} />
            </div>
          </div>
          <div className="sbti-kpi-value">
            {formatNumber(currentTarget, 0)}
            <span className="sbti-kpi-unit">tCO2e</span>
          </div>
          <div className="sbti-kpi-subtitle">
            Actual: {formatNumber(currentActual, 0)} tCO2e ({new Date().getFullYear()})
          </div>
        </div>

        <div className={`sbti-kpi-card ${isOnTrack ? "success" : "warning"}`}>
          <div className="sbti-kpi-header">
            <span className="sbti-kpi-title">Pathway Status</span>
            <div className={`sbti-kpi-icon ${isOnTrack ? "success" : "warning"}`}>
              {isOnTrack ? <CheckCircle size={18} /> : <AlertTriangle size={18} />}
            </div>
          </div>
          <div className="sbti-kpi-value">
            <span className={`status-pill ${isOnTrack ? "on-track" : "behind"}`}>
              {isOnTrack ? "ON TRACK" : "BEHIND TARGET"}
            </span>
          </div>
          <div className="sbti-kpi-subtitle">
            Reduction: {sbtiData?.reduction_achieved_pct || 0}% vs Baseline
          </div>
        </div>

        <div className="sbti-kpi-card success">
          <div className="sbti-kpi-header">
            <span className="sbti-kpi-title">Net-Zero Goal ({sbtiData?.target_year || 2050})</span>
            <div className="sbti-kpi-icon success">
              <TrendingDown size={18} />
            </div>
          </div>
          <div className="sbti-kpi-value">
            {formatNumber(sbtiData?.target_emissions_final || 0, 0)}
            <span className="sbti-kpi-unit">tCO2e</span>
          </div>
          <div className="sbti-kpi-subtitle">
            Linear Rate: {sbtiData?.reduction_rate_pct || 4.2}% per year
          </div>
        </div>
      </div>

      {/* Main Trajectory Charts Grid */}
      <div className="sbti-charts-grid">
        <div className="sbti-card">
          <div className="sbti-card-header">
            <div>
              <h3 className="sbti-card-title">SBTi Decarbonization Pathway ({sbtiData?.pathway_type || "1.5°C"})</h3>
              <p className="sbti-card-subtitle">
                Linear reduction trajectory from base year {sbtiData?.base_year || 2024} to target year {sbtiData?.target_year || 2050}
              </p>
            </div>
          </div>

          <div style={{ height: "360px", width: "100%" }}>
            {sbtiData?.trajectory && sbtiData.trajectory.length > 0 ? (
              <LineChart
                data={sbtiData.trajectory}
                xAxisKey="year"
                lines={trajectoryLines}
                height={350}
              />
            ) : (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", color: "#94a3b8" }}>
                No trajectory configured. Click "Configure Target" to set baseline and targets.
              </div>
            )}
          </div>
        </div>

        <div className="sbti-card">
          <div className="sbti-card-header">
            <div>
              <h3 className="sbti-card-title">Emissions Composition by Scope</h3>
              <p className="sbti-card-subtitle">
                Verified Scope 1, Scope 2, and Scope 3 breakdown
              </p>
            </div>
          </div>

          <div style={{ height: "360px", width: "100%" }}>
            {sbtiData?.trajectory && sbtiData.trajectory.length > 0 ? (
              <BarChart
                data={sbtiData.trajectory.filter((t) => t.actual !== null && t.actual !== undefined && t.actual > 0)}
                xAxisKey="year"
                bars={scopeBars}
                height={350}
              />
            ) : (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", color: "#94a3b8" }}>
                No verified emissions history available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Milestone & Projection Table */}
      <div className="sbti-card">
        <div className="sbti-card-header">
          <div>
            <h3 className="sbti-card-title">Annual Pathway Milestones & Verification Data</h3>
            <p className="sbti-card-subtitle">
              Yearly comparison of targets, actual emissions, and progress towards net-zero alignment
            </p>
          </div>
        </div>

        <div className="sbti-table-container">
          <table className="sbti-table">
            <thead>
              <tr>
                <th>Year</th>
                <th>SBTi Target</th>
                <th>BAU Projection</th>
                <th>Actual Emissions</th>
                <th>Scope 1</th>
                <th>Scope 2</th>
                <th>Scope 3</th>
                <th>Variance vs Target</th>
                <th>Compliance Status</th>
              </tr>
            </thead>
            <tbody>
              {sbtiData?.trajectory && sbtiData.trajectory.length > 0 ? (
                sbtiData.trajectory.map((row) => {
                  const hasActual = row.actual !== null && row.actual !== undefined && row.actual > 0;
                  const variance = hasActual ? row.actual - row.sbti_target : null;
                  let statusClass = "projected";
                  let statusLabel = "Projected";

                  if (hasActual) {
                    if (row.actual <= row.sbti_target) {
                      statusClass = "achieved";
                      statusLabel = "Achieved";
                    } else {
                      statusClass = "off-track";
                      statusLabel = "Off-Track";
                    }
                  }

                  return (
                    <tr key={row.year}>
                      <td style={{ fontWeight: 600 }}>{row.year}</td>
                      <td>{formatNumber(row.sbti_target, 1)} tCO2e</td>
                      <td style={{ color: "#64748b" }}>{formatNumber(row.bau_projection, 1)} tCO2e</td>
                      <td style={{ fontWeight: hasActual ? 700 : 400, color: hasActual ? "var(--text-main)" : "#94a3b8" }}>
                        {hasActual ? `${formatNumber(row.actual, 1)} tCO2e` : "—"}
                      </td>
                      <td>{hasActual ? `${formatNumber(row.scope1, 1)}` : "—"}</td>
                      <td>{hasActual ? `${formatNumber(row.scope2, 1)}` : "—"}</td>
                      <td>{hasActual ? `${formatNumber(row.scope3, 1)}` : "—"}</td>
                      <td>
                        {variance !== null ? (
                          <span style={{ color: variance <= 0 ? "#10b981" : "#ef4444", fontWeight: 600 }}>
                            {variance > 0 ? `+${formatNumber(variance, 1)}` : formatNumber(variance, 1)} tCO2e
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        <span className={`badge-status ${statusClass}`}>
                          {statusLabel}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="9" style={{ textAlign: "center", padding: "30px", color: "#94a3b8" }}>
                    No trajectory milestone records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SbtiDashboard;
