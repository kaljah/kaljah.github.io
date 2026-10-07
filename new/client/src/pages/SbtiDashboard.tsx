import { Button, PageHeader, SegmentedControl } from "../ui";
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
  Download,
  Sliders,
  Save,
  Globe,
  ShieldCheck,
  Calendar,
  Sparkles,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import "./SbtiDashboard.css";

interface TrajectoryRow {
  year: number | string;
  sbti_target: number;
  sbti_15c?: number;
  sbti_wb2c?: number;
  bau_projection?: number;
  actual?: number | null;
  scope1?: number;
  scope2?: number;
  scope3?: number;
  scope12?: number;
  [key: string]: any;
}

interface SbtiData {
  has_target?: boolean;
  trajectory?: TrajectoryRow[];
  target_year?: number;
  base_year?: number;
  base_year_emissions?: number;
  reduction_rate_pct?: number;
  pathway_type?: string;
  pathway_label?: string;
  current_actual_emissions?: number | null;
  current_actual?: number | null;
  current_target_emissions?: number | null;
  current_target?: number | null;
  ytd_actual?: number | null;
  ytd_year?: number | string;
  on_track?: boolean | null;
  current_year?: number;
  latest_actual_year?: number;
  reduction_achieved_pct?: number;
  target_emissions_final?: number;
  residual_floor?: number;
  [key: string]: any;
}

const SbtiDashboard: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();

  const [loading, setLoading] = useState<boolean>(true);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const isFirstLoadRef = useRef<boolean>(true);
  const [sbtiData, setSbtiData] = useState<SbtiData | null>(null);
  const [showConfig, setShowConfig] = useState<boolean>(false);
  const [savingTarget, setSavingTarget] = useState<boolean>(false);
  const [scopeMode, setScopeMode] = useState<string>("all"); // 'all' (Scopes 1+2+3) or 's1_s2' (Scopes 1+2)

  // Editable Target Form State
  const [targetForm, setTargetForm] = useState({
    base_year: 2024,
    base_year_emissions: 0,
    target_year: 2050,
    reduction_rate_pct: 4.2,
    pathway_type: "1.5C",
  });

  const fetchData = async (activeScope = scopeMode) => {
    if (isFirstLoadRef.current) {
      setLoading(true);
    } else {
      setIsUpdating(true);
    }
    try {
      const [trajRes, manageRes] = await Promise.all([
        api.get(`/dashboard/sbti-trajectory?scope=${activeScope}`),
        api.get("/manage/sbti").catch(() => ({ data: {} })),
      ]);

      if (trajRes.data && trajRes.data.has_target) {
        setSbtiData(trajRes.data);
      } else {
        setSbtiData(null);
      }

      if (manageRes.data) {
        if (manageRes.data.has_target) {
          setTargetForm({
            base_year: manageRes.data.base_year || 2024,
            base_year_emissions: manageRes.data.base_year_emissions || 0,
            target_year: manageRes.data.target_year || 2050,
            reduction_rate_pct: manageRes.data.reduction_rate_pct || 4.2,
            pathway_type: manageRes.data.pathway_type || "1.5C",
          });
        } else if (manageRes.data.suggested_base_year_emissions) {
          setTargetForm((prev) => ({
            ...prev,
            base_year: manageRes.data.suggested_base_year || 2024,
            base_year_emissions: manageRes.data.suggested_base_year_emissions || 0,
          }));
        }
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

  const handleScopeModeChange = (newScope: string) => {
    setScopeMode(newScope);
    fetchData(newScope);
  };

  const handlePathwayChange = (pathway: string) => {
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

  const handleAutoFillBaseline = async () => {
    try {
      const res = await api.get(`/manage/sbti?base_year=${targetForm.base_year}`);
      if (res.data && res.data.suggested_base_year_emissions !== undefined) {
        setTargetForm((prev) => ({
          ...prev,
          base_year_emissions: res.data.suggested_base_year_emissions,
        }));
        toast.show(
          `Baseline auto-filled with verified emissions for ${targetForm.base_year}: ${formatNumber(res.data.suggested_base_year_emissions, 1)} tCO2e`,
          "success"
        );
      }
    } catch {
      toast.show("Could not fetch verified baseline emissions for this year", "warning");
    }
  };

  const handleSaveTarget = async (e: React.FormEvent) => {
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
      await fetchData(scopeMode);
    } catch (err: any) {
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
      "Corporate SBTi Target (tCO2e)",
      "1.5C Benchmark (tCO2e)",
      "WB-2C Benchmark (tCO2e)",
      "BAU Projection (tCO2e)",
      "Actual Verified Emissions (tCO2e)",
      "Scope 1 (tCO2e)",
      "Scope 2 (tCO2e)",
      "Scope 3 (tCO2e)",
      "Scope 1+2 (tCO2e)",
      "Status",
    ];

    const rows = sbtiData.trajectory.map((r) => {
      let status = "Projected";
      if (r.actual !== null && r.actual !== undefined) {
        status = r.actual <= r.sbti_target ? "Achieved" : "Off-Track";
      }
      return [
        `"${r.year}"`,
        r.sbti_target,
        r.sbti_15c,
        r.sbti_wb2c,
        r.bau_projection,
        r.actual !== null && r.actual !== undefined ? r.actual : "",
        r.scope1 || 0,
        r.scope2 || 0,
        r.scope3 || 0,
        r.scope12 || 0,
        `"${status}"`,
      ].join(",");
    });

    const csvContent = "\uFEFF" + [headers.join(","), ...rows].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `sbti_netzero_trajectory_${sbtiData.target_year || 2050}_${new Date().getFullYear()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.show("SBTi Trajectory CSV exported successfully", "success");
  };

  // Trajectory chart lines: Active Corporate Target + Actual + Reference Benchmarks + BAU
  const trajectoryLines = useMemo(() => [
    {
      dataKey: "sbti_target",
      name: `Corporate Target (${sbtiData?.reduction_rate_pct || 4.2}%/yr)`,
      color: "#10b981",
      strokeWidth: 3,
    },
    {
      dataKey: "actual",
      name: `Actual Emissions (${scopeMode === "s1_s2" ? "Scope 1+2" : "Scope 1+2+3"})`,
      color: "#ff6600",
      strokeWidth: 3,
    },
    {
      dataKey: "sbti_15c",
      name: "1.5°C Benchmark (-4.2%/yr)",
      color: "#059669",
      strokeWidth: 2,
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
      strokeWidth: 1.5,
      strokeDasharray: "5 5",
    },
  ], [sbtiData, scopeMode]);

  // Scope breakdown bars
  const scopeBars = useMemo(() => [
    { dataKey: "scope1", name: "Scope 1 (Direct)", color: "#ff6600", stackId: "a" },
    { dataKey: "scope2", name: "Scope 2 (Indirect)", color: "#3b82f6", stackId: "a" },
    { dataKey: "scope3", name: "Scope 3 (Value Chain)", color: "#8b5cf6", stackId: "a" },
  ], []);

  if (loading && !sbtiData) {
    return <LoadingSpinner fullScreen message="Loading SBTi Net-Zero Trajectory..." />;
  }

  const isConfigured = Boolean(sbtiData && sbtiData.has_target);
  // No complete year yet: the server returns null for the current year and a year-to-date total;
  // the target of that year still comes from the pathway (browser test #14 showed both as 0)
  const ytdYear = sbtiData?.ytd_year;
  const ytdRow = (sbtiData?.trajectory || []).find((r) => String(r.year) === String(ytdYear));
  const currentActual = sbtiData?.current_actual_emissions ?? sbtiData?.current_actual ?? null;
  const currentTarget =
    sbtiData?.current_target_emissions ?? sbtiData?.current_target ?? ytdRow?.sbti_target ?? null;
  const isYtd = currentActual == null && sbtiData?.ytd_actual != null;
  // BUG-028: no evaluable year -> "No data", never a default ON TRACK
  const isOnTrack = isConfigured ? (sbtiData?.on_track ?? null) : null;
  const noData = isConfigured && isOnTrack === null;
  const currentYear = sbtiData?.current_year || sbtiData?.latest_actual_year || ytdYear || new Date().getFullYear();

  return (
    <div className="[padding:24px] [max-width:1600px] [margin:0_auto] [display:flex] [flex-direction:column] [gap:24px]" style={{ opacity: isUpdating ? 0.8 : 1, transition: "opacity 0.2s ease" }}>
      {/* Top Header */}
      <PageHeader
        className="mb-6"
        title="SBTi & Net-Zero Trajectory"
        description="Track corporate decarbonization against Science Based Targets initiative (SBTi) 1.5°C & Well-Below 2°C pathways per Corporate Net-Zero Standard v1.2."
        actions={
          <>
            <SegmentedControl
              label="Scope coverage"
              value={scopeMode}
              onChange={handleScopeModeChange}
              options={[
                { value: "all", label: "All scopes (1+2+3)", title: "Track across all scopes (Scope 1, 2, and 3)" },
                { value: "s1_s2", label: "Scope 1+2 (operational)", title: "Track operational emissions (Scope 1 and 2 only)" },
              ]}
            />
            {(user?.role === "admin" || user?.role === "superuser") && (
              <Button variant="secondary" onClick={() => setShowConfig(!showConfig)}>
                <Sliders className="size-4" aria-hidden="true" />
                {showConfig ? "Hide target settings" : "Configure target"}
              </Button>
            )}
            {isConfigured && (
              <Button variant="secondary" onClick={exportCsv}>
                <Download className="size-4" aria-hidden="true" />
                Export pathway CSV
              </Button>
            )}
          </>
        }
      />

      {/* Target Setting Drawer / Form */}
      {showConfig && (
        <div className="[background:var(--card-bg,_var(--color-white))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-lg)] [padding:24px] [box-shadow:var(--shadow-card)]">
          <div className="sbti-config-header">
            <h3>
              <Globe size={20} className="text-primary" />
              SBTi Corporate Target Setup
            </h3>
            <span className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
              Per SBTi Corporate Net-Zero Standard v1.2 (Criteria C24 / NZ-C1)
            </span>
          </div>

          <form onSubmit={handleSaveTarget}>
            <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))] [gap:16px] [align-items:flex-end]">
              <div className="sbti-form-group">
                <label>Pathway Alignment</label>
                <div className="flex! gap-[8px]!">
                  <button
                    type="button"
                    className={`btn-secondary ${targetForm.pathway_type === "1.5C" ? "active" : ""}`}
                    onClick={() => handlePathwayChange("1.5C")}
                    style={{
                      flex: 1,
                      background: targetForm.pathway_type === "1.5C" ? "rgba(16, 185, 129, 0.15)" : "var(--input-bg, #f8fafc)",
                      borderColor: targetForm.pathway_type === "1.5C" ? "#10b981" : "var(--border-color, #e2e8f0)",
                      color: targetForm.pathway_type === "1.5C" ? "#065f46" : "var(--text-secondary, #475569)",
                      fontWeight: 600,
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
                      background: targetForm.pathway_type === "WB2C" ? "rgba(59, 130, 246, 0.15)" : "var(--input-bg, #f8fafc)",
                      borderColor: targetForm.pathway_type === "WB2C" ? "#3b82f6" : "var(--border-color, #e2e8f0)",
                      color: targetForm.pathway_type === "WB2C" ? "#1e40af" : "var(--text-secondary, #475569)",
                      fontWeight: 600,
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
                  className="[padding:10px_14px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--input-bg,_var(--color-ink-50))] [color:var(--text-main,_var(--color-ink-900))] [font-size:var(--text-md)] [transition:all_0.2s] focus:[outline:none] focus:[border-color:var(--primary,_var(--color-brand-500))] focus:[background:var(--card-bg,_var(--color-white))] focus:[box-shadow:0_0_0_3px_rgba(249,_115,_22,_0.1)]"
                  min="2015"
                  max="2035"
                  value={targetForm.base_year}
                  onChange={(e) => setTargetForm({ ...targetForm, base_year: parseInt(e.target.value) || 2024 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <div className="flex! justify-between! items-center!">
                  <label>Base Year Baseline (tCO2e)</label>
                  <button
                    type="button"
                    className="[display:inline-flex] [align-items:center] [gap:5px] [padding:4px_10px] [font-size:var(--text-sm)] [font-weight:600] [border-radius:var(--radius-sm)] [background:rgba(37,_99,_235,_0.1)] [color:var(--color-blue-600)] [border:1px_solid_rgba(37,_99,_235,_0.2)] [cursor:pointer] [transition:all_0.2s] hover:[background:rgba(37,_99,_235,_0.2)] hover:[border-color:var(--color-blue-600)]"
                    onClick={handleAutoFillBaseline}
                    title="Auto-fill with verified emissions for base year"
                  >
                    <Sparkles size={12} />
                    Auto-Fill Verified
                  </button>
                </div>
                <input
                  type="number"
                  step="0.01"
                  className="[padding:10px_14px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--input-bg,_var(--color-ink-50))] [color:var(--text-main,_var(--color-ink-900))] [font-size:var(--text-md)] [transition:all_0.2s] focus:[outline:none] focus:[border-color:var(--primary,_var(--color-brand-500))] focus:[background:var(--card-bg,_var(--color-white))] focus:[box-shadow:0_0_0_3px_rgba(249,_115,_22,_0.1)]"
                  min="0.01"
                  value={targetForm.base_year_emissions}
                  onChange={(e) => setTargetForm({ ...targetForm, base_year_emissions: parseFloat(e.target.value) || 0 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <label>Net-Zero Target Year</label>
                <input
                  type="number"
                  className="[padding:10px_14px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--input-bg,_var(--color-ink-50))] [color:var(--text-main,_var(--color-ink-900))] [font-size:var(--text-md)] [transition:all_0.2s] focus:[outline:none] focus:[border-color:var(--primary,_var(--color-brand-500))] focus:[background:var(--card-bg,_var(--color-white))] focus:[box-shadow:0_0_0_3px_rgba(249,_115,_22,_0.1)]"
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
                  min="0.1"
                  max="25.0"
                  className="[padding:10px_14px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--input-bg,_var(--color-ink-50))] [color:var(--text-main,_var(--color-ink-900))] [font-size:var(--text-md)] [transition:all_0.2s] focus:[outline:none] focus:[border-color:var(--primary,_var(--color-brand-500))] focus:[background:var(--card-bg,_var(--color-white))] focus:[box-shadow:0_0_0_3px_rgba(249,_115,_22,_0.1)]"
                  value={targetForm.reduction_rate_pct}
                  onChange={(e) => setTargetForm({ ...targetForm, reduction_rate_pct: parseFloat(e.target.value) || 0 })}
                  required
                />
              </div>

              <div className="sbti-form-group">
                <button
                  type="submit"
                  className="btn-primary flex! items-center! justify-center! gap-[8px]! h-[42px]!"
                  disabled={savingTarget}
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
      <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(240px,_1fr))] [gap:18px]">
        <div className="[padding:22px_24px] [border-radius:var(--radius-lg)] [background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [display:flex] [flex-direction:column] [justify-content:space-between] [position:relative] [overflow:hidden] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated,_0_8px_24px_rgba(0,_0,_0,_0.08))] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[width:4px] before:[height:100%] before:[background:var(--primary,_var(--color-brand-500))] before:[border-radius:var(--radius-sm)_0_0_var(--radius-sm)] [&.success::before]:[background:var(--color-green-500)] [&&]:[&.warning::before]:[background:var(--color-amber-500)] [&&]:[&&]:[&.info::before]:[background:var(--color-blue-500)] [&&]:[&&]:[&&]:[&.neutral::before]:[background:var(--color-ink-400)]">
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:12px]">
            <span className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [text-transform:uppercase] [letter-spacing:0.05em]">Base Year Baseline</span>
            <div className="[width:36px] [height:36px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [background:rgba(249,_115,_22,_0.1)] [color:var(--color-link)] [&.success]:[background:rgba(16,_185,_129,_0.1)] [&.success]:[color:var(--color-green-700)] [&&]:[&.warning]:[background:rgba(245,_158,_11,_0.1)] [&&]:[&.warning]:[color:var(--color-amber-700)] [&&]:[&&]:[&.info]:[background:rgba(59,_130,_246,_0.1)] [&&]:[&&]:[&.info]:[color:var(--color-blue-700)] [&&]:[&&]:[&&]:[&.neutral]:[background:rgba(148,_163,_184,_0.15)] [&&]:[&&]:[&&]:[&.neutral]:[color:var(--color-ink-500)]">
              <Calendar size={18} />
            </div>
          </div>
          <div className="[font-size:var(--text-2xl)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:4px]">
            {formatNumber(sbtiData?.base_year_emissions || 0, 0)}
            <span className="[font-size:var(--text-base)] [font-weight:500] [color:var(--text-secondary,_var(--color-ink-500))] [margin-left:4px]">tCO2e</span>
          </div>
          <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [display:flex] [align-items:center] [gap:4px]">
            Base Year: {sbtiData?.base_year || "Not Set"}
          </div>
        </div>

        <div className="[padding:22px_24px] [border-radius:var(--radius-lg)] [background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [display:flex] [flex-direction:column] [justify-content:space-between] [position:relative] [overflow:hidden] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated,_0_8px_24px_rgba(0,_0,_0,_0.08))] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[width:4px] before:[height:100%] before:[background:var(--primary,_var(--color-brand-500))] before:[border-radius:var(--radius-sm)_0_0_var(--radius-sm)] [&.success::before]:[background:var(--color-green-500)] [&&]:[&.warning::before]:[background:var(--color-amber-500)] [&&]:[&&]:[&.info::before]:[background:var(--color-blue-500)] [&&]:[&&]:[&&]:[&.neutral::before]:[background:var(--color-ink-400)] info">
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:12px]">
            <span className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [text-transform:uppercase] [letter-spacing:0.05em]">Current Year Target</span>
            <div className="[width:36px] [height:36px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [background:rgba(249,_115,_22,_0.1)] [color:var(--color-link)] [&.success]:[background:rgba(16,_185,_129,_0.1)] [&.success]:[color:var(--color-green-700)] [&&]:[&.warning]:[background:rgba(245,_158,_11,_0.1)] [&&]:[&.warning]:[color:var(--color-amber-700)] [&&]:[&&]:[&.info]:[background:rgba(59,_130,_246,_0.1)] [&&]:[&&]:[&.info]:[color:var(--color-blue-700)] [&&]:[&&]:[&&]:[&.neutral]:[background:rgba(148,_163,_184,_0.15)] [&&]:[&&]:[&&]:[&.neutral]:[color:var(--color-ink-500)] info">
              <Target size={18} />
            </div>
          </div>
          <div className="[font-size:var(--text-2xl)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:4px]">
            {currentTarget == null ? "—" : formatNumber(currentTarget, 0)}
            <span className="[font-size:var(--text-base)] [font-weight:500] [color:var(--text-secondary,_var(--color-ink-500))] [margin-left:4px]">tCO2e</span>
          </div>
          <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [display:flex] [align-items:center] [gap:4px]">
            {currentActual != null
              ? `Actual: ${formatNumber(currentActual, 0)} tCO2e (${currentYear})`
              : isYtd
                ? `Year to date: ${formatNumber(sbtiData?.ytd_actual, 0)} tCO2e (${ytdYear}, partial year)`
                : `Actual: — (${currentYear})`}
          </div>
        </div>

        <div className={`[padding:22px_24px] [border-radius:var(--radius-lg)] [background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [display:flex] [flex-direction:column] [justify-content:space-between] [position:relative] [overflow:hidden] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated,_0_8px_24px_rgba(0,_0,_0,_0.08))] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[width:4px] before:[height:100%] before:[background:var(--primary,_var(--color-brand-500))] before:[border-radius:var(--radius-sm)_0_0_var(--radius-sm)] [&.success::before]:[background:var(--color-green-500)] [&&]:[&.warning::before]:[background:var(--color-amber-500)] [&&]:[&&]:[&.info::before]:[background:var(--color-blue-500)] [&&]:[&&]:[&&]:[&.neutral::before]:[background:var(--color-ink-400)] ${isConfigured && !noData ? (isOnTrack ? "success" : "warning") : "neutral"}`}>
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:12px]">
            <span className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [text-transform:uppercase] [letter-spacing:0.05em]">Pathway Status</span>
            <div className={`[width:36px] [height:36px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [background:rgba(249,_115,_22,_0.1)] [color:var(--color-link)] [&.success]:[background:rgba(16,_185,_129,_0.1)] [&.success]:[color:var(--color-green-700)] [&&]:[&.warning]:[background:rgba(245,_158,_11,_0.1)] [&&]:[&.warning]:[color:var(--color-amber-700)] [&&]:[&&]:[&.info]:[background:rgba(59,_130,_246,_0.1)] [&&]:[&&]:[&.info]:[color:var(--color-blue-700)] [&&]:[&&]:[&&]:[&.neutral]:[background:rgba(148,_163,_184,_0.15)] [&&]:[&&]:[&&]:[&.neutral]:[color:var(--color-ink-500)] ${isConfigured && !noData ? (isOnTrack ? "success" : "warning") : "neutral"}`}>
              {isConfigured && !noData ? (
                isOnTrack ? <CheckCircle size={18} /> : <AlertTriangle size={18} />
              ) : (
                <ShieldCheck size={18} />
              )}
            </div>
          </div>
          <div className="[font-size:var(--text-2xl)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:4px]">
            <span className={`status-pill ${isConfigured && !noData ? (isOnTrack ? "on-track" : "behind") : "not-set"}`}>
              {!isConfigured ? "NOT CONFIGURED" : noData ? "NO DATA" : isOnTrack ? "ON TRACK" : "BEHIND TARGET"}
            </span>
          </div>
          <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [display:flex] [align-items:center] [gap:4px]">
            {!isConfigured
              ? "Set corporate baseline & targets to track alignment"
              : noData
                ? "No complete year of verified data in the target window"
                : `Reduction: ${sbtiData?.reduction_achieved_pct}% vs ${sbtiData?.base_year} baseline (progress year ${sbtiData?.latest_actual_year})`}
          </div>
        </div>

        <div className="[padding:22px_24px] [border-radius:var(--radius-lg)] [background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [display:flex] [flex-direction:column] [justify-content:space-between] [position:relative] [overflow:hidden] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated,_0_8px_24px_rgba(0,_0,_0,_0.08))] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[width:4px] before:[height:100%] before:[background:var(--primary,_var(--color-brand-500))] before:[border-radius:var(--radius-sm)_0_0_var(--radius-sm)] [&.success::before]:[background:var(--color-green-500)] [&&]:[&.warning::before]:[background:var(--color-amber-500)] [&&]:[&&]:[&.info::before]:[background:var(--color-blue-500)] [&&]:[&&]:[&&]:[&.neutral::before]:[background:var(--color-ink-400)] success">
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:12px]">
            <span className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [text-transform:uppercase] [letter-spacing:0.05em]">Net-Zero Goal ({sbtiData?.target_year || 2050})</span>
            <div className="[width:36px] [height:36px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [background:rgba(249,_115,_22,_0.1)] [color:var(--color-link)] [&.success]:[background:rgba(16,_185,_129,_0.1)] [&.success]:[color:var(--color-green-700)] [&&]:[&.warning]:[background:rgba(245,_158,_11,_0.1)] [&&]:[&.warning]:[color:var(--color-amber-700)] [&&]:[&&]:[&.info]:[background:rgba(59,_130,_246,_0.1)] [&&]:[&&]:[&.info]:[color:var(--color-blue-700)] [&&]:[&&]:[&&]:[&.neutral]:[background:rgba(148,_163,_184,_0.15)] [&&]:[&&]:[&&]:[&.neutral]:[color:var(--color-ink-500)] success">
              <TrendingDown size={18} />
            </div>
          </div>
          <div className="[font-size:var(--text-2xl)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:4px]">
            {formatNumber(sbtiData?.target_emissions_final || 0, 0)}
            <span className="[font-size:var(--text-base)] [font-weight:500] [color:var(--text-secondary,_var(--color-ink-500))] [margin-left:4px]">tCO2e</span>
          </div>
          <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [display:flex] [align-items:center] [gap:4px]">
            {isConfigured
              ? `Residual Floor: ${formatNumber(sbtiData?.residual_floor || 0, 0)} tCO2e (10% Cap)`
              : "Linear Rate: 4.2% per year"}
          </div>
        </div>
      </div>

      {/* Main Trajectory Charts Grid */}
      <div className="[display:grid] [grid-template-columns:2fr_1fr]! [gap:24px] [@media(max-width:1100px)]:[grid-template-columns:1fr]!">
        <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [&&]:[border-radius:var(--radius-lg)] [padding:24px] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[border-color:var(--border-color-hover,_rgba(255,_255,_255,_0.95))]">
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:18px]">
            <div>
              <h3 className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:2px]">{sbtiData?.pathway_label || "Decarbonization Pathway"}</h3>
              <p className="[font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-500))]">
                Linear reduction trajectory from base year {sbtiData?.base_year || 2024} to target year {sbtiData?.target_year || 2050} (Residual emissions capped at 10% per NZ-C1)
              </p>
            </div>
          </div>

          <div className="h-[360px]! w-full!">
            {sbtiData?.trajectory && sbtiData.trajectory.length > 0 ? (
              <LineChart
                data={sbtiData.trajectory}
                xAxisKey="year"
                lines={trajectoryLines}
                height={350}
              />
            ) : (
              <div className="flex! justify-center! items-center! h-full! text-[color:#475569]!">
                No trajectory configured. Click "Configure Target" to set baseline and targets.
              </div>
            )}
          </div>
        </div>

        <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [&&]:[border-radius:var(--radius-lg)] [padding:24px] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[border-color:var(--border-color-hover,_rgba(255,_255,_255,_0.95))]">
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:18px]">
            <div>
              <h3 className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:2px]">Emissions Composition by Scope</h3>
              <p className="[font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-500))]">
                Verified Scope 1, Scope 2, and Scope 3 breakdown
              </p>
            </div>
          </div>

          <div className="h-[360px]! w-full!">
            {sbtiData?.trajectory && sbtiData.trajectory.length > 0 ? (
              <BarChart
                data={sbtiData.trajectory.filter((t) => t.actual !== null && t.actual !== undefined && (t.actual as number) > 0)}
                xAxisKey="year"
                bars={scopeBars}
                height={350}
              />
            ) : (
              <div className="flex! justify-center! items-center! h-full! text-[color:#475569]!">
                No verified emissions history available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Milestone & Projection Table */}
      <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [&&]:[border-radius:var(--radius-lg)] [padding:24px] [box-shadow:var(--shadow-card,_0_4px_12px_rgba(0,_0,_0,_0.05))] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] hover:[border-color:var(--border-color-hover,_rgba(255,_255,_255,_0.95))]">
        <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:18px]">
          <div>
            <h3 className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--text-main,_var(--color-ink-900))] [margin-bottom:2px]">Annual Pathway Milestones & Verification Data</h3>
            <p className="[font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-500))]">
              Yearly comparison of targets, actual emissions, and progress towards net-zero alignment ({scopeMode === "s1_s2" ? "Scope 1+2 Operational View" : "All Scopes View"})
            </p>
          </div>
        </div>

        <div className="[overflow-x:auto] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--bg-card,_rgba(255,_255,_255,_0.6))] [backdrop-filter:blur(8px)]" tabIndex={0} role="region" aria-label="Pathway table">
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
                <th>Scope 1+2</th>
                <th>Variance vs Target</th>
                <th>Compliance Status</th>
              </tr>
            </thead>
            <tbody>
              {sbtiData?.trajectory && sbtiData.trajectory.length > 0 ? (
                sbtiData.trajectory.map((row) => {
                  const hasActual = row.actual !== null && row.actual !== undefined && row.actual > 0;
                  const variance = hasActual && row.actual != null ? row.actual - row.sbti_target : null;
                  let statusClass = "projected";
                  let statusLabel = "Projected";

                  if (hasActual && row.actual != null) {
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
                      <td className="font-semibold!">{row.year}</td>
                      <td className="font-medium!">{formatNumber(row.sbti_target, 1)} tCO2e</td>
                      <td className="text-[color:var(--text-primary,_#0f172a)]! font-medium!">{formatNumber(row.bau_projection, 1)} tCO2e</td>
                      <td className={`${hasActual ? "[font-weight:700]!" : "[font-weight:400]!"} ${hasActual ? "[color:var(--text-primary,_#0f172a)]!" : "[color:#64748b]!"}`}>
                        {hasActual ? `${formatNumber(row.actual, 1)} tCO2e` : "—"}
                      </td>
                      <td>{hasActual ? `${formatNumber(row.scope1, 1)}` : "—"}</td>
                      <td>{hasActual ? `${formatNumber(row.scope2, 1)}` : "—"}</td>
                      <td>{hasActual ? `${formatNumber(row.scope3, 1)}` : "—"}</td>
                      <td>{hasActual ? `${formatNumber(row.scope12, 1)}` : "—"}</td>
                      <td>
                        {variance !== null ? (
                          <span className={`[font-weight:600]! ${variance <= 0 ? "[color:#2e7d32]!" : "[color:#b91c1c]!"}`}>
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
                  <td colSpan={10} className="text-center! p-[30px]! text-[color:#475569]!">
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
