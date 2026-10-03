import EmissionsOverviewCard from "./dashboard/EmissionsOverviewCard";
import FlaringComplianceCard from "./dashboard/FlaringComplianceCard";
import DetailedBreakdownSection from "./dashboard/DetailedBreakdownSection";
import { useAnalyticsFilter } from "../filters/useAnalyticsFilter";
import { activateOnKey } from "../utils/a11yKeys";
import { SegmentedControl, Button } from "../ui";
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
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { ChevronDown, ChevronUp, Clock, Eye, EyeOff, ArrowRight, Flame, CheckCircle2, AlertTriangle, Hexagon } from "lucide-react";
import "./Dashboard.css";
import "./TopBarFilters.css";
import { useGwpStandard } from "../hooks/useGwpStandard";

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

  const denom = n * sumXX - sumX * sumX;
  if (!denom || Math.abs(denom) < 1e-9) return [];
  const slope = (n * sumXY - sumX * sumY) / denom;
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
  const [isReady, setIsReady] = useState(false);
  const [currentActivity, setCurrentActivity] = useAnalyticsFilter("activity");
  const [currentDivision, setCurrentDivision] = useAnalyticsFilter("division");
  const [currentRegion, setCurrentRegion] = useAnalyticsFilter("region");
  const [currentSegment, setCurrentSegment] = useAnalyticsFilter("segment");
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
    fugitive: 0,
    other: 0,
  });

  const [sbtiData, setSbtiData] = useState(null);
  const [flaringData, setFlaringData] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [categoricalData, setCategoricalData] = useState([]);
  const [currentYear, setCurrentYear] = useAnalyticsFilter("year");
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
  // BUG-013: tooltip values come from the active standard in constants.js
  const { standard: activeGwpStandard, gwp: activeGwp } = useGwpStandard();

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
          // the server already scopes a restricted user to their facilities; a default filter is
          // only applied when every accessible facility shares it (a region with two fields showed
          // the first field only)
          const shared = (key) => facilitiesData.length > 0 && facilitiesData.every((f) => f[key] === facilitiesData[0][key]);
          if (opDefaults.defaultActivity && shared("activity")) setCurrentActivity(opDefaults.defaultActivity);
          if (opDefaults.defaultDivision && shared("division")) setCurrentDivision(opDefaults.defaultDivision);
          if (opDefaults.defaultFacilityId && facilitiesData.length === 1) setCurrentRegion(opDefaults.defaultFacilityId);
        }
        setIsReady(true);
      } catch (error) {
        console.error("Failed to load initial data:", error);
        setIsReady(true);
      }
    };
    loadInitialData();
  }, [user]);

  const [isUpdating, setIsUpdating] = useState(false);
  const isFirstLoadRef = useRef(true);

  // Load dashboard data
  useEffect(() => {
    if (!isReady) return;
    loadDashboardData();
  }, [
    isReady,
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

      // Fetch Flaring Summary (Executive Decree 21-330 breakdown)
      try {
        const flareRes = await api.get(`/dashboard/flaring-summary?${filterParams}`);
        setFlaringData(flareRes.data);
      } catch (err) {
        console.error("Failed to load flaring summary", err);
        setFlaringData(null);
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
        fugitive: 0,
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
          totals.fugitive += row.fugitive || 0;
          totals.other += (row.other || 0) + (row.process || 0);
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
        // BUG-094: only implemented projects reduce "Net" (Planned ones are shown, not netted)
        if (item.counts_toward_net === false) return;
        if (currentYear === "all" || String(item.year) === currentYear) {
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
          name: "Equipment Leaks",
          value: Number((stats.fugitive ?? 0).toFixed(2)),
          color: "#8b5cf6",
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
    "#ff6600",
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
      <div className="flex! items-center! gap-[10px]!">
        {/* GWP horizon */}
        <SegmentedControl
          label="GWP horizon"
          size="sm"
          value={gwpHorizon}
          onChange={setGwpHorizon}
          options={[
            {
              value: "100",
              label: "GWP-100",
              title: activeGwp
                ? `100-Year (Standard, CH4=${activeGwp.CH4}) per IPCC ${activeGwpStandard}`
                : "100-Year (Standard)",
            },
            {
              value: "20",
              label: "GWP-20",
              title: activeGwp
                ? `20-Year (Near-term, CH4=${activeGwp.CH4_20}) per IPCC ${activeGwpStandard}`
                : "20-Year (Near-term)",
            },
          ]}
        />

        {goal ? (
          <div className="[display:flex] [align-items:center] [gap:8px] [background:rgba(255,_255,_255,_0.8)] [padding:4px_10px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [font-size:var(--text-sm)]">
            <span className="text-[length:0.8rem]! text-[color:var(--text-secondary)]!">
              Target {goal.year}: <strong className="text-[color:var(--text-primary)]!">{Number(goal.target_amount).toLocaleString()} tCO₂e</strong>
            </span>
            <button
              className="btn-target-action [padding:6px_14px] [font-size:var(--text-sm)] [font-weight:600] [border-radius:var(--radius-md)] [background:rgba(255,_255,_255,_0.9)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [color:var(--text-primary)] [cursor:pointer] [transition:all_0.2s_ease] [white-space:nowrap] hover:[border-color:var(--accent-color,_var(--color-brand-500))] hover:[color:var(--color-link)]"
              onClick={() => navigate("/manage-data", { state: { tab: "goals" } })}
              title="Manage emission goals and base years in Manage Data"
            >
              Edit Target
            </button>
          </div>
        ) : (
          <button
            className="btn-target-action [padding:6px_14px] [font-size:var(--text-sm)] [font-weight:600] [border-radius:var(--radius-md)] [background:rgba(255,_255,_255,_0.9)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [color:var(--text-primary)] [cursor:pointer] [transition:all_0.2s_ease] [white-space:nowrap] hover:[border-color:var(--accent-color,_var(--color-brand-500))] hover:[color:var(--color-link)]"
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
        year: currentYear, // BUG-077: pass "all" explicitly so the brief is labelled correctly
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
      className="[min-height:100vh] [background:transparent] [padding:24px_32px_48px]! [position:relative] [overflow-x:hidden] [color:var(--text-primary,_var(--color-ink-900))] [@media_print]:[padding:20px]! [@media_print]:[max-width:100%]! [@media(max-width:768px)]:[padding:14px_12px_36px]!"
      style={{
        opacity: isUpdating ? 0.8 : 1,
        transition: "opacity 0.15s ease",
      }}
    >
      <div className="dashboard-grid [display:flex] [flex-direction:column] [gap:24px] [max-width:1600px] [margin:0_auto] [&>*]:[opacity:0] [&>*]:[animation:dashboardFadeIn_0.5s_cubic-bezier(0.16,_1,_0.3,_1)_forwards] [&&]:[&>*:nth-child(1)]:[animation-delay:0.05s] [&&]:[&&]:[&>*:nth-child(2)]:[animation-delay:0.12s] [&&]:[&&]:[&&]:[&>*:nth-child(3)]:[animation-delay:0.18s] [&&]:[&&]:[&&]:[&&]:[&>*:nth-child(4)]:[animation-delay:0.24s] [&&]:[&&]:[&&]:[&&]:[&&]:[&>*:nth-child(5)]:[animation-delay:0.30s]">
        <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:20px]">
          <h1 className="grid-title">GHG Emissions Dashboard</h1>
          <div className="live-badge [background:rgba(255,_255,_255,_0.8)] [backdrop-filter:blur(8px)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [padding:6px_14px] [&&]:[border-radius:999px] [display:flex] [align-items:center] [gap:8px] [font-size:var(--text-sm)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [box-shadow:var(--shadow-xs)]">
            <div className={`pulse-dot ${isUpdating ? "updating" : ""}`}></div>
            {isUpdating ? "Syncing filters..." : `Live Content • Updated ${lastUpdated}`}
          </div>
        </div>

        {pendingCount > 0 && (
          <div className={`pending-banner-card [display:flex] [justify-content:space-between] [align-items:center]! [flex-wrap:wrap]! [gap:16px] [padding:16px_22px]! [margin-bottom:24px] [background:rgba(255,_255,_255,_0.88)] [backdrop-filter:blur(12px)] [-webkit-backdrop-filter:blur(12px)] [border:1px_solid_rgba(245,_158,_11,_0.28)] [&&]:[border-radius:var(--radius-lg)] [box-shadow:0_4px_20px_-2px_rgba(245,_158,_11,_0.08),_0_2px_6px_-1px_rgba(15,_23,_42,_0.02)] [position:relative] [overflow:hidden] [transition:all_0.25s_cubic-bezier(0.16,_1,_0.3,_1)] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[bottom:0] before:[width:4px] before:[background:linear-gradient(180deg,_var(--color-amber-500)_0%,_var(--color-brand-500)_100%)] before:[border-radius:var(--radius-sm)_0_0_var(--radius-sm)] [&.active-preview]:[border-color:rgba(255,_102,_0,_0.4)] [&.active-preview]:[background:linear-gradient(135deg,_rgba(255,_255,_255,_0.95)_0%,_rgba(255,_247,_237,_0.9)_100%)] [&.active-preview]:[box-shadow:0_6px_24px_-2px_rgba(255,_102,_0,_0.12),_0_2px_8px_-1px_rgba(15,_23,_42,_0.04)] [&:hover_.pending-banner-icon]:[transform:scale(1.05)] [@media(max-width:640px)]:[flex-direction:column]! [@media(max-width:640px)]:[align-items:stretch]! [@media(max-width:640px)]:[padding:14px_16px]! ${includePending ? "active-preview" : ""}`}>
            <div className="[display:flex] [align-items:center] [gap:14px] [flex:1] [min-width:280px]">
              <div className="pending-banner-icon [width:42px] [height:42px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [background:linear-gradient(135deg,_rgba(245,_158,_11,_0.15)_0%,_rgba(255,_102,_0,_0.12)_100%)] [border:1px_solid_rgba(245,_158,_11,_0.25)] [color:var(--color-amber-700)] [flex-shrink:0] [box-shadow:0_2px_8px_rgba(245,_158,_11,_0.1)] [transition:transform_0.2s_ease]">
                <Clock size={20} />
              </div>
              <div className="[display:flex] [flex-direction:column] [gap:4px]">
                <div className="[display:flex] [align-items:center] [gap:10px] [flex-wrap:wrap]">
                  <h3 className="[margin:0] [font-size:var(--text-md)] [font-weight:700] [color:var(--text-primary,_var(--color-ink-900))] [letter-spacing:-0.01em]">
                    {includePending
                      ? "Previewing Pending & Verified Emissions"
                      : "Pending Records Awaiting Review"}
                  </h3>
                  <span className={`[display:inline-flex] [align-items:center] [gap:5px] [padding:2px_9px] [border-radius:999px] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [text-transform:uppercase] [background:rgba(245,_158,_11,_0.12)] [color:var(--color-amber-700)]! [border:1px_solid_rgba(245,_158,_11,_0.25)] [&.active-preview-badge]:[background:rgba(255,_102,_0,_0.12)] [&.active-preview-badge]:[color:var(--color-brand-700)]! [&.active-preview-badge]:[border-color:rgba(255,_102,_0,_0.28)] ${includePending ? "active-preview-badge" : ""}`}>
                    {includePending ? "Live Preview Active" : "Pending Approval"}
                  </span>
                </div>
                <p className="pending-banner-desc">
                  There are <strong>{pendingCount.toLocaleString()}</strong> emission records
                  {pendingCo2e > 0 && (
                    <span className="[display:inline-block] [font-weight:600] [color:var(--color-amber-700)] [background:rgba(245,_158,_11,_0.08)] [padding:1px_6px] [border-radius:var(--radius-sm)] [margin:0_4px] [font-variant-numeric:tabular-nums]">
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

            <div className="[display:flex] [align-items:center] [gap:12px] [flex-wrap:wrap] [@media(max-width:640px)]:[justify-content:space-between] [@media(max-width:640px)]:[width:100%] [@media(max-width:640px)]:[margin-top:4px] [@media(max-width:640px)]:[padding-top:10px] [@media(max-width:640px)]:[border-top:1px_solid_rgba(226,_232,_240,_0.8)]">
              <label
                className="[display:flex] [align-items:center] [gap:10px] [padding:6px_14px] [border-radius:var(--radius-md)] [background:rgba(241,_245,_249,_0.8)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [cursor:pointer] [user-select:none] [transition:all_0.2s_ease] hover:[background:rgba(255,_247,_237,_0.9)] hover:[border-color:rgba(255,_102,_0,_0.3)] [&:hover_.pending-toggle-label]:[color:var(--text-primary,_var(--color-ink-900))]!"
                title="Toggle pending emissions preview"
              >
                <span className="pending-toggle-label [display:flex] [align-items:center] [gap:6px] [font-size:var(--text-sm)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-600))] [transition:color_0.2s_ease]">
                  {includePending ? <Eye size={15} /> : <EyeOff size={15} />}
                  <span>Preview Pending Data</span>
                </span>
                <div className={`pending-switch ${includePending ? "active" : ""}`}>
                  <input
                    type="checkbox"
                    checked={includePending}
                    onChange={(e) => setIncludePending(e.target.checked)}
                    className="[opacity:0]! [width:0] [height:0] [position:absolute]"
                  />
                  <span className="pending-switch-slider [position:absolute] [top:2px] [left:2px] [width:16px] [height:16px] [background-color:var(--color-white)] [border-radius:50%] [box-shadow:var(--shadow-xs)] [transition:transform_0.25s_cubic-bezier(0.4,_0,_0.2,_1)]" />
                </div>
              </label>

              {['admin', 'superuser'].includes(user?.role) && (
                <button
                  type="button"
                  className="[display:inline-flex] [align-items:center] [gap:7px] [padding:8px_16px] [font-size:var(--text-sm)] [font-weight:600] [border-radius:var(--radius-md)] [background:linear-gradient(135deg,_var(--color-amber-700)_0%,_var(--color-amber-700)_100%)] [color:var(--color-white)] [border:none] [cursor:pointer] [box-shadow:0_2px_10px_rgba(217,_119,_6,_0.25)] [transition:all_0.2s_cubic-bezier(0.16,_1,_0.3,_1)]! [white-space:nowrap] hover:[transform:translateY(-1px)] hover:[box-shadow:0_4px_14px_rgba(217,_119,_6,_0.35)] hover:[filter:brightness(1.05)] active:[transform:translateY(0)] [&_svg]:[transition:transform_0.2s_ease]! [&:hover_svg]:[transform:translateX(2px)]"
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


        {/* Hero Overview Card */}
        <EmissionsOverviewCard
        currentActivity={currentActivity}
        currentDivision={currentDivision}
        currentRegion={currentRegion}
        currentYear={currentYear}
        exportingPDF={exportingPDF}
        facilities={facilities}
        goal={goal}
        handleExportPDF={handleExportPDF}
        hasProductionData={hasProductionData}
        intensity={intensity}
        stats={stats}
        variance={variance}
      />

        {/* --- Operational Flaring & Decree 21-330 Regulatory Compliance Banner --- */}
        {flaringData && (flaringData.total_flaring?.volume_knm3 > 0 || stats.flaring > 0) && (
          <FlaringComplianceCard
        flaringData={flaringData}
      />
        )}

        {/* --- Primary Analytics Grid: Trend Line (2fr) + Donuts (1fr) --- */}
        <div className="charts-section [display:grid] [grid-template-columns:2fr_1fr]! [gap:24px]! [@media(max-width:1024px)]:[grid-template-columns:1fr]! [@media(max-width:1200px)]:[grid-template-columns:1fr]! [@media(max-width:1200px)]:[gap:20px]!">
          {/* Trend Chart */}
          <div className="card trend-card-enhanced glass-panel">
            <div className="[display:flex] [justify-content:space-between] [align-items:center]! [margin-bottom:24px] [@media(max-width:768px)]:[flex-direction:column] [@media(max-width:768px)]:[align-items:flex-start]! [@media(max-width:768px)]:[gap:12px]">
              <div>
                <h3 className="card-title">Emissions Trend & Projection</h3>
                <p className="m-[0px]! text-[color:var(--text-secondary)]! text-[length:0.85rem]!">
                  Historical inventory trajectory with 5-year predictive forecast
                </p>
              </div>
              <div className="[@media_print]:[display:none]! [display:flex]! [align-items:center] [gap:12px]">
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
              className="chart-container h-[360px]! w-full! min-w-0! relative!"
             
            >
              <LineChartWrapper
                data={trendData}
                xKey="year"
                lines={
                  isCompareMode
                    ? // every facility of any year (the first year's facilities only, before)
                      [...new Set(trendData.flatMap((p) => Object.keys(p)))]
                        .filter((k) => k !== "year" && k !== "trajectory" && k !== "forecast")
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
                      ].filter((l) => trendData.some((p) => p[l.dataKey] != null)) // no legend entry without a line
                }
                height={360}
              />
            </div>
          </div>

          {/* Donut Charts Column (1fr) */}
          <div className="[display:flex] [flex-direction:column] [gap:24px] [min-width:0]">
            <div className="card donut-card-enhanced glass-panel">
              <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:12px]">
                <h3 className="[font-size:var(--text-md)] [font-weight:700] [color:var(--color-ink-800)] [margin:0] activity">Emissions by Activity</h3>
              </div>
              <div
                className="chart-container h-[170px]! w-full! min-w-0! relative!"
               
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
              <div className="[display:flex] [justify-content:space-between] [align-items:center] [margin-bottom:12px]">
                <h3 className="[font-size:var(--text-md)] [font-weight:700] [color:var(--color-ink-800)] [margin:0] source">Emissions by Source</h3>
              </div>
              <div
                className="chart-container h-[170px]! w-full! min-w-0! relative!"
               
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
          <div className="card full-width-card glass-panel p-[24px]! rounded-[20px]!">
            <div className="[display:flex] [justify-content:space-between] [align-items:center]! [@media(max-width:768px)]:[flex-direction:column] [@media(max-width:768px)]:[align-items:flex-start]! [@media(max-width:768px)]:[gap:12px] mb-[16px]!">
              <div>
                <h3 className="card-subtitle text-[length:1.15rem]! font-bold!">
                  {sbtiData.pathway_label || "Decarbonization Trajectory"}
                </h3>
                <p className="m-[0px]! text-[color:var(--text-secondary)]! text-[length:0.875rem]!">
                  Progress monitoring against corporate Net-Zero targets from Base Year {sbtiData.base_year} to Target Year {sbtiData.target_year}
                </p>
              </div>
              <Button
                variant="secondary" type="submit"
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
              </Button>
            </div>
            <div className="chart-container h-[320px]! w-full!">
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
                    name: sbtiData?.pathway_label || "Linear Target", // BUG-059: label follows the stored pathway
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
          <div role="button" tabIndex={0} onKeyDown={activateOnKey}
            className="[display:flex] [justify-content:space-between] [align-items:center]! [@media(max-width:768px)]:[flex-direction:column] [@media(max-width:768px)]:[align-items:flex-start]! [@media(max-width:768px)]:[gap:12px] clickable-card-header [transition:opacity_0.2s_ease] hover:[opacity:0.85]!"
            onClick={() => setCategoricalCollapsed(!categoricalCollapsed)}
            style={{
              cursor: "pointer",
              userSelect: "none",
              marginBottom: categoricalCollapsed ? "0" : "24px",
            }}
          >
            <div className="flex! items-center! gap-[12px]!">
              <h3 className="card-subtitle">Categorical Emissions Overview</h3>
              <div className="[display:flex] [align-items:center] [gap:6px] [font-size:var(--text-sm)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [background:var(--bg-hover,_var(--color-ink-100))] [padding:4px_12px] [border-radius:999px]">
                <Hexagon size="14" strokeWidth="2" aria-hidden="true" />
                Activity → Division → Region
              </div>
            </div>
            <div
              className=" flex! items-center! text-[color:#64748b]!"
             
            >
              {categoricalCollapsed ? (
                <ChevronDown size={18} />
              ) : (
                <ChevronUp size={18} />
              )}
            </div>
          </div>
          <div
            className={`[@media_print]:[&.collapsed]:[display:block]! [@media_print]:[&.collapsed]:[max-height:none]! [@media_print]:[&.collapsed]:[opacity:1]! [max-height:2500px]! [opacity:1]! [overflow:hidden] [transition:max-height_0.4s_cubic-bezier(0.4,_0,_0.2,_1),_opacity_0.3s_ease,_margin-top_0.3s_ease] [&&]:[&.collapsed]:[max-height:0]! [&&]:[&.collapsed]:[opacity:0]! [&.collapsed]:[margin-top:0] [&.collapsed]:[pointer-events:none] ${categoricalCollapsed ? "collapsed" : ""}`}
          >
            <div className="categorical-hierarchy-grid">
              {getActivityOptions()
                .filter((o) => o.value !== "all")
                .map((opt) => (
                  <div key={opt.value} className="[display:flex] [flex-direction:column] [gap:16px]">
                    <div className="[font-size:var(--text-base)] [font-weight:700] [color:var(--text-primary,_var(--color-ink-900))] [padding-bottom:6px] [border-bottom:2px_solid_var(--accent-color,_var(--color-brand-500))] [width:fit-content] [padding-right:12px]">{opt.label}</div>
                    {getHierarchicalData[opt.value] ? (
                      Object.entries(
                        getHierarchicalData[opt.value].divisions,
                      ).map(([div, divData]) => (
                        <div key={div} className="[background:rgba(255,_255,_255,_0.6)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-lg)] [padding:14px]">
                          <div className="[font-size:var(--text-sm)] [font-weight:700] [color:var(--text-secondary,_var(--color-ink-500))] [text-transform:uppercase] [margin-bottom:12px] [letter-spacing:0.05em]">{div}</div>
                          <div className="[display:flex] [flex-direction:column] [gap:8px]">
                            {divData.regions.map((reg, ridx) => (
                              <div key={ridx} className="[background:rgba(255,_255,_255,_0.9)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-md)] [padding:10px_12px] [transition:transform_0.2s_ease,_border-color_0.2s_ease,_box-shadow_0.2s_ease] [box-shadow:var(--shadow-xs)] hover:[border-color:var(--accent-color,_var(--color-brand-500))] hover:[transform:translateX(4px)] hover:[box-shadow:0_4px_12px_rgba(255,_102,_0,_0.1)]">
                                <div className="[font-size:var(--text-sm)] [font-weight:600] [color:var(--text-primary,_var(--color-ink-900))] [margin-bottom:4px]">
                                  {reg.region}{" "}
                                  {reg.field && (
                                    <span className="[color:var(--color-ink-600)] [font-weight:500]">
                                      - {reg.field}
                                    </span>
                                  )}
                                </div>
                                <div className="[font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-ink-900)]! [&_.unit]:[font-size:var(--text-xs)]! [&_.unit]:[color:var(--text-secondary,_var(--color-ink-500))]! [&_.unit]:[font-weight:600]!">
                                  {formatCompactNumber(reg.total_emissions)}{" "}
                                  <span className="unit">tCO₂e</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="[font-size:var(--text-sm)] [color:var(--color-ink-600)] [font-style:italic] [padding:8px_0]">
                        No emissions data for this activity
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </div>

        <DetailedBreakdownSection
        detailedBreakdownCollapsed={detailedBreakdownCollapsed}
        expandedActivities={expandedActivities}
        expandedDivisions={expandedDivisions}
        flaringData={flaringData}
        formatActivityName={formatActivityName}
        getHierarchicalData={getHierarchicalData}
        navigate={navigate}
        setDetailedBreakdownCollapsed={setDetailedBreakdownCollapsed}
        stats={stats}
        toggleActivity={toggleActivity}
        toggleDivision={toggleDivision}
      />
      </div>
    </div>
  );
};

export default DashboardEnhanced;
