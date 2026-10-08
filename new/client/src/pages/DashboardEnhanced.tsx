import React, { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import EmissionsOverviewCard from "./dashboard/EmissionsOverviewCard";
import FlaringComplianceCard from "./dashboard/FlaringComplianceCard";
import DetailedBreakdownSection from "./dashboard/DetailedBreakdownSection";
import { useAnalyticsFilter } from "../filters/useAnalyticsFilter";
import { SegmentedControl, Badge, cn } from "../ui";
import { PendingBanner, TrendCard, DonutCard, SbtiCard, CategoricalCard, BridgeCard } from "./dashboard/DashboardCards";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import CustomDropdown from "../components/CustomDropdown";
import { calculateTrend } from "../utils/formatters";
import { useLayout } from "../context/LayoutContext";
import { getUserOperationalDefaults } from "../utils/userDefaults";

import "./Dashboard.css";
import "./TopBarFilters.css";
import { useGwpStandard } from "../hooks/useGwpStandard";

interface HistoricalDataPoint {
  year: number;
  emissions: number;
}

interface ForecastPoint {
  year: number;
  forecast: number;
}

interface FacilityItem {
  id: string | number;
  name: string;
  field?: string;
  segment?: string;
  activity?: string;
  division?: string;
  [key: string]: any;
}

interface AvailableFiltersState {
  years: number[];
  regions: string[];
  segments: string[];
}

interface DashboardStats {
  totalEmissions: number;
  netEmissions: number;
  scope1: number;
  scope2: number;
  scope3: number;
  mitigation: number;
  methaneEmissions: number;
  purchasedEnergy: number;
  combustion: number;
  flaring: number;
  venting: number;
  fugitive: number;
  other: number;
  totalProductionBoe?: number;
  [key: string]: any;
}

interface GoalData {
  year: number | string;
  target_amount: number;
  [key: string]: any;
}

interface BaseYearData {
  year: number;
  value?: number;
  [key: string]: any;
}

interface CategoricalItem {
  activity?: string;
  division?: string;
  region?: string;
  total_emissions: number;
  [key: string]: any;
}

interface HierarchicalDataStructure {
  [activity: string]: {
    total: number;
    divisions: {
      [division: string]: {
        total: number;
        regions: CategoricalItem[];
      };
    };
  };
}

// Simple Linear Regression for Forecasting
const calculateForecast = (data: HistoricalDataPoint[]): ForecastPoint[] => {
  if (data.length < 2) return [];

  const n = data.length;
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumXX = 0;

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
  const forecast: ForecastPoint[] = [];

  // Forecast next 5 years
  for (let i = 1; i <= 5; i++) {
    const year = lastYear + i;
    const emissions = Number((slope * year + intercept).toFixed(2));
    forecast.push({ year, forecast: Math.max(0, emissions) }); // No negative emissions
  }
  return forecast;
};

// Helper to map DB activity acronyms to readable legends
const formatActivityName = (act?: string): string => {
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
  "var(--color-amber-500)",
  "var(--color-blue-500)",
  "var(--color-green-500)",
  "var(--color-legacy-6366f1)",
  "var(--color-red-500)",
  "var(--color-pink-500)",
  "var(--color-brand-500)",
  "var(--color-legacy-a855f7)",
];

const ACTIVITY_COLOR_MAP: Record<string, string> = {
  "E&P (Upstream)": "var(--color-amber-500)", // amber
  "LQS (Liquefaction)": "var(--color-blue-500)", // blue
  "RPC (Refining)": "var(--color-green-500)", // green
  "TRC (Transport)": "var(--color-legacy-6366f1)", // indigo
};

const DashboardEnhanced: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();

  // Filter states
  const [isReady, setIsReady] = useState<boolean>(false);
  const [currentActivity, setCurrentActivity] = useAnalyticsFilter("activity");
  const [currentDivision, setCurrentDivision] = useAnalyticsFilter("division");
  const [currentRegion, setCurrentRegion] = useAnalyticsFilter("region");
  const [currentSegment, setCurrentSegment] = useAnalyticsFilter("segment");
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [availableFilters, setAvailableFilters] = useState<AvailableFiltersState>({
    years: [],
    regions: [],
    segments: [],
  });

  // Data states
  const [stats, setStats] = useState<DashboardStats>({
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

  const [sbtiData, setSbtiData] = useState<any>(null);
  const [flaringData, setFlaringData] = useState<any>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [categoricalData, setCategoricalData] = useState<CategoricalItem[]>([]);
  const [currentYear, setCurrentYear] = useAnalyticsFilter("year");
  const [expandedActivities, setExpandedActivities] = useState<Record<string, boolean>>({});
  const [expandedDivisions, setExpandedDivisions] = useState<Record<string, boolean>>({});
  const [goal, setGoal] = useState<GoalData | null>(null);
  const [intensity, setIntensity] = useState<number>(0);
  const [hasProductionData, setHasProductionData] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);
  const [isCompareMode, setIsCompareMode] = useState<boolean>(false);
  const [variance, setVariance] = useState<{ emissions: string; intensity: string }>({ emissions: "—", intensity: "—" });
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [pendingCo2e, setPendingCo2e] = useState<number>(0);
  const [includePending, setIncludePending] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>(
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  );
  const [categoricalCollapsed, setCategoricalCollapsed] = useState<boolean>(false);
  const [detailedBreakdownCollapsed, setDetailedBreakdownCollapsed] = useState<boolean>(false);
  const [exportingPDF, setExportingPDF] = useState<boolean>(false);
  const [gwpHorizon, setGwpHorizon] = useState<string>("100"); // "100" (Standard 100-yr) or "20" (Near-term 20-yr)
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
        const facilitiesData: FacilityItem[] = Array.isArray(facRes.data)
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
          const shared = (key: string) => facilitiesData.length > 0 && facilitiesData.every((f) => f[key] === facilitiesData[0][key]);
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

  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const isFirstLoadRef = useRef<boolean>(true);

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
      const queryParams: Record<string, string> = {
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
      const batchRes = await api.get(`/dashboard/batch-all?${filterParams.toString()}`);
      const batch = batchRes.data;

      if (batch.pending_stats) {
        setPendingCount(batch.pending_stats.count || 0);
        setPendingCo2e(batch.pending_stats.totalCo2e || 0);
      } else if (user?.role && ["admin", "superuser"].includes(user.role)) {
        try {
          const pRes = await api.get("/emissions/pending");
          setPendingCount(pRes.data.total_pending || 0);
        } catch (e) {
          console.error(e);
        }
      }

      const summaryData: any[] = batch.summary || [];
      const mitData: any[] = batch.mitigation || [];
      const s3Data: any = batch.scope3_summary || { total: 0 };
      const catData: CategoricalItem[] = batch.categorical_breakdown || [];
      const intensityData: any[] = batch.intensity_stats || [];
      const gObj: GoalData | null = batch.goal || null;
      const bYearObj: BaseYearData | null = batch.base_year || null;

      setGoal(gObj);
      setCategoricalData(catData);

      // Fetch SBTi Trajectory Data
      try {
        const sbtiRes = await api.get("/dashboard/sbti-trajectory");
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
        const flareRes = await api.get(`/dashboard/flaring-summary?${filterParams.toString()}`);
        setFlaringData(flareRes.data);
      } catch (err) {
        console.error("Failed to load flaring summary", err);
        setFlaringData(null);
      }

      const totals: DashboardStats = {
        totalEmissions: 0,
        scope1: 0,
        scope2: 0,
        // BUG-UI-04 FIX: Apply year filter to Scope 3 just like Scope 1 & 2
        scope3:
          currentYear === "all"
            ? (s3Data.total || 0)
            : (s3Data.by_year?.[currentYear] ??
              s3Data.by_year?.[parseInt(currentYear, 10)] ??
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
        netEmissions: 0,
      };

      const yearlyTrend: Record<string | number, Record<string, any>> = {};
      const facilityNames: Record<string | number, string> = {};
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
      const intensityPyData: any[] = batch.intensity_stats_py || [];
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
        const cy = parseInt(currentYear, 10);
        const py = cy - 1;

        // BUG FIX: Calculate aggregate emissions dynamically from summaryData to support Compare Mode
        // because yearlyTrend uses facility names instead of 'emissions' key when in Compare Mode.
        let cyEmissions = 0;
        let pyEmissions = 0;
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
      let trendArray: any[] = Object.values(yearlyTrend).sort(
        (a: any, b: any) => a.year - b.year,
      );

      if (gObj && bYearObj && !isCompareMode) {
        const baseEmissions =
          yearlyTrend[bYearObj.year]?.emissions ||
          trendArray[0]?.emissions ||
          0;
        const startYear = bYearObj.year;
        const endYear = typeof gObj.year === "string" ? parseInt(gObj.year, 10) : gObj.year;
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
        const historicalData: HistoricalDataPoint[] = trendArray
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
        .map((a) => ({ value: a as string, label: formatActivityName(a as string) })),
    ];
  };

  const getDivisionOptions = () => {
    const divisionsSet = new Set<string>();
    const filtered = facilities.filter(
      (f) =>
        (currentSegment === "all" || f.segment === currentSegment) &&
        (currentActivity === "all" || f.activity === currentActivity),
    );
    filtered.forEach((f) => {
      if (f.division) divisionsSet.add(f.division);
    });
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

  const handleSegmentChange = (value: string) => {
    setCurrentSegment(value);
    setCurrentActivity("all");
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleActivityChange = (value: string) => {
    setCurrentActivity(value);
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleDivisionChange = (value: string) => {
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
          color: "var(--color-green-500)",
        },
        {
          name: "Flaring",
          value: Number((stats.flaring ?? 0).toFixed(2)),
          color: "var(--color-brand-500)",
        },
        {
          name: "Venting",
          value: Number((stats.venting ?? 0).toFixed(2)),
          color: "var(--color-amber-500)",
        },
        {
          name: "Equipment Leaks",
          value: Number((stats.fugitive ?? 0).toFixed(2)),
          color: "var(--color-violet-500)",
        },
        {
          name: "Other",
          value: Number((stats.other ?? 0).toFixed(2)),
          color: "var(--color-blue-500)",
        },
      ].filter((d) => d.value > 0),
    [stats],
  );

  const activityChartData = useMemo(() => {
    const acting: Record<string, number> = {};
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
            onChange={(val: any) => setCurrentYear(val)}
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
            onChange={(val: any) => setCurrentRegion(val)}
            placeholder="Region"
          />
        </div>
      </div>,
    );

    setTopBarRight(
      <div className="flex! items-center! gap-[10px]!">
        {/* GWP horizon */}
        <SegmentedControl
          label="GWP horizon"
          size="sm"
          value={gwpHorizon}
          onChange={(val: any) => setGwpHorizon(val)}
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
      </div>,
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
    activeGwp,
    activeGwpStandard,
  ]);

  const toggleActivity = (act: string) => {
    setExpandedActivities((prev) => ({ ...prev, [act]: !prev[act] }));
  };

  const toggleDivision = (div: string) => {
    setExpandedDivisions((prev) => ({ ...prev, [div]: !prev[div] }));
  };

  const getHierarchicalData = useMemo(() => {
    const hierarchy: HierarchicalDataStructure = {};
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

  // every facility of any year when comparing, otherwise the headline series that have data
  const trendLines = isCompareMode
    ? [...new Set(trendData.flatMap((p) => Object.keys(p)))]
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
          color: "var(--color-brand-500)",
        },
        {
          dataKey: "scope1",
          name: "Scope 1",
          color: "var(--color-blue-500)",
        },
        {
          dataKey: "trajectory",
          name: "Target Path",
          color: "var(--color-green-500)",
          strokeDasharray: "5 5",
        },
        {
          dataKey: "forecast",
          name: "Forecast",
          color: "var(--color-violet-500)",
          strokeDasharray: "3 3",
        },
      ].filter((l) => trendData.some((p) => p[l.dataKey] != null));

  return (
    <div
      className="[min-height:100vh] [background:transparent] [padding:24px_32px_48px]! [position:relative] [overflow-x:hidden] [color:var(--text-primary,_var(--color-ink-900))] [@media_print]:[padding:20px]! [@media_print]:[max-width:100%]! [@media(max-width:768px)]:[padding:14px_12px_36px]!"
      style={{
        opacity: isUpdating ? 0.8 : 1,
        transition: "opacity 0.15s ease",
      }}
    >
      <div className="dashboard-grid [display:flex] [flex-direction:column] [gap:24px] [max-width:1600px] [margin:0_auto] [&>*]:[opacity:0] [&>*]:[animation:dashboardFadeIn_0.5s_cubic-bezier(0.16,_1,_0.3,_1)_forwards] [&&]:[&>*:nth-child(1)]:[animation-delay:0.05s] [&&]:[&&]:[&>*:nth-child(2)]:[animation-delay:0.12s] [&&]:[&&]:[&&]:[&>*:nth-child(3)]:[animation-delay:0.18s] [&&]:[&&]:[&&]:[&&]:[&>*:nth-child(4)]:[animation-delay:0.24s] [&&]:[&&]:[&&]:[&&]:[&&]:[&>*:nth-child(5)]:[animation-delay:0.30s]">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h1 className="grid-title m-0 text-xl font-bold text-text">GHG Emissions Dashboard</h1>
          <Badge className="live-badge gap-2 bg-surface/80 px-3.5 py-1.5 text-sm text-text-secondary">
            <span className={cn("size-2 rounded-full bg-green-500", isUpdating && "animate-pulse")} aria-hidden="true" />
            {isUpdating ? "Syncing filters..." : `Live content • Updated ${lastUpdated}`}
          </Badge>
        </div>

        {pendingCount > 0 && (
          <PendingBanner
            count={pendingCount}
            co2e={pendingCo2e}
            includePending={includePending}
            onIncludePending={setIncludePending}
            canReview={Boolean(user?.role && ["admin", "superuser"].includes(user.role))}
            onReview={() => navigate("/manage-data", { state: { tab: "pending" } })}
          />
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
          <FlaringComplianceCard flaringData={flaringData} />
        )}

        <div className="charts-section grid gap-6 [grid-template-columns:2fr_1fr] max-[1200px]:grid-cols-1">
          <TrendCard data={trendData} lines={trendLines} compare={isCompareMode} onCompare={() => setIsCompareMode(!isCompareMode)} />
          <div className="flex min-w-0 flex-col gap-6">
            <DonutCard title="Emissions by Activity" data={activityChartData} noun="activity" />
            <DonutCard title="Emissions by Source" data={sourceChartData} noun="source" />
          </div>
        </div>

        <BridgeCard
          params={
            new URLSearchParams({
              facilityId: currentRegion,
              activity: currentActivity,
              division: currentDivision,
              ...(currentSegment !== "all" ? { segment: currentSegment } : {}),
              ...(currentYear !== "all" ? { year: currentYear } : {}),
              ...(includePending ? { includePending: "true" } : {}),
              ...(gwpHorizon && gwpHorizon !== "100" ? { gwp_horizon: gwpHorizon } : {}),
            })
          }
        />

        {sbtiData?.trajectory?.length > 0 && <SbtiCard sbti={sbtiData} onOpen={() => navigate("/sbti")} />}

        <CategoricalCard
          collapsed={categoricalCollapsed}
          onToggle={() => setCategoricalCollapsed(!categoricalCollapsed)}
          activities={getActivityOptions().filter((o) => o.value !== "all")}
          hierarchy={getHierarchicalData as any}
        />

        <DetailedBreakdownSection
          detailedBreakdownCollapsed={detailedBreakdownCollapsed}
          expandedActivities={expandedActivities}
          expandedDivisions={expandedDivisions}
          flaringData={flaringData}
          formatActivityName={formatActivityName}
          getHierarchicalData={getHierarchicalData as any}
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
