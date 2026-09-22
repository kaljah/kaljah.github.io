import React, { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { SkeletonCard } from "../components/SkeletonLoader";
import {
  PieChart as PieChartWrapper,
  LineChart as LineChartWrapper,
} from "../components/charts";
import CustomDropdown from "../components/CustomDropdown";
import {
  formatCompactNumber,
  calculateTrend,
} from "../utils/formatters";
import { useLayout } from "../context/LayoutContext";
import { getUserOperationalDefaults, isUnrestrictedLocation } from "../utils/userDefaults";
import {
  ChevronDown,
  ChevronUp,
  Clock,
  Eye,
  EyeOff,
  ArrowRight,
} from "lucide-react";
import "./Dashboard.css";

// Simple Linear Regression for Forecasting
const calculateForecast = (data) => {
  if (data.length < 2) return [];

  const n = data.length;
  let sumX = 0,
    sumY = 0,
    sumXY = 0,
    sumXX = 0;

  data.forEach((p) => {
    sumX += p.year;
    sumY += p.emissions;
    sumXY += p.year * p.emissions;
    sumXX += p.year * p.year;
  });

  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  const lastYear = data[data.length - 1].year;
  const forecast = [];

  // Forecast next 5 years
  for (let i = 1; i <= 5; i++) {
    const year = lastYear + i;
    const emissions = Number((slope * year + intercept).toFixed(2));
    forecast.push({ year, forecast: Math.max(0, emissions) }); // No negative emissions
  }
  return forecast;
};

const DashboardEnhanced = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();

  // Filter states
  const [currentActivity, setCurrentActivity] = useState("all");
  const [currentDivision, setCurrentDivision] = useState("all");
  const [currentRegion, setCurrentRegion] = useState("all");
  const [currentSegment, setCurrentSegment] = useState("all");
  const [facilities, setFacilities] = useState([]);
  const [availableFilters, setAvailableFilters] = useState({
    years: [],
    regions: [],
    segments: [],
  });

  // Data states
  const [stats, setStats] = useState({
    totalEmissions: 0,
    netEmissions: 0,
    scope1: 0,
    scope2: 0,
    scope3: 0,
    mitigation: 0,
    methaneEmissions: 0,
    purchasedEnergy: 0,
    combustion: 0,
    flaring: 0,
    venting: 0,
    other: 0,
  });

  const [sbtiData, setSbtiData] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [categoricalData, setCategoricalData] = useState([]);
  const [currentYear, setCurrentYear] = useState("all");
  const [expandedActivities, setExpandedActivities] = useState({});
  const [expandedDivisions, setExpandedDivisions] = useState({});
  const [goal, setGoal] = useState(null);
  const [intensity, setIntensity] = useState(0);
  const [hasProductionData, setHasProductionData] = useState(true);
  const [loading, setLoading] = useState(true);
  const [isCompareMode, setIsCompareMode] = useState(false);
  const [variance, setVariance] = useState({ emissions: "—", intensity: "—" });
  const [pendingCount, setPendingCount] = useState(0);
  const [pendingCo2e, setPendingCo2e] = useState(0);
  const [includePending, setIncludePending] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  );
  const [categoricalCollapsed, setCategoricalCollapsed] = useState(false);
  const [detailedBreakdownCollapsed, setDetailedBreakdownCollapsed] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);
  const [gwpHorizon, setGwpHorizon] = useState("100"); // "100" (Standard 100-yr) or "20" (Near-term 20-yr)

  const navigate = useNavigate();

  // Load facilities and available filters
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [facRes, filterRes] = await Promise.all([
          api.get("/facilities"),
          api.get("/filters/available"),
        ]);
        const facilitiesData = Array.isArray(facRes.data)
          ? facRes.data
          : facRes.data?.data || [];
        setFacilities(facilitiesData);
        setAvailableFilters({
          years: Array.isArray(filterRes.data?.years)
            ? filterRes.data.years
            : [],
          regions: Array.isArray(filterRes.data?.regions)
            ? filterRes.data.regions
            : [],
          segments: Array.isArray(filterRes.data?.segments)
            ? filterRes.data.segments
            : [],
        });

        const opDefaults = getUserOperationalDefaults(user, facilitiesData);
        if (opDefaults.isRestricted || facilitiesData.length === 1) {
          if (opDefaults.defaultActivity) setCurrentActivity(opDefaults.defaultActivity);
          if (opDefaults.defaultDivision) setCurrentDivision(opDefaults.defaultDivision);
          if (opDefaults.defaultFacilityId) setCurrentRegion(opDefaults.defaultFacilityId);
        }
      } catch (error) {
        console.error("Failed to load initial data:", error);
      }
    };
    loadInitialData();
  }, [user]);

  const [isUpdating, setIsUpdating] = useState(false);
  const isFirstLoadRef = useRef(true);

  // Load dashboard data
  useEffect(() => {
    loadDashboardData();
  }, [
    currentActivity,
    currentDivision,
    currentRegion,
    currentYear,
    currentSegment,
    isCompareMode,
    includePending,
    gwpHorizon,
  ]);

  const loadDashboardData = async () => {
    try {
      if (isFirstLoadRef.current) {
        setLoading(true);
      } else {
        setIsUpdating(true);
      }
      const queryParams = {
        facilityId: currentRegion,
        activity: currentActivity,
        division: currentDivision,
      };
      if (currentSegment !== "all") {
        queryParams.segment = currentSegment;
      }
      if (isCompareMode) {
        queryParams.groupBy = "facility";
      }

      const filterParams = new URLSearchParams(queryParams);
      if (currentYear !== "all") {
        filterParams.append("year", currentYear);
      }
      if (includePending) {
        filterParams.append("includePending", "true");
      }
      if (gwpHorizon && gwpHorizon !== "100") {
        filterParams.append("gwp_horizon", gwpHorizon);
      }

      // Part 3: Optimized Batch Dashboard API Call
      const batchRes = await api.get(`/dashboard/batch-all?${filterParams}`);
      const batch = batchRes.data;

      if (batch.pending_stats) {
        setPendingCount(batch.pending_stats.count || 0);
        setPendingCo2e(batch.pending_stats.totalCo2e || 0);
      } else if (['admin', 'superuser'].includes(user?.role)) {
        try {
          const pRes = await api.get('/emissions/pending');
          setPendingCount(pRes.data.total_pending || 0);
        } catch (e) { console.error(e); }
      }

      const summaryData = batch.summary || [];
      const mitData = batch.mitigation || [];
      const s3Data = batch.scope3_summary || { total: 0 };
      const catData = batch.categorical_breakdown || [];
      const intensityData = batch.intensity_stats || [];
      const gObj = batch.goal;
      const bYearObj = batch.base_year;

      setGoal(gObj);
      setCategoricalData(catData);

      // Fetch SBTi Trajectory Data
      try {
        const sbtiRes = await api.get('/dashboard/sbti-trajectory');
        if (sbtiRes.data && sbtiRes.data.has_target) {
            setSbtiData(sbtiRes.data);
        } else {
            setSbtiData(null);
        }
      } catch (err) {
        console.error("Failed to load SBTi data", err);
      }


      let totals = {
        totalEmissions: 0,
        scope1: 0,
        scope2: 0,
        // BUG-UI-04 FIX: Apply year filter to Scope 3 just like Scope 1 & 2
        scope3:
          currentYear === "all"
            ? (s3Data.total || 0)
            : (s3Data.by_year?.[currentYear] ??
              s3Data.by_year?.[parseInt(currentYear)] ??
              0),
        mitigation: 0,
        methaneEmissions: 0,
        purchasedEnergy: 0,
        combustion: 0,
        flaring: 0,
        venting: 0,
        other: 0,
        totalProductionBoe: 0,
      };

      const yearlyTrend = {};
      const facilityNames = {};
      if (isCompareMode) {
        facilities.forEach((f) => {
          facilityNames[f.id] = f.name;
        });
      }

      summaryData.forEach((row) => {
        const year = row.year;
        const fid = row.facility_id || "total";
        const s1 = row.scope1_total || 0;
        const s2 = row.scope2_total || 0;
        const total = s1 + s2;

        // Handle Totals for Hero Card (Only if matches filter)
        // BUG FIX: Unconditionally aggregate totals so that Compare Mode correctly sums the selected regions,
        // instead of keeping totals at 0.
        if (currentYear === "all" || year.toString() === currentYear) {
          totals.scope1 += s1;
          totals.scope2 += s2;
          totals.totalEmissions += total;
          totals.combustion += row.combustion || 0;
          totals.flaring += row.flaring || 0;
          totals.venting += row.venting || 0;
          totals.other += row.other || 0;
          totals.methaneEmissions += row.ch4_total || 0;
          totals.purchasedEnergy += (row.scope2_energy || 0) / 1000;
        }

        // Handle Trend Data (Aggregate/Comparison)
        if (!yearlyTrend[year]) {
          yearlyTrend[year] = { year: Number(year) };
        }

        if (isCompareMode && fid !== "total") {
          const name = facilityNames[fid] || `Facility ${fid}`;
          yearlyTrend[year][name] = Number(
            ((yearlyTrend[year][name] || 0) + total).toFixed(2),
          );
        } else if (!isCompareMode && fid === "total") {
          yearlyTrend[year].emissions = Number(
            ((yearlyTrend[year].emissions || 0) + total).toFixed(3),
          );
          yearlyTrend[year].scope1 = Number(
            ((yearlyTrend[year].scope1 || 0) + s1).toFixed(3),
          );
          yearlyTrend[year].scope2 = Number(
            ((yearlyTrend[year].scope2 || 0) + s2).toFixed(3),
          );
        }
      });

      mitData.forEach((item) => {
        if (currentYear === "all" || item.year.toString() === currentYear) {
          totals.mitigation += item.quantity_tco2e || 0;
        }
      });

      totals.netEmissions = totals.totalEmissions - totals.mitigation;

      // Weighted Intensity Calculation
      let weightedIntensity = 0;
      let hasProd = false;
      if (intensityData && intensityData.length > 0) {
        let totalEmissionsForIntensity = 0;
        let totalBoeForIntensity = 0;
        intensityData.forEach((d) => {
          if (d.total_boe > 0) {
            const intVal =
              gwpHorizon === "20" && d.co2_intensity_gwp20 != null
                ? d.co2_intensity_gwp20
                : d.co2_intensity;
            totalEmissionsForIntensity += intVal * d.total_boe;
            totalBoeForIntensity += d.total_boe;
          }
        });
        if (totalBoeForIntensity > 0) {
          weightedIntensity = totalEmissionsForIntensity / totalBoeForIntensity;
          hasProd = true;
        }
      }
      setIntensity(weightedIntensity);
      setHasProductionData(hasProd);

      // Prior Year Weighted Intensity Calculation for YoY Trend
      let pyIntensity = 0;
      let pyHasProd = false;
      const intensityPyData = batch.intensity_stats_py || [];
      if (intensityPyData && intensityPyData.length > 0) {
        let totalEmissionsForPy = 0;
        let totalBoeForPy = 0;
        intensityPyData.forEach((d) => {
          if (d.total_boe > 0) {
            const intVal =
              gwpHorizon === "20" && d.co2_intensity_gwp20 != null
                ? d.co2_intensity_gwp20
                : d.co2_intensity;
            totalEmissionsForPy += intVal * d.total_boe;
            totalBoeForPy += d.total_boe;
          }
        });
        if (totalBoeForPy > 0) {
          pyIntensity = totalEmissionsForPy / totalBoeForPy;
          pyHasProd = true;
        }
      }

      // YoY Variance Calculation
      if (currentYear !== "all") {
        const cy = parseInt(currentYear);
        const py = cy - 1;

        // BUG FIX: Calculate aggregate emissions dynamically from summaryData to support Compare Mode
        // because yearlyTrend uses facility names instead of 'emissions' key when in Compare Mode.
        let cyEmissions = 0,
          pyEmissions = 0;
        summaryData.forEach((row) => {
          const total = (row.scope1_total || 0) + (row.scope2_total || 0);
          if (row.year === cy) cyEmissions += total;
          if (row.year === py) pyEmissions += total;
        });

        const emissionsVariance = pyEmissions > 0 ? calculateTrend(cyEmissions, pyEmissions) : "—";
        const intensityVariance =
          hasProd && pyHasProd && pyIntensity > 0
            ? calculateTrend(weightedIntensity, pyIntensity)
            : "—";

        setVariance({
          emissions: emissionsVariance,
          intensity: intensityVariance,
        });
      } else {
        setVariance({ emissions: "—", intensity: "—" });
      }

      // Target Trajectory Calculation
      let trendArray = Object.values(yearlyTrend).sort(
        (a, b) => a.year - b.year,
      );

      if (gObj && bYearObj && !isCompareMode) {
        const baseEmissions =
          yearlyTrend[bYearObj.year]?.emissions ||
          trendArray[0]?.emissions ||
          0;
        const startYear = bYearObj.year;
        const endYear = gObj.year;
        const targetVal = gObj.target_amount;

        // Pad trendArray with future years up to endYear if needed
        const lastYearWithData =
          trendArray.length > 0
            ? trendArray[trendArray.length - 1].year
            : startYear;
        if (endYear > lastYearWithData) {
          for (let y = lastYearWithData + 1; y <= endYear; y++) {
            // Check if year already exists (e.g. from forecast)
            if (!trendArray.find((t) => t.year === y)) {
              trendArray.push({ year: y });
            }
          }
        }

        // Sort again to be sure
        trendArray.sort((a, b) => a.year - b.year);

        trendArray.forEach((point) => {
          if (point.year >= startYear && point.year <= endYear) {
            const progress = (point.year - startYear) / (endYear - startYear);
            point.trajectory = Number(
              (baseEmissions + (targetVal - baseEmissions) * progress).toFixed(
                2,
              ),
            );
          }
        });
      }

      // FORECAST LOGIC (Only in standard view, if no goals or even with goals?)
      // Let's add forecast if we have > 1 year of data and NOT in compare mode
      if (!isCompareMode) {
        const historicalData = trendArray
          .filter((d) => d.emissions !== undefined)
          .map((d) => ({ year: d.year, emissions: d.emissions }));
        const forecastPoints = calculateForecast(historicalData);

        // Merge forecast into trendArray
        forecastPoints.forEach((fp) => {
          const existing = trendArray.find((t) => t.year === fp.year);
          if (existing) {
            existing.forecast = fp.forecast;
          } else {
            trendArray.push(fp);
          }
        });
        trendArray.sort((a, b) => a.year - b.year);
      }

      if (bYearObj && yearlyTrend[bYearObj.year]) {
        bYearObj.value = yearlyTrend[bYearObj.year].emissions;
      }

      setStats(totals);
      setTrendData(trendArray);
      setLastUpdated(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
    } catch (error) {
      console.error("Dashboard load error:", error);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
      setIsUpdating(false);
      isFirstLoadRef.current = false;
    }
  };

  const getSegmentOptions = () => {
    const segments = availableFilters.segments || [];
    return [
      { value: "all", label: "All Supply Chains" },
      ...segments.map((s) => ({ value: s, label: s })),
    ];
  };

  const getActivityOptions = () => {
    const filtered = facilities.filter(
      (f) => currentSegment === "all" || f.segment === currentSegment,
    );
    const activities = new Set(filtered.map((f) => f.activity).filter(Boolean));
    return [
      { value: "all", label: "All Activities" },
      ...Array.from(activities)
        .sort()
        .map((a) => ({ value: a, label: formatActivityName(a) })),
    ];
  };

  const getDivisionOptions = () => {
    let divisionsSet = new Set();
    const filtered = facilities.filter(
      (f) =>
        (currentSegment === "all" || f.segment === currentSegment) &&
        (currentActivity === "all" || f.activity === currentActivity),
    );
    filtered.forEach((f) => { if (f.division) divisionsSet.add(f.division); });
    return [
      { value: "all", label: "All Divisions" },
      ...Array.from(divisionsSet)
        .sort()
        .map((d) => ({ value: d, label: d })),
    ];
  };

  const getRegionOptions = () => {
    const filtered = facilities.filter(
      (f) =>
        (currentSegment === "all" || f.segment === currentSegment) &&
        (currentActivity === "all" || f.activity === currentActivity) &&
        (currentDivision === "all" || f.division === currentDivision),
    );
    return [
      { value: "all", label: "All Regions" },
      ...filtered.map((f) => ({
        value: f.id.toString(),
        label: f.name,
        subLabel: f.field,
      })),
    ];
  };


  const getYearOptions = () => {
    return [
      { value: "all", label: "All Years" },
      ...availableFilters.years
        .sort((a, b) => b - a)
        .map((y) => ({ value: y.toString(), label: y.toString() })),
    ];
  };

  const handleSegmentChange = (value) => {
    setCurrentSegment(value);
    setCurrentActivity("all");
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleActivityChange = (value) => {
    setCurrentActivity(value);
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleDivisionChange = (value) => {
    setCurrentDivision(value);
    setCurrentRegion("all");
  };

  const sourceChartData = useMemo(
    () =>
      [
        // BUG-UI-05 FIX: Guard with ?? 0 to prevent .toFixed() on undefined when stats update fails
        {
          name: "Combustion",
          value: Number((stats.combustion ?? 0).toFixed(2)),
          color: "#10b981",
        },
        {
          name: "Flaring",
          value: Number((stats.flaring ?? 0).toFixed(2)),
          color: "#ff6600",
        },
        {
          name: "Venting",
          value: Number((stats.venting ?? 0).toFixed(2)),
          color: "#f59e0b",
        },
        {
          name: "Other",
          value: Number((stats.other ?? 0).toFixed(2)),
          color: "#3b82f6",
        },
      ].filter((d) => d.value > 0),
    [stats],
  );

  // Helper to map DB activity acronyms to readable legends
  const formatActivityName = (act) => {
    if (!act) return "Other";
    const lower = act.toLowerCase().trim();
    if (lower === "ep" || lower === "e&p" || lower.includes("e&p"))
      return "E&P (Upstream)";
    if (lower === "lqs" || lower.includes("lqs")) return "LQS (Liquefaction)";
    if (lower === "rpc" || lower.includes("rpc")) return "RPC (Refining)";
    if (lower === "trc" || lower.includes("trc")) return "TRC (Transport)";
    return act;
  };

  // Palette: one distinct color per activity
  const ACTIVITY_PALETTE = [
    "#f59e0b",
    "#3b82f6",
    "#10b981",
    "#6366f1",
    "#ef4444",
    "#ec4899",
    "#14b8a6",
    "#a855f7",
  ];
  const ACTIVITY_COLOR_MAP = {
    "E&P (Upstream)": "#f59e0b", // amber
    "LQS (Liquefaction)": "#3b82f6", // blue
    "RPC (Refining)": "#10b981", // green
    "TRC (Transport)": "#6366f1", // indigo
  };

  const activityChartData = useMemo(() => {
    const acting = {};
    categoricalData.forEach((item) => {
      const act = formatActivityName(item.activity);
      acting[act] = (acting[act] || 0) + (item.total_emissions || 0);
    });
    const entries = Object.entries(acting)
      .map(([name, value]) => ({ name, value: Number(value.toFixed(2)) }))
      .filter((d) => d.value > 0);

    return entries.map((entry, index) => {
      return {
        ...entry,
        color:
          ACTIVITY_COLOR_MAP[entry.name] ||
          ACTIVITY_PALETTE[index % ACTIVITY_PALETTE.length],
      };
    });
  }, [categoricalData]);

  // Set TopBar content
  useEffect(() => {
    setTopBarLeft(
      <div className="dashboard-filters">
        <div className="filter-wrapper">
          <CustomDropdown
            options={getYearOptions()}
            value={currentYear}
            onChange={setCurrentYear}
            placeholder="Year"
          />
        </div>
        <div className="filter-wrapper">
          <CustomDropdown
            options={getSegmentOptions()}
            value={currentSegment}
            onChange={handleSegmentChange}
            placeholder="Supply Chain"
          />
        </div>
        <div className="filter-wrapper">
          <CustomDropdown
            options={getActivityOptions()}
            value={currentActivity}
            onChange={handleActivityChange}
            placeholder="Activity"
          />
        </div>
        <div className="filter-wrapper">
          <CustomDropdown
            options={getDivisionOptions()}
            value={currentDivision}
            onChange={handleDivisionChange}
            placeholder="Division"
          />
        </div>
        <div className="filter-wrapper">
          <CustomDropdown
            options={getRegionOptions()}
            value={currentRegion}
            onChange={setCurrentRegion}
            placeholder="Region"
          />
        </div>
      </div>
    );

    setTopBarRight(
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {/* Dual GWP Horizon Toggle */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            background: "var(--bg-card, rgba(255, 255, 255, 0.08))",
            borderRadius: "8px",
            padding: "2px",
            border: "1px solid var(--border-color, rgba(226, 232, 240, 0.8))",
          }}
          title="Global Warming Potential Horizon: 100-Year (Standard, CH4=28) vs 20-Year (Near-term, CH4=84 per IPCC AR5/AR6)"
        >
          <button
            type="button"
            style={{
              padding: "4px 8px",
              fontSize: "0.75rem",
              fontWeight: 600,
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              background: gwpHorizon === "100" ? "var(--accent-color, #ff6600)" : "transparent",
              color: gwpHorizon === "100" ? "#fff" : "var(--text-secondary)",
              transition: "all 0.15s ease",
            }}
            onClick={() => setGwpHorizon("100")}
          >
            GWP-100
          </button>
          <button
            type="button"
            style={{
              padding: "4px 8px",
              fontSize: "0.75rem",
              fontWeight: 600,
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              background: gwpHorizon === "20" ? "#ef4444" : "transparent",
              color: gwpHorizon === "20" ? "#fff" : "var(--text-secondary)",
              transition: "all 0.15s ease",
            }}
            onClick={() => setGwpHorizon("20")}
          >
            GWP-20
          </button>
        </div>

        {goal ? (
          <div className="topbar-goal-badge">
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Target {goal.year}: <strong style={{ color: "var(--text-primary)" }}>{Number(goal.target_amount).toLocaleString()} tCO₂e</strong>
            </span>
            <button
              className="btn-target-action"
              onClick={() => navigate("/manage-data", { state: { tab: "goals" } })}
              title="Manage emission goals and base years in Manage Data"
            >
              Edit Target
            </button>
          </div>
        ) : (
          <button
            className="btn-target-action"
            onClick={() => navigate("/manage-data", { state: { tab: "goals" } })}
            title="Set emission targets in Manage Data"
          >
            + Set Target
          </button>
        )}
      </div>
    );

    return () => {
      setTopBarLeft(null);
      setTopBarRight(null);
    };
  }, [
    currentActivity,
    currentDivision,
    currentRegion,
    currentYear,
    currentSegment,
    facilities,
    goal,
    navigate,
    setTopBarLeft,
    setTopBarRight,
    gwpHorizon,
  ]);

  const toggleActivity = (act) => {
    setExpandedActivities((prev) => ({ ...prev, [act]: !prev[act] }));
  };

  const toggleDivision = (div) => {
    setExpandedDivisions((prev) => ({ ...prev, [div]: !prev[div] }));
  };

  const getHierarchicalData = useMemo(() => {
    const hierarchy = {};
    categoricalData.forEach((item) => {
      const act = item.activity || "Unassigned";
      const div = item.division || "Unknown";
      if (!hierarchy[act]) hierarchy[act] = { total: 0, divisions: {} };
      if (!hierarchy[act].divisions[div])
        hierarchy[act].divisions[div] = { total: 0, regions: [] };
      hierarchy[act].total += item.total_emissions;
      hierarchy[act].divisions[div].total += item.total_emissions;
      hierarchy[act].divisions[div].regions.push(item);
    });
    return hierarchy;
  }, [categoricalData]);

  const handleExportPDF = async () => {
    try {
      setExportingPDF(true);
      toast.info("Generating executive brief PDF...");
      const { generateModernPDF } = await import("../utils/ModernReportGenerator");
      await generateModernPDF(api, {
        year: currentYear !== "all" ? currentYear : undefined,
        regionId: currentRegion !== "all" ? currentRegion : undefined,
        scope: "all",
      });
      toast.success("Executive brief PDF generated successfully!");
    } catch (err) {
      console.error("PDF generation failed:", err);
      toast.error("Failed to generate PDF report. Opening print dialog.");
      window.print();
    } finally {
      setExportingPDF(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading Dashboard Data..." fullScreen />;
  }

  return (
    <div
      className="dashboard-content"
      style={{
        opacity: isUpdating ? 0.8 : 1,
        transition: "opacity 0.15s ease",
      }}
    >
      <div className="dashboard-grid">
        <div className="dashboard-header-row">
          <h1 className="grid-title">GHG Emissions Dashboard</h1>
          <div className="live-badge">
            <div className={`pulse-dot ${isUpdating ? "updating" : ""}`}></div>
            {isUpdating ? "Syncing filters..." : `Live Content • Updated ${lastUpdated}`}
          </div>
        </div>

        {pendingCount > 0 && (
          <div className={`pending-banner-card ${includePending ? "active-preview" : ""}`}>
            <div className="pending-banner-left">
              <div className="pending-banner-icon">
                <Clock size={20} />
              </div>
              <div className="pending-banner-info">
                <div className="pending-banner-header">
                  <h3 className="pending-banner-title">
                    {includePending
                      ? "Previewing Pending & Verified Emissions"
                      : "Pending Records Awaiting Review"}
                  </h3>
                  <span className={`pending-badge ${includePending ? "active-preview-badge" : ""}`}>
                    {includePending ? "Live Preview Active" : "Pending Approval"}
                  </span>
                </div>
                <p className="pending-banner-desc">
                  There are <strong>{pendingCount.toLocaleString()}</strong> emission records
                  {pendingCo2e > 0 && (
                    <span className="pending-co2e-highlight">
                      {pendingCo2e.toLocaleString()} tCO₂e
                    </span>
                  )}
                  pending approval.
                  {!includePending
                    ? " Official metrics currently display verified records only."
                    : " Dashboard metrics now combine pending drafts and verified records."}
                </p>
              </div>
            </div>

            <div className="pending-banner-actions">
              <label
                className="pending-toggle-wrapper"
                title="Toggle pending emissions preview"
              >
                <span className="pending-toggle-label">
                  {includePending ? <Eye size={15} /> : <EyeOff size={15} />}
                  <span>Preview Pending Data</span>
                </span>
                <div className={`pending-switch ${includePending ? "active" : ""}`}>
                  <input
                    type="checkbox"
                    checked={includePending}
                    onChange={(e) => setIncludePending(e.target.checked)}
                    className="pending-switch-input"
                  />
                  <span className="pending-switch-slider" />
                </div>
              </label>

              {['admin', 'superuser'].includes(user?.role) && (
                <button
                  type="button"
                  className="pending-review-btn"
                  onClick={() => navigate('/manage-data', { state: { tab: 'pending' } })}
                  title="Go to Manage Data to review pending records"
                >
                  <span>Review Now</span>
                  <ArrowRight size={14} />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Zero-Data Quick Start Onboarding Card */}
        {!loading && stats.totalEmissions === 0 && stats.netEmissions === 0 && stats.scope3 === 0 && trendData.length === 0 && (
          <div
            className="card glass-panel"
            style={{
              background: "linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%)",
              border: "1px solid rgba(16, 185, 129, 0.2)",
              borderRadius: "12px",
              padding: "24px",
              marginBottom: "24px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
              <div
                style={{
                  background: "#10b981",
                  color: "#fff",
                  borderRadius: "8px",
                  width: "36px",
                  height: "36px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "1.2rem",
                }}
              >
                ✦
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.1rem", color: "var(--text-primary)" }}>
                  Welcome to Antigravity GHG Inventory
                </h3>
                <p style={{ margin: "2px 0 0 0", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                  Your emissions workspace is initialized. Follow this 4-step workflow to establish your inventory:
                </p>
              </div>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "14px",
              }}
            >
              <div
                style={{
                  background: "var(--bg-card, rgba(255, 255, 255, 0.05))",
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                  padding: "14px",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#10b981", textTransform: "uppercase" }}>
                  Step 1 • Facilities
                </div>
                <h4 style={{ margin: "6px 0 4px 0", fontSize: "0.95rem" }}>Set Boundaries</h4>
                <p style={{ margin: "0 0 10px 0", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  Define production facilities, segments, and operational control.
                </p>
                <button
                  className="btn-secondary-unified"
                  style={{ fontSize: "0.75rem", padding: "4px 10px", width: "100%" }}
                  onClick={() => navigate("/manage-data")}
                >
                  Manage Facilities →
                </button>
              </div>
              <div
                style={{
                  background: "var(--bg-card, rgba(255, 255, 255, 0.05))",
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                  padding: "14px",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#3b82f6", textTransform: "uppercase" }}>
                  Step 2 • Ingestion
                </div>
                <h4 style={{ margin: "6px 0 4px 0", fontSize: "0.95rem" }}>Log Activity Data</h4>
                <p style={{ margin: "0 0 10px 0", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  Import Scope 1 fuel, Scope 2 electricity, or Scope 3 supply chain CSVs.
                </p>
                <button
                  className="btn-secondary-unified"
                  style={{ fontSize: "0.75rem", padding: "4px 10px", width: "100%" }}
                  onClick={() => navigate("/emissions")}
                >
                  Enter Emissions →
                </button>
              </div>
              <div
                style={{
                  background: "var(--bg-card, rgba(255, 255, 255, 0.05))",
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                  padding: "14px",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase" }}>
                  Step 3 • Verification
                </div>
                <h4 style={{ margin: "6px 0 4px 0", fontSize: "0.95rem" }}>QA/QC & Approvals</h4>
                <p style={{ margin: "0 0 10px 0", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  Maker-checker dual approval and anomaly outlier resolution.
                </p>
                <button
                  className="btn-secondary-unified"
                  style={{ fontSize: "0.75rem", padding: "4px 10px", width: "100%" }}
                  onClick={() => navigate("/qa-dashboard")}
                >
                  QA/QC Console →
                </button>
              </div>
              <div
                style={{
                  background: "var(--bg-card, rgba(255, 255, 255, 0.05))",
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                  padding: "14px",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#8b5cf6", textTransform: "uppercase" }}>
                  Step 4 • Compliance
                </div>
                <h4 style={{ margin: "6px 0 4px 0", fontSize: "0.95rem" }}>Generate Reports</h4>
                <p style={{ margin: "0 0 10px 0", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                  Export OGMP 2.0 Gold Standard and GHG Protocol disclosures.
                </p>
                <button
                  className="btn-secondary-unified"
                  style={{ fontSize: "0.75rem", padding: "4px 10px", width: "100%" }}
                  onClick={() => navigate("/reports")}
                >
                  View Reports →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Hero Overview Card */}
        <div className="card hero-card glass-panel">
          <div className="hero-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 className="hero-title">Emissions Overview</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="location-badge">
                {currentRegion !== "all"
                  ? facilities.find((f) => f.id.toString() === currentRegion)
                      ?.name || "Region"
                  : currentDivision !== "all"
                    ? currentDivision
                    : currentActivity !== "all"
                      ? currentActivity
                      : "All Regions"}
              </div>
              <button
                onClick={handleExportPDF}
                disabled={exportingPDF}
                className="btn-secondary-unified"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.9)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: exportingPDF ? 'not-allowed' : 'pointer',
                  color: 'var(--text-primary)',
                  opacity: exportingPDF ? 0.7 : 1,
                }}
                title="Export multi-page executive summary PDF"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                  <path d="M6 14h12v8H6z" />
                </svg>
                {exportingPDF ? "Generating PDF..." : "Export Executive Brief (PDF)"}
              </button>
            </div>
          </div>

          <div className="hero-stats-grid">
            <div className="stat-item">
              <div className="stat-label">Gross Operational Emissions (Scope 1+2)</div>
              <div className="stat-value-row">
                <div className="stat-value">
                  {formatCompactNumber(stats.totalEmissions)}
                </div>
                <span className="stat-unit">tCO₂e</span>
                {currentYear !== "all" && variance.emissions !== "—" && (
                  <span
                    className={`variance-badge ${variance.emissions.startsWith("+") ? "danger" : "success"}`}
                  >
                    {variance.emissions}
                  </span>
                )}
              </div>
              {goal && goal.target_amount > 0 && (
                <div className="stat-sublabel" style={{ marginTop: "8px" }}>
                  <span
                    className={`goal-progress-badge ${
                      stats.totalEmissions / goal.target_amount > 1
                        ? "danger"
                        : stats.totalEmissions / goal.target_amount > 0.9
                          ? "warning"
                          : "normal"
                    }`}
                  >
                    {(
                      (stats.totalEmissions / goal.target_amount) *
                      100
                    ).toFixed(1)}
                    % GOAL
                  </span>
                </div>
              )}
            </div>

            <div className="stat-item border-left">
              <div className="stat-label">Net Emissions</div>
              <div className="stat-value-row">
                <div className="stat-value success">
                  {formatCompactNumber(stats.netEmissions)}
                </div>
                <span className="stat-unit">tCO₂e</span>
              </div>
              <div className="stat-sublabel">
                Less{" "}
                <span className="success-text">
                  {formatCompactNumber(stats.mitigation)}
                </span>{" "}
                Mitigation
              </div>
            </div>

            <div className="stat-item border-left">
              <div className="stat-label">Total CH4 (Methane)</div>
              <div className="stat-value-row">
                <div className="stat-value warning">
                  {formatCompactNumber(stats.methaneEmissions)}
                </div>
                <span className="stat-unit">tCH₄</span>
              </div>
            </div>

            <div className="stat-item border-left">
              <div className="stat-label">Performance Intensity</div>
              <div className="stat-value-row">
                <div
                  className="stat-value"
                  style={{
                    color: !hasProductionData && stats.totalEmissions > 0 ? "#f59e0b" : "#8b5cf6",
                    fontSize: !hasProductionData && stats.totalEmissions > 0 ? "1.25rem" : undefined,
                  }}
                >
                  {!hasProductionData && stats.totalEmissions > 0 ? "Pending" : formatCompactNumber(intensity, 2)}
                </div>
                <span className="stat-unit">
                  {!hasProductionData && stats.totalEmissions > 0 ? "Production" : "kg/BOE"}
                </span>
                {currentYear !== "all" && variance.intensity !== "—" && hasProductionData && (
                  <span
                    className={`variance-badge ${variance.intensity.startsWith("+") ? "danger" : "success"}`}
                  >
                    {variance.intensity}
                  </span>
                )}
              </div>
              <div className="stat-sublabel">
                {!hasProductionData && stats.totalEmissions > 0 ? (
                  <span style={{ color: "#d97706", fontWeight: 600 }}>Production figures required</span>
                ) : (
                  "CO₂e Intensity (Scope 1+2)"
                )}
              </div>
            </div>
          </div>

          <div className="scope-pills-row">
            <div className="scope-pill scope-1">
              <span className="pill-label">Scope 1 (Direct)</span>
              <span className="pill-value">
                {formatCompactNumber(stats.scope1)} tCO₂e
              </span>
            </div>
            <div className="scope-pill scope-2">
              <span className="pill-label">Scope 2 (Indirect)</span>
              <span className="pill-value">
                {formatCompactNumber(stats.scope2)} tCO₂e
              </span>
            </div>
            <div className="scope-pill scope-3">
              <span className="pill-label">Scope 3 (Supply Chain)</span>
              <span className="pill-value">
                {formatCompactNumber(stats.scope3)} tCO₂e
              </span>
            </div>
          </div>
        </div>

        {/* --- Primary Analytics Grid: Trend Line (2fr) + Donuts (1fr) --- */}
        <div className="charts-section">
          {/* Trend Chart */}
          <div className="card trend-card-enhanced glass-panel">
            <div className="card-header-row">
              <div>
                <h3 className="card-title">Emissions Trend & Projection</h3>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Historical inventory trajectory with 5-year predictive forecast
                </p>
              </div>
              <div className="card-header-actions">
                <button
                  className={`compare-toggle-btn ${isCompareMode ? "active" : ""}`}
                  onClick={() => setIsCompareMode(!isCompareMode)}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M18 20V10M12 20V4M6 20v-6" />
                  </svg>
                  {isCompareMode ? "Standard View" : "Compare Regions"}
                </button>
              </div>
            </div>
            <div
              className="chart-container"
              style={{
                height: "360px",
                width: "100%",
                minWidth: 0,
                position: "relative",
              }}
            >
              <LineChartWrapper
                data={trendData}
                xKey="year"
                lines={
                  isCompareMode
                    ? Object.keys(trendData[0] || {})
                        .filter((k) => k !== "year" && k !== "trajectory")
                        .map((k, i) => ({
                          dataKey: k,
                          name: k,
                          color: `hsl(${(i * 137.5) % 360}, 70%, 60%)`,
                        }))
                    : [
                        {
                          dataKey: "emissions",
                          name: "Total Emissions",
                          color: "#ff6600",
                        },
                        {
                          dataKey: "scope1",
                          name: "Scope 1",
                          color: "#3b82f6",
                        },
                        {
                          dataKey: "trajectory",
                          name: "Target Path",
                          color: "#10b981",
                          strokeDasharray: "5 5",
                        },
                        {
                          dataKey: "forecast",
                          name: "Forecast",
                          color: "#8b5cf6",
                          strokeDasharray: "3 3",
                        },
                      ]
                }
                height={360}
              />
            </div>
          </div>

          {/* Donut Charts Column (1fr) */}
          <div className="donuts-row">
            <div className="card donut-card-enhanced glass-panel">
              <div className="donut-header">
                <h3 className="donut-title activity">Emissions by Activity</h3>
              </div>
              <div
                className="chart-container"
                style={{
                  height: "170px",
                  width: "100%",
                  minWidth: 0,
                  position: "relative",
                }}
              >
                <PieChartWrapper
                  data={activityChartData}
                  height={170}
                  innerRadius={50}
                  outerRadius={75}
                />
              </div>
            </div>
            <div className="card donut-card-enhanced glass-panel">
              <div className="donut-header">
                <h3 className="donut-title source">Emissions by Source</h3>
              </div>
              <div
                className="chart-container"
                style={{
                  height: "170px",
                  width: "100%",
                  minWidth: 0,
                  position: "relative",
                }}
              >
                <PieChartWrapper
                  data={sourceChartData}
                  height={170}
                  innerRadius={50}
                  outerRadius={75}
                />
              </div>
            </div>
          </div>
        </div>

        {/* SBTi Trajectory Pathway - Full Width Banner */}
        {sbtiData && sbtiData.trajectory && sbtiData.trajectory.length > 0 && (
          <div className="card full-width-card glass-panel" style={{ padding: '24px', borderRadius: '20px' }}>
            <div className="card-header-row" style={{ marginBottom: '16px' }}>
              <div>
                <h3 className="card-subtitle" style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                  SBTi Decarbonization Trajectory ({sbtiData.pathway_type || "1.5°C"})
                </h3>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  Progress monitoring against corporate Net-Zero targets from Base Year {sbtiData.base_year} to Target Year {sbtiData.target_year}
                </p>
              </div>
              <button
                className="btn-secondary-unified"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 16px",
                  borderRadius: "10px",
                  background: "rgba(255, 255, 255, 0.8)",
                  border: "1px solid var(--border-color)",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  color: "var(--text-primary)"
                }}
                onClick={() => navigate("/sbti")}
              >
                View Full SBTi Dashboard →
              </button>
            </div>
            <div className="chart-container" style={{ height: "320px", width: "100%" }}>
              <LineChartWrapper
                data={sbtiData.trajectory}
                xAxisKey="year"
                series={[
                  {
                    dataKey: "actual",
                    name: "Actual Verified Emissions",
                    color: "#3b82f6",
                    strokeWidth: 3
                  },
                  {
                    dataKey: "sbti_target",
                    name: "SBTi 1.5°C Linear Target",
                    color: "#10b981",
                    strokeDasharray: "5 5",
                    strokeWidth: 2
                  },
                  {
                    dataKey: "bau_projection",
                    name: "Business as Usual (+1.5%/yr)",
                    color: "#ef4444",
                    strokeDasharray: "3 3",
                    strokeWidth: 2
                  }
                ]}
                height={320}
              />
            </div>
          </div>
        )}

        {/* Categorical Breakdown Cards */}

        <div
          className={`card categorical-card glass-panel ${categoricalCollapsed ? "collapsed-card" : ""}`}
        >
          <div
            className="card-header-row clickable-card-header"
            onClick={() => setCategoricalCollapsed(!categoricalCollapsed)}
            style={{
              cursor: "pointer",
              userSelect: "none",
              marginBottom: categoricalCollapsed ? "0" : "24px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <h3 className="card-subtitle">Categorical Emissions Overview</h3>
              <div className="card-info-badge">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                </svg>
                Activity → Division → Region
              </div>
            </div>
            <div
              className="collapse-toggle-icon"
              style={{
                display: "flex",
                alignItems: "center",
                color: "#64748b",
              }}
            >
              {categoricalCollapsed ? (
                <ChevronDown size={18} />
              ) : (
                <ChevronUp size={18} />
              )}
            </div>
          </div>
          <div
            className={`collapsible-body-wrapper ${categoricalCollapsed ? "collapsed" : ""}`}
          >
            <div className="categorical-hierarchy-grid">
              {getActivityOptions()
                .filter((o) => o.value !== "all")
                .map((opt) => (
                  <div key={opt.value} className="activity-group">
                    <div className="activity-group-header">{opt.label}</div>
                    {getHierarchicalData[opt.value] ? (
                      Object.entries(
                        getHierarchicalData[opt.value].divisions,
                      ).map(([div, divData]) => (
                        <div key={div} className="division-group">
                          <div className="division-group-header">{div}</div>
                          <div className="region-cards-grid">
                            {divData.regions.map((reg, ridx) => (
                              <div key={ridx} className="region-compact-card">
                                <div className="region-name">
                                  {reg.region}{" "}
                                  {reg.field && (
                                    <span className="region-field">
                                      - {reg.field}
                                    </span>
                                  )}
                                </div>
                                <div className="region-value">
                                  {formatCompactNumber(reg.total_emissions)}{" "}
                                  <span className="unit">tCO₂e</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="no-data-msg">
                        No emissions data for this activity
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </div>

        <div className="main-dashboard-grid">
          <div className="detailed-breakdown-section">
            <div
              className={`card detailed-table-card glass-panel ${detailedBreakdownCollapsed ? "collapsed-card" : ""}`}
            >
              <div
                className="table-header-row clickable-card-header"
                onClick={() =>
                  setDetailedBreakdownCollapsed(!detailedBreakdownCollapsed)
                }
                style={{
                  cursor: "pointer",
                  userSelect: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <h3 className="card-title" style={{ margin: 0 }}>
                  Detailed Breakdown
                </h3>
                <div
                  className="collapse-toggle-icon"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    color: "#64748b",
                  }}
                >
                  {detailedBreakdownCollapsed ? (
                    <ChevronDown size={18} />
                  ) : (
                    <ChevronUp size={18} />
                  )}
                </div>
              </div>
              <div
                className={`collapsible-body-wrapper ${detailedBreakdownCollapsed ? "collapsed" : ""}`}
              >
                <div className="table-container" style={{ marginTop: "16px" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Category / Source</th>
                        <th className="text-right">Results (tCO₂e)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="summary-row">
                        <td>Scope 1 (Direct)</td>
                        <td className="text-right font-bold">
                          {formatCompactNumber(stats.scope1)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="indent">Stationary Combustion</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.combustion)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="indent">Flaring</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.flaring)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="indent">Venting</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.venting)}
                        </td>
                      </tr>
                      <tr className="detail-row">
                        <td className="indent">Other Sources</td>
                        <td className="text-right">
                          {formatCompactNumber(stats.other)}
                        </td>
                      </tr>
                      <tr className="summary-row">
                        <td>Scope 2 (Indirect - Energy)</td>
                        <td className="text-right font-bold">
                          {formatCompactNumber(stats.scope2)}
                        </td>
                      </tr>
                      <tr className="summary-row">
                        <td>Scope 3 (Supply Chain)</td>
                        <td className="text-right font-bold">
                          {formatCompactNumber(stats.scope3)}
                        </td>
                      </tr>
                      <tr className="total-row">
                        <td>Total Footprint (Scopes 1+2+3)</td>
                        <td className="text-right">
                          {formatCompactNumber(
                            (stats.scope1 || 0) +
                              (stats.scope2 || 0) +
                              (stats.scope3 || 0)
                          )}
                        </td>
                      </tr>
                      <tr
                        className="total-row"
                        style={{ color: "#10b981", borderTop: "none" }}
                      >
                        <td>Net Footprint</td>
                        <td className="text-right">
                          {formatCompactNumber(
                            (stats.scope1 || 0) +
                              (stats.scope2 || 0) +
                              (stats.scope3 || 0) -
                              (stats.mitigation || 0)
                          )}
                        </td>
                      </tr>

                      <tr className="header-divider">
                        <td colSpan="2">Organizational Breakdown</td>
                      </tr>
                      {Object.entries(getHierarchicalData).map(
                        ([act, actData]) => (
                          <React.Fragment key={act}>
                            <tr
                              className="act-row clickable"
                              onClick={() => toggleActivity(act)}
                            >
                              <td>
                                <span className="toggle-icon">
                                  {expandedActivities[act] ? "▼" : "▶"}
                                </span>
                                {formatActivityName(act)}
                              </td>
                              <td className="text-right font-bold">
                                {formatCompactNumber(actData.total)}
                              </td>
                            </tr>
                            {expandedActivities[act] &&
                              Object.entries(actData.divisions).map(
                                ([div, divData]) => (
                                  <React.Fragment key={div}>
                                    <tr
                                      className="div-row clickable"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleDivision(div);
                                      }}
                                    >
                                      <td className="indent">
                                        <span className="toggle-icon">
                                          {expandedDivisions[div] ? "▼" : "▶"}
                                        </span>
                                        {div}
                                      </td>
                                      <td className="text-right">
                                        {formatCompactNumber(divData.total)}
                                      </td>
                                    </tr>
                                    {expandedDivisions[div] &&
                                      divData.regions.map((reg, ridx) => (
                                        <tr key={ridx} className="reg-row">
                                          <td className="indent-double">
                                            {reg.region}
                                          </td>
                                          <td className="text-right">
                                            {formatCompactNumber(
                                              reg.total_emissions,
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                  </React.Fragment>
                                ),
                              )}
                          </React.Fragment>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <div className="dashboard-sidebar">
            {/* Moved Trend Chart to Top */}

            <div className="card library-card">
              <div className="card-header-row">
                <h3 className="card-title">Reference Libraries</h3>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  style={{ opacity: 0.3 }}
                >
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
              </div>
              <div className="library-list">
                <div className="library-item">
                  <div className="dot blue"></div>
                  API Compendium: 2021
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
                <div className="library-item">
                  <div className="dot green"></div>
                  ISO 14064-1:2018
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
                <div className="library-item">
                  <div className="dot orange"></div>
                  GRI 305 Standards
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
              </div>
              <button
                className="manage-factors-btn"
                onClick={() =>
                  navigate("/manage-data", { state: { tab: "factors" } })
                }
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Manage Custom Factors
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardEnhanced;
