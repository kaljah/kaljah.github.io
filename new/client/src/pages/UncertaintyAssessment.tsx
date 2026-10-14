import React, { useState, useEffect, useMemo } from "react";
import { BarChart } from "../components/charts";
import {
  Info,
  Download,
  ChevronDown,
  ChevronRight,
  Search,
  ShieldCheck,
  BarChart2,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Activity,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import CustomDropdown from "../components/CustomDropdown";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import "./UncertaintyAssessment.css";
import { t } from "../i18n";

interface Contributor {
  name: string;
  uncertainty?: string;
  contribution: number;
}

interface CategorySection {
  category: string;
  total_emissions?: number;
  uncertainty_decimal?: number;
  level: "low" | "medium" | "high" | string;
  uncertainty_pct: string;
  top_contributors: Contributor[];
}

export interface MonteCarloHistogramBin {
  bin: string;
  bin_range: string;
  midpoint: number;
  emissions_tco2e: number;
  count: number;
  frequency: number;
}

export interface MonteCarloData {
  mean: number;
  median: number;
  std: number;
  ci_lower: number;
  ci_upper: number;
  p5: number;
  p95: number;
  relative_uncertainty_95pct: number;
  iterations: number;
  histogram: MonteCarloHistogramBin[];
  percentiles: Record<string, number>;
}

interface UncertaintyData {
  inventory_uncertainty_decimal?: number;
  inventory_uncertainty_pct?: string;
  confidence_level_pct?: number;
  coverage_factor?: number;
  total_inventory_emissions?: number;
  tier_breakdown?: Record<string, number>;
  uncertainty_bands?: Record<string, number>;
  categories: CategorySection[];
  monte_carlo?: MonteCarloData;
  [key: string]: any;
}

interface Facility {
  id?: string | number;
  facility_id?: string | number;
  name?: string;
  facility_name?: string;
  [key: string]: any;
}

const UncertaintyAssessment: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();

  const [data, setData] = useState<UncertaintyData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedYear, setSelectedYear] = useState<string>("all");
  const [selectedScope, setSelectedScope] = useState<string>("all");
  const [selectedFacility, setSelectedFacility] = useState<string>("all");
  const [availableYears, setAvailableYears] = useState<(string | number)[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [exporting, setExporting] = useState<boolean>(false);

  // New UX state
  const [analyticsView, setAnalyticsView] = useState<"relative" | "absolute" | "monte_carlo">("relative");
  const [riskFilter, setRiskFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Load filter options on mount
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const [filterRes, facRes] = await Promise.all([
          api.get("/filters/available"),
          api.get("/facilities"),
        ]);
        if (filterRes.data?.years?.length > 0) {
          setAvailableYears(filterRes.data.years);
          if (selectedYear === "all") {
            setSelectedYear(filterRes.data.years[0].toString());
          }
        } else {
          setLoading(false);
        }
        if (facRes.data) {
          const facList: Facility[] = Array.isArray(facRes.data) ? facRes.data : facRes.data.facilities || [];
          setFacilities(facList);
          const opDefaults = getUserOperationalDefaults(user, facList);
          if (opDefaults.isRestricted && opDefaults.defaultFacilityId) {
            setSelectedFacility(opDefaults.defaultFacilityId);
          }
        }
      } catch (err) {
        console.error("Failed to load filters:", err);
        setLoading(false);
      }
    };
    loadFilters();
  }, [user]);

  // Fetch uncertainty data when filters change
  useEffect(() => {
    if (selectedYear === "all") {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set("year", selectedYear);
        if (selectedScope !== "all") params.set("scope", selectedScope);
        if (selectedFacility !== "all") params.set("facility_id", selectedFacility);

        const res = await api.get(`/dashboard/uncertainty?${params.toString()}`);
        setData(res.data);
      } catch (error) {
        console.error("Failed to load uncertainty data:", error);
        toast.error(t("Failed to load uncertainty data"));
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedYear, selectedScope, selectedFacility]);

  // CSV export handler
  const handleExport = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      params.set("year", selectedYear);
      params.set("export", "csv");
      if (selectedScope !== "all") params.set("scope", selectedScope);
      if (selectedFacility !== "all") params.set("facility_id", selectedFacility);

      const res = await api.get(`/dashboard/uncertainty?${params.toString()}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `uncertainty_${selectedYear}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("Uncertainty assessment exported successfully"));
    } catch (err) {
      console.error("Export failed:", err);
      toast.error(t("Export failed"));
    } finally {
      setExporting(false);
    }
  };

  // Inventory uncertainty level
  const getUncertaintyLevel = (decimal?: number | null) => {
    if (decimal == null) return "";
    if (decimal <= 0.1) return "level-low";
    if (decimal <= 0.3) return "level-medium";
    return "level-high";
  };

  const getUncertaintyLabel = (decimal?: number | null) => {
    if (decimal == null) return "";
    if (decimal <= 0.1) return t("Low Uncertainty (ISO 14064-1 Compliant)");
    if (decimal <= 0.3) return t("Moderate Uncertainty (Monitoring Recommended)");
    return t("High Uncertainty (Priority Action Required)");
  };

  // Toggle category row expand
  const toggleCategoryExpand = (categoryName: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryName)) {
        next.delete(categoryName);
      } else {
        next.add(categoryName);
      }
      return next;
    });
  };

  // Build dropdown options
  const yearOptions = [
    { value: "all", label: t("Select Year") },
    ...availableYears.map((y) => ({ value: y.toString(), label: y.toString() })),
  ];

  const scopeOptions = [
    { value: "all", label: t("All Scopes") },
    { value: "1", label: t("Scope 1") },
    { value: "2", label: t("Scope 2") },
    { value: "3", label: t("Scope 3") },
  ];

  const facilityOptions = [
    { value: "all", label: t("All Facilities") },
    ...facilities.map((f) => ({
      value: (f.id || f.facility_id || "").toString(),
      label: f.name || f.facility_name || `Facility ${f.id}`,
    })),
  ];

  // Filtered categories for the table
  const filteredCategories = useMemo(() => {
    if (!data?.categories) return [];
    return data.categories.filter((cat) => {
      // Risk level filter
      if (riskFilter !== "all" && cat.level !== riskFilter) {
        return false;
      }
      // Search query filter
      if (searchQuery.trim() !== "") {
        const q = searchQuery.toLowerCase();
        const matchesCategory = cat.category.toLowerCase().includes(q);
        const matchesContributor = cat.top_contributors?.some((c) =>
          c.name.toLowerCase().includes(q)
        );
        if (!matchesCategory && !matchesContributor) {
          return false;
        }
      }
      return true;
    });
  }, [data?.categories, riskFilter, searchQuery]);

  // Dynamic height for chart
  const chartDynamicHeight = useMemo(() => {
    const count = data?.categories?.length || 0;
    return Math.max(340, count * 38 + 70);
  }, [data?.categories?.length]);

  if (loading) {
    return (
      <div className="[padding:24px_32px_48px] [max-width:1600px] [margin:0_auto] [color:var(--text-primary,_var(--color-ink-900))]">
        <LoadingSpinner message={t("Quantifying Inventory Uncertainty...")} />
      </div>
    );
  }

  const totalEmissions = data?.total_inventory_emissions || 1;
  const highRiskCount = data?.categories.filter((c) => c.level === "high").length || 0;
  const mediumRiskCount = data?.categories.filter((c) => c.level === "medium").length || 0;
  const lowRiskCount = data?.categories.filter((c) => c.level === "low").length || 0;

  return (
    <div className="[padding:24px_32px_48px] [max-width:1600px] [margin:0_auto] [color:var(--text-primary,_var(--color-ink-900))]">
      {/* ── Page Header ── */}
      <div className="[margin-bottom:28px] [display:flex] [justify-content:space-between] [align-items:flex-end]! [gap:24px] [flex-wrap:wrap]! [@media(max-width:900px)]:[flex-direction:column]! [@media(max-width:900px)]:[align-items:flex-start]!">
        <div>
          <h1 className="ua-title">{t("Data Reliability Analysis")}</h1>
          <p className="[font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-500))] [max-width:850px] [margin:0] [line-height:1.5]">
            {t(
              "Dynamic quantification of GHG inventory uncertainty according to ISO 14064-1 §7.5 and IPCC 2006 Guidelines Vol.1 §3.3."
            )}
          </p>
        </div>

        <div className="[display:flex] [gap:14px] [align-items:flex-end] [flex-wrap:wrap]! [@media(max-width:900px)]:[width:100%]">
          <div className="[display:flex] [flex-direction:column] [gap:6px] w-[130px]!">
            <CustomDropdown
              options={yearOptions}
              value={selectedYear}
              onChange={setSelectedYear}
              placeholder={t("Year")}
            />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:6px] w-[150px]!">
            <CustomDropdown
              options={scopeOptions}
              value={selectedScope}
              onChange={setSelectedScope}
              placeholder={t("Scope")}
            />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:6px] w-[200px]!">
            <CustomDropdown
              options={facilityOptions}
              value={selectedFacility}
              onChange={setSelectedFacility}
              placeholder={t("Facility")}
            />
          </div>

          <button
            className="[display:inline-flex] [align-items:center] [gap:8px] [padding:9px_18px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--bg-card,_var(--color-white))] [color:var(--text-primary,_var(--color-ink-800))] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [transition:all_0.2s_ease] hover:[background:var(--color-primary)] hover:[color:var(--color-white)] hover:[border-color:var(--accent-color,_var(--color-brand-500))] hover:[box-shadow:var(--shadow-card)]"
            onClick={handleExport}
            disabled={exporting || !data}
            title={t("Export uncertainty assessment as CSV")}
          >
            <Download size={15} />
            {exporting ? t("Exporting...") : t("Export CSV")}
          </button>
        </div>
      </div>

      {!data ? (
        <div className="ua-methodology-box mt-[24px]!">
          <Info size={24} className="ua-methodology-icon" />
          <div>
            <h4>{t("No Uncertainty Data Available")}</h4>
            <p>
              {t(
                "No verified emission records found for the selected filters. Ensure emissions have been submitted and verified before running the uncertainty assessment."
              )}
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* ── ZONE 1: Executive Compliance & Data Maturity Hero Banner ── */}
          <div className="ua-hero-card">
            {/* Column A: Global Uncertainty KPI */}
            <div className="ua-hero-col">
              <div>
                <div className="ua-hero-label">
                  <ShieldCheck size={14} className="text-brand-500!" />
                  {t("Global Inventory Uncertainty")}
                </div>
                <div className="ua-hero-kpi-row">
                  <span
                    className={`ua-hero-big-value ${getUncertaintyLevel(
                      data.inventory_uncertainty_decimal
                    )}`}
                  >
                    {data.inventory_uncertainty_pct || "±0.0%"}
                  </span>
                  {data.confidence_level_pct && (
                    <span className="ua-hero-confidence-badge">
                      {data.confidence_level_pct}% IC (k={data.coverage_factor})
                    </span>
                  )}
                </div>
              </div>
              <div className="ua-hero-subtext">
                <div className="[font-weight:700] [color:var(--color-ink-800)]">
                  {getUncertaintyLabel(data.inventory_uncertainty_decimal)}
                </div>
                <div>
                  {t("Total assessed inventory:")}{" "}
                  <strong className="text-ink-900!">
                    {(totalEmissions / 1_000_000).toFixed(2)} M tCO₂e
                  </strong>
                </div>
              </div>
            </div>

            {/* Column B: Scope 1 Tier Maturity */}
            <div className="ua-hero-col">
              <div>
                <div className="ua-hero-label">
                  <Layers size={14} className="text-blue-500!" />
                  {t("Factor Maturity (Scope 1)")}
                </div>
                <div className="ua-stacked-bar-container">
                  <div className="ua-stacked-bar">
                    <div
                      className="ua-stacked-segment tier-3"
                      style={{ width: `${data.tier_breakdown?.["Tier 3"] ?? 0}%` }}
                      title={`Tier 3: ${data.tier_breakdown?.["Tier 3"] ?? 0}%`}
                    />
                    <div
                      className="ua-stacked-segment tier-2"
                      style={{ width: `${data.tier_breakdown?.["Tier 2"] ?? 0}%` }}
                      title={`Tier 2: ${data.tier_breakdown?.["Tier 2"] ?? 0}%`}
                    />
                    <div
                      className="ua-stacked-segment tier-1"
                      style={{ width: `${data.tier_breakdown?.["Tier 1"] ?? 0}%` }}
                      title={`Tier 1: ${data.tier_breakdown?.["Tier 1"] ?? 0}%`}
                    />
                  </div>
                  <div className="ua-stacked-legend">
                    <div className="ua-stacked-legend-row">
                      <span>
                        <span className="ua-legend-dot tier-3" />
                        {t("Tier 3 (Direct Measurement / CEMS)")}
                      </span>
                      <strong className="text-ink-900!">
                        {data.tier_breakdown?.["Tier 3"] ?? 0}%
                      </strong>
                    </div>
                    <div className="ua-stacked-legend-row">
                      <span>
                        <span className="ua-legend-dot tier-2" />
                        {t("Tier 2 (Sonatrach Site-Specific Factors)")}
                      </span>
                      <strong className="text-ink-900!">
                        {data.tier_breakdown?.["Tier 2"] ?? 0}%
                      </strong>
                    </div>
                    <div className="ua-stacked-legend-row">
                      <span>
                        <span className="ua-legend-dot tier-1" />
                        {t("Tier 1 (IPCC Default Factors)")}
                      </span>
                      <strong className="text-ink-900!">
                        {data.tier_breakdown?.["Tier 1"] ?? 0}%
                      </strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Column C: Risk Bands Exposure */}
            <div className="ua-hero-col">
              <div>
                <div className="ua-hero-label">
                  <AlertTriangle size={14} className="text-amber-500!" />
                  {t("Uncertainty Risk Exposure")}
                </div>
                <div className="ua-stacked-bar-container">
                  <div className="ua-stacked-bar">
                    <div
                      className="ua-stacked-segment band-low"
                      style={{ width: `${data.uncertainty_bands?.["low"] ?? 0}%` }}
                      title={`Faible: ${data.uncertainty_bands?.["low"] ?? 0}%`}
                    />
                    <div
                      className="ua-stacked-segment band-medium"
                      style={{ width: `${data.uncertainty_bands?.["medium"] ?? 0}%` }}
                      title={`Moyen: ${data.uncertainty_bands?.["medium"] ?? 0}%`}
                    />
                    <div
                      className="ua-stacked-segment band-high"
                      style={{ width: `${data.uncertainty_bands?.["high"] ?? 0}%` }}
                      title={`Élevé: ${data.uncertainty_bands?.["high"] ?? 0}%`}
                    />
                  </div>
                  <div className="ua-stacked-legend">
                    <div className="ua-stacked-legend-row">
                      <span>
                        <span className="ua-legend-dot band-high" />
                        {t("High (> ±30%)")}
                      </span>
                      <strong className="text-red-700!">
                        {data.uncertainty_bands?.["high"] ?? 0}%
                      </strong>
                    </div>
                    <div className="ua-stacked-legend-row">
                      <span>
                        <span className="ua-legend-dot band-medium" />
                        {t("Moderate (±10% to ±30%)")}
                      </span>
                      <strong className="text-amber-700!">
                        {data.uncertainty_bands?.["medium"] ?? 0}%
                      </strong>
                    </div>
                    <div className="ua-stacked-legend-row">
                      <span>
                        <span className="ua-legend-dot band-low" />
                        {t("Low (≤ ±10%)")}
                      </span>
                      <strong className="text-green-700!">
                        {data.uncertainty_bands?.["low"] ?? 0}%
                      </strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── ZONE 2: Analytics Hub with Segmented Switcher ── */}
          {data.categories.length > 0 && (
            <div className="ua-chart-card">
              <div className="ua-chart-header">
                <div>
                  <h3 className="category-title">
                    {analyticsView === "relative"
                      ? t("Relative Uncertainty by Category (±%)")
                      : analyticsView === "absolute"
                      ? t("Verified Emissions & 95% Margin by Category (tCO₂e)")
                      : t("Empirical Monte Carlo Distribution — Probability Histogram (IPCC Approach 2)")}
                  </h3>
                  <p className="[font-size:var(--text-xs)] [color:var(--text-secondary,_var(--color-ink-500))] [margin:4px_0_0_18px]">
                    {analyticsView === "relative"
                      ? t(
                          "Ranking of categories according to their statistical dispersion relative to the critical threshold of ±30%."
                        )
                      : analyticsView === "absolute"
                      ? t(
                          "Weighting of total emissions by category and absolute uncertainty whiskers."
                        )
                      : t(
                          "Log-normal stochastic simulation (2,500 iterations) illustrating the probability density function and P5/P95 percentiles."
                        )}
                  </p>
                </div>

                {/* Segmented Control Pill Switcher */}
                <div className="ua-segmented-control">
                  <button
                    type="button"
                    id="ua-switch-relative"
                    className={`ua-segmented-btn ${analyticsView === "relative" ? "active" : ""}`}
                    onClick={() => setAnalyticsView("relative")}
                  >
                    <BarChart2 size={13} />
                    {t("Relative Uncertainty (±%)")}
                  </button>
                  <button
                    type="button"
                    id="ua-switch-absolute"
                    className={`ua-segmented-btn ${analyticsView === "absolute" ? "active" : ""}`}
                    onClick={() => setAnalyticsView("absolute")}
                  >
                    <Layers size={13} />
                    {t("Volumetric Impact (tCO₂e)")}
                  </button>
                  <button
                    type="button"
                    id="ua-switch-monte-carlo"
                    className={`ua-segmented-btn ${analyticsView === "monte_carlo" ? "active" : ""}`}
                    onClick={() => setAnalyticsView("monte_carlo")}
                  >
                    <Activity size={13} />
                    {t("Monte Carlo Histogram")}
                  </button>
                </div>
              </div>

              {analyticsView === "monte_carlo" ? (
                <div className="flex flex-col gap-4 w-full" id="ua-monte-carlo-view">
                  {data.monte_carlo && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-ink-50/70 border border-border">
                      <div className="flex flex-col">
                        <span className="text-[11px] font-semibold uppercase text-text-secondary">{t("Simulated Mean")}</span>
                        <span className="text-sm font-bold text-text mt-0.5">{Number(data.monte_carlo.mean).toLocaleString()} tCO₂e</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-semibold uppercase text-text-secondary">{t("Median (P50)")}</span>
                        <span className="text-sm font-bold text-text mt-0.5">{Number(data.monte_carlo.median).toLocaleString()} tCO₂e</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-semibold uppercase text-text-secondary">{t("95% Interval (P5 - P95)")}</span>
                        <span className="text-sm font-bold text-emerald-700 mt-0.5">
                          [{Number(data.monte_carlo.ci_lower).toLocaleString()} - {Number(data.monte_carlo.ci_upper).toLocaleString()}]
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-semibold uppercase text-text-secondary">{t("95% Uncertainty")}</span>
                        <span className="text-sm font-bold text-brand-600 mt-0.5">±{data.monte_carlo.relative_uncertainty_95pct}% ({data.monte_carlo.iterations} runs)</span>
                      </div>
                    </div>
                  )}

                  <div style={{ height: `${chartDynamicHeight}px` }} className="w-full min-w-0" id="ua-monte-carlo-histogram">
                    <BarChart
                      data={
                        data.monte_carlo?.histogram?.map((b) => ({
                          name: `${b.emissions_tco2e}`,
                          count: b.count,
                          range: b.bin_range,
                        })) || []
                      }
                      dataKey="count"
                      xKey="name"
                      color="var(--color-brand-500)"
                      height={chartDynamicHeight}
                      exportName="monte-carlo-histogram"
                      formatValue={(v) => `${v} runs`}
                    />
                  </div>
                </div>
              ) : analyticsView === "relative" ? (
                <div style={{ height: `${chartDynamicHeight}px` }} className="w-full min-w-0">
                  <BarChart
                    data={data.categories.map((c) => {
                      const value =
                        Math.abs(
                          parseFloat(String(c.uncertainty_pct).replace(/[^0-9.\-]/g, ""))
                        ) || 0;
                      const color =
                        value <= 10
                          ? "var(--color-unc-low)"
                          : value <= 30
                          ? "var(--color-unc-medium)"
                          : "var(--color-unc-high)";
                      return { name: c.category, value, color };
                    })}
                    dataKey="value"
                    xKey="name"
                    color="var(--color-unc-high)"
                    horizontal
                    sortDesc
                    height={chartDynamicHeight}
                    referenceValue={30}
                    referenceLabel={t("Critical threshold (±30%)")}
                    exportName="uncertainty-by-category"
                    formatValue={(v) => `±${Number(v).toFixed(1)}%`}
                  />
                </div>
              ) : (
                <div style={{ height: `${chartDynamicHeight}px` }} className="w-full min-w-0">
                  <BarChart
                    data={data.categories.map((c: any) => {
                      const u = Number(c.uncertainty_decimal) || 0;
                      const value = Number(c.total_emissions) || 0;
                      const color =
                        u <= 0.1
                          ? "var(--color-unc-low)"
                          : u <= 0.3
                          ? "var(--color-unc-medium)"
                          : "var(--color-unc-high)";
                      return { name: c.category, value, range: value * u, color };
                    })}
                    dataKey="value"
                    xKey="name"
                    horizontal
                    sortDesc
                    height={chartDynamicHeight}
                    errorKey="range"
                    exportName="emissions-by-category-with-95-range"
                  />
                </div>
              )}
            </div>
          )}

          {/* ── ZONE 3: Interactive Materiality & Reliability Master-Detail Table ── */}
          <div className="ua-table-card">
            <div className="ua-table-toolbar">
              <div className="[display:flex] [align-items:center] [gap:16px] [flex-wrap:wrap]">
                <h3 className="category-title">
                  {t("Reliability Directory & Contributors")}
                </h3>
                {/* Risk filter chips */}
                <div className="ua-filter-chips">
                  <button
                    type="button"
                    className={`ua-chip ${riskFilter === "all" ? "active" : ""}`}
                    onClick={() => setRiskFilter("all")}
                  >
                    {t("Tous")} ({data.categories.length})
                  </button>
                  <button
                    type="button"
                    className={`ua-chip ${riskFilter === "high" ? "active" : ""}`}
                    onClick={() => setRiskFilter("high")}
                  >
                    {t("High Risk (> ±30%)")} ({highRiskCount})
                  </button>
                  <button
                    type="button"
                    className={`ua-chip ${riskFilter === "medium" ? "active" : ""}`}
                    onClick={() => setRiskFilter("medium")}
                  >
                    {t("Moderate (±10% - ±30%)")} ({mediumRiskCount})
                  </button>
                  <button
                    type="button"
                    className={`ua-chip ${riskFilter === "low" ? "active" : ""}`}
                    onClick={() => setRiskFilter("low")}
                  >
                    {t("Low (≤ ±10%)")} ({lowRiskCount})
                  </button>
                </div>
              </div>

              {/* Quick Search */}
              <div className="ua-search-input-wrap">
                <Search
                  size={14}
                  className="[position:absolute] [left:10px] [top:50%] [transform:translateY(-50%)] [color:var(--color-ink-400)]"
                />
                <input
                  type="text"
                  className="ua-search-input"
                  placeholder={t("Search category...")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Table */}
            <div className="ua-table-wrapper">
              <table className="ua-table">
                <thead>
                  <tr>
                    <th className="w-11!"></th>
                    <th>{t("Emission Category")}</th>
                    <th>{t("Verified Emissions (tCO₂e)")}</th>
                    <th>{t("Share of inventory")}</th>
                    <th>{t("Uncertainty (±%)")}</th>
                    <th>{t("Risk Level")}</th>
                    <th>{t("Principal Variance Contributor")}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCategories.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="[text-align:center] [padding:32px] [color:var(--color-ink-500)]">
                        {t("No category matches the applied filters.")}
                      </td>
                    </tr>
                  ) : (
                    filteredCategories.map((cat) => {
                      const isExpanded = expandedCategories.has(cat.category);
                      const sharePct = ((Number(cat.total_emissions) || 0) / totalEmissions) * 100;
                      const topContrib = cat.top_contributors?.[0];

                      return (
                        <React.Fragment key={cat.category}>
                          <tr
                            className={`ua-row-clickable ${isExpanded ? "ua-row-expanded" : ""}`}
                            role="row"
                            tabIndex={0}
                            onClick={() => toggleCategoryExpand(cat.category)}
                            onKeyDown={(e) => {
                              if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                                e.preventDefault();
                                toggleCategoryExpand(cat.category);
                              }
                            }}
                          >
                            <td className="[text-align:center]">
                              {isExpanded ? (
                                <ChevronDown size={16} className="text-brand-500!" />
                              ) : (
                                <ChevronRight size={16} className="text-ink-400!" />
                              )}
                            </td>
                            <td>
                              <span className="[font-weight:700] [color:var(--color-ink-900)]">
                                {cat.category}
                              </span>
                            </td>
                            <td>
                              <span className="[font-family:var(--font-mono)] [font-weight:600]">
                                {Number(cat.total_emissions || 0).toLocaleString("fr-FR", {
                                  maximumFractionDigits: 1,
                                })}
                              </span>
                            </td>
                            <td>
                              <span className="[font-family:var(--font-mono)] [color:var(--color-ink-600)]">
                                {sharePct.toFixed(1)}%
                              </span>
                            </td>
                            <td>
                              <span
                                className={`[display:inline-block] [padding:2px_8px] [border-radius:var(--radius-sm)] [font-weight:700] [font-family:var(--font-mono)] uncertainty-${cat.level}`}
                              >
                                {cat.uncertainty_pct}
                              </span>
                            </td>
                            <td>
                              <span
                                className={`ua-risk-pill uncertainty-${cat.level}`}
                              >
                                {cat.level === "high"
                                  ? t("High (>30%)")
                                  : cat.level === "medium"
                                  ? t("Moderate (10-30%)")
                                  : t("Low (≤10%)")}
                              </span>
                            </td>
                            <td>
                              {topContrib ? (
                                <span className="[font-size:var(--text-xs)] [color:var(--color-ink-700)]">
                                  <strong>{topContrib.name}</strong>{" "}
                                  <span className="[color:var(--color-ink-500)]">
                                    ({topContrib.contribution}%)
                                  </span>
                                </span>
                              ) : (
                                <span className="[color:var(--color-ink-400)]">—</span>
                              )}
                            </td>
                          </tr>

                          {/* Expanded Detail Panel */}
                          {isExpanded && (
                            <tr>
                              <td colSpan={7} className="ua-detail-expanded-cell">
                                <div className="[font-size:var(--text-xs)] [font-weight:700] [text-transform:uppercase] [color:var(--color-ink-500)] [margin-bottom:12px] [letter-spacing:0.04em]">
                                  {t("Key uncertainty drivers for")} : {cat.category}
                                </div>
                                <div className="ua-detail-panel">
                                  {cat.top_contributors?.map((contrib, cIdx) => (
                                    <div key={cIdx} className="ua-contributor-card">
                                      <div className="ua-contributor-header">
                                        <span className="ua-contributor-title">
                                          {contrib.name}
                                        </span>
                                        {contrib.uncertainty && (
                                          <span className="[font-size:var(--text-xs)] [font-weight:700] [padding:2px_6px] [background:var(--color-ink-100)] [border-radius:var(--radius-sm)]">
                                            {contrib.uncertainty}
                                          </span>
                                        )}
                                      </div>
                                      <div className="[display:flex] [justify-content:space-between] [font-size:var(--text-xs)] [color:var(--color-ink-600)]">
                                        <span>{t("Category Weight")}</span>
                                        <strong>{contrib.contribution}%</strong>
                                      </div>
                                      <div className="ua-contributor-bar-bg">
                                        <div
                                          className="ua-contributor-bar-fill"
                                          style={{ width: `${contrib.contribution}%` }}
                                        />
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── ZONE 4: Methodology Footer ── */}
          <div className="ua-methodology-box">
            <Info size={24} className="ua-methodology-icon" />
            <div>
              <h4>{t("Calculation Methodology & ISO 14064-1 Compliance")}</h4>
              <p>
                {t(
                  "Uncertainty is quantified using the quadratic error propagation method (SRSS / Approach 1) per IPCC 2006 Guidelines Vol. 1, Ch. 3 (Eq. 3.3). Expansion factor k=2 is applied in accordance with GUM §6.2 to obtain expanded uncertainty at 95% confidence level. Emission factor uncertainties account for intra-sector correlations (Audit RC-10)."
                )}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default UncertaintyAssessment;
