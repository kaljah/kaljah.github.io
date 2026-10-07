import MethaneIntensityMethaneIntensity, { type MethaneIntensityStats } from "./methane-intensity/MethaneIntensityMethaneIntensity";
import MethaneIntensityOGMP20Gold from "./methane-intensity/MethaneIntensityOGMP20Gold";
import MethaneIntensityOGMP20Level from "./methane-intensity/MethaneIntensityOGMP20Level";
import MethaneIntensityHistoricalMethaneTrends from "./methane-intensity/MethaneIntensityHistoricalMethaneTrends";
import { useAnalyticsFilter } from "../filters/useAnalyticsFilter";
import React, { useState, useEffect, useMemo, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { BarChart } from "../components/charts";
import { useLayout } from "../context/LayoutContext";
import CustomDropdown from "../components/CustomDropdown";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { CH4_DENSITY_KG_M3 } from "../constants";
import { Download } from "lucide-react";
import "./CarbonIntensity.css";
import "./TopBarFilters.css";

interface Facility {
  id: string | number;
  name: string;
  field?: string;
  segment?: string;
  activity?: string;
  division?: string;
  [key: string]: any;
}

interface RegionalMethaneData {
  facility_id: string | number;
  facility_name: string;
  total_boe?: number;
  total_oil?: number;
  total_gas?: number;
  total_gas_m3?: number;
  flaring_volume?: number;
  flaring_emissions?: number;
  total_ch4?: number;
  methane_loss_rate_pct?: number | null;
  ch4_intensity?: number;
  segment_category?: string;
  wec_fee_usd?: number | null;
  wec_status?: string;
  wec_rate_usd_per_t?: number;
  [key: string]: any;
}

interface TrendItem {
  year: number | string;
  data: RegionalMethaneData[];
}

const MethaneIntensity: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();

  // Filter states
  const [currentActivity, setCurrentActivity] = useAnalyticsFilter("activity");
  const [currentDivision, setCurrentDivision] = useAnalyticsFilter("division");
  const [currentRegion, setCurrentRegion] = useAnalyticsFilter("region");
  const [currentSegment, setCurrentSegment] = useAnalyticsFilter("segment");
  const [selectedYear, setSelectedYear] = useAnalyticsFilter("year");
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [availableYears, setAvailableYears] = useState<(string | number)[]>([]);
  const [availableSegments, setAvailableSegments] = useState<string[]>([]);

  // View states
  const [trendView, setTrendView] = useState<"chart" | "heatmap">("chart");
  const [exporting, setExporting] = useState<boolean>(false);
  const [ogmpCollapsed, setOgmpCollapsed] = useState<boolean>(true);
  const [roadmapCollapsed, setRoadmapCollapsed] = useState<boolean>(true);
  const [selectedBaselineYear, setSelectedBaselineYear] = useState<number>(2023);
  const [globalThreshold, setGlobalThreshold] = useState<number>(20.0);
  const [upstreamTargetPct, setUpstreamTargetPct] = useState<number>(0.2);
  const [midstreamTargetPct, setMidstreamTargetPct] = useState<number>(0.05);

  // Data states
  const [stats, setStats] = useState<MethaneIntensityStats>({
    avgCh4Intensity: 0,
    avgMethaneLossRatePct: 0,
    upstreamLossRatePct: 0,
    midstreamLossRatePct: 0,
    avgFlaringRatePct: 0,
    totalCh4Emissions: 0,
    totalCh4VolumeM3: 0,
    totalGasProductionM3: 0,
    totalGasProductionMscf: 0,
    totalOilProduction: 0,
    totalBoe: 0,
    totalFlaringVolume: 0,
    totalFlaringEmissions: 0,
    totalWecFeeUsd: 0,
    ogmpGoldStatus: "Compliant",
    upstreamGasM3: 0,
    upstreamCh4Tonnes: 0,
    midstreamGasM3: 0,
    midstreamCh4Tonnes: 0,
  });

  const [regionalData, setRegionalData] = useState<RegionalMethaneData[]>([]);
  const [ogmpSurveys, setOgmpSurveys] = useState<any[]>([]);
  const [ogmpRoadmapData, setOgmpRoadmapData] = useState<any[]>([]);
  const [rawTrendData, setRawTrendData] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const isFirstLoadRef = useRef<boolean>(true);

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        const [facRes, filterRes, settingsRes] = await Promise.all([
          api.get("/facilities"),
          api.get("/filters/available"),
          api.get("/auth/settings").catch(() => ({ data: {} })),
        ]);
        const facilitiesData: Facility[] = Array.isArray(facRes.data)
          ? facRes.data
          : facRes.data?.data || [];
        setFacilities(facilitiesData);

        if (settingsRes.data) {
          if (settingsRes.data.ogmp_default_base_year) {
            setSelectedBaselineYear(
              Number(settingsRes.data.ogmp_default_base_year),
            );
          }
          if (settingsRes.data.reconciliation_threshold) {
            setGlobalThreshold(
              Number(settingsRes.data.reconciliation_threshold),
            );
          }
          if (settingsRes.data.ogmp_upstream_target_pct !== undefined) {
            setUpstreamTargetPct(
              Number(settingsRes.data.ogmp_upstream_target_pct),
            );
          }
          if (settingsRes.data.ogmp_midstream_target_pct !== undefined) {
            setMidstreamTargetPct(
              Number(settingsRes.data.ogmp_midstream_target_pct),
            );
          }
        }

        if (filterRes.data && filterRes.data.years) {
          setAvailableYears(filterRes.data.years);
        } else {
          setAvailableYears([]); // no invented years when the filter list is unavailable
        }
        if (filterRes.data && filterRes.data.segments) {
          const VALID_SUPPLY_CHAIN = ["upstream", "midstream", "downstream"];
          const filteredSegments = (filterRes.data.segments as string[]).filter(s =>
            VALID_SUPPLY_CHAIN.includes(String(s).trim().toLowerCase())
          );
          setAvailableSegments(filteredSegments.length > 0 ? filteredSegments : ["Downstream", "Midstream", "Upstream"]);
        }

        const opDefaults = getUserOperationalDefaults(user, facilitiesData);
        if (opDefaults.isRestricted || facilitiesData.length === 1) {
          if (opDefaults.defaultActivity) setCurrentActivity(opDefaults.defaultActivity);
          if (opDefaults.defaultDivision) setCurrentDivision(opDefaults.defaultDivision);
          if (opDefaults.defaultFacilityId) setCurrentRegion(opDefaults.defaultFacilityId);
        }
      } catch (error) {
        console.error("Initialization error:", error);
      }
    };
    init();
  }, [user]);

  // Load data on filter changes
  useEffect(() => {
    loadMethaneData();
    loadOgmpData();
    loadRoadmapData();
  }, [
    currentActivity,
    currentDivision,
    currentRegion,
    selectedYear,
    currentSegment,
  ]);

  // Load trend data
  useEffect(() => {
    if (selectedYear) {
      loadTrendData(selectedYear);
    }
  }, [selectedYear, currentActivity, currentDivision, currentSegment, currentRegion]);

  const loadMethaneData = async () => {
    try {
      if (isFirstLoadRef.current) {
        setLoading(true);
      } else {
        setIsUpdating(true);
      }
      const params = new URLSearchParams({
        year: String(selectedYear),
        facilityId: currentRegion,
        activity: currentActivity,
        division: currentDivision,
      });
      if (currentSegment !== "all") {
        params.append("segment", currentSegment);
      }

      const res = await api.get(`/dashboard/intensity-stats?${params}`);
      const data: RegionalMethaneData[] = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setRegionalData(data);

      let tOil = 0,
        tGasMscf = 0,
        tGasM3 = 0,
        tBoe = 0,
        tFlaringVol = 0,
        tFlaringEm = 0;
      let wCh4Sum = 0,
        tCh4Tonnes = 0,
        tCh4WithGas = 0,
        tWecFee = 0;
      // the WEC is assessed per calendar year: the server returns no fee for "all years"
      let wecAssessed = false;
      let wecRate: number | null = null; // the rate the server applied (Settings), not the statutory default
      let wecReason: string | null = null; // why no charge was assessed (e.g. the charge starts with 2034 emissions)

      let upGasM3 = 0,
        upCh4Tonnes = 0;
      let midGasM3 = 0,
        midCh4Tonnes = 0;

      data.forEach((d) => {
        const boe = d.total_boe || 0;
        const gasM3 = d.total_gas_m3 || (d.total_gas || 0) * 28.3168;
        const ch4Tonnes = d.total_ch4 || 0;
        // BUG-086: one server-side segment classifier (segment_category) for KPI cards, trend and targets
        const seg = d.segment_category || "";

        tOil += d.total_oil || 0;
        tGasMscf += d.total_gas || 0;
        tGasM3 += gasM3;
        tFlaringVol += d.flaring_volume || 0;
        tFlaringEm += d.flaring_emissions || 0;
        tCh4Tonnes += ch4Tonnes;
        if (gasM3 > 0) tCh4WithGas += ch4Tonnes; // loss-rate numerator: facilities with gas production
        tWecFee += d.wec_fee_usd || 0;
        if (d.wec_fee_usd != null) wecAssessed = true;
        else if (!wecReason && d.wec_status) wecReason = d.wec_status;
        if (d.wec_rate_usd_per_t) wecRate = d.wec_rate_usd_per_t;
        // loss rate numerator and denominator cover the same facilities (those with gas production)
        if (seg === "midstream" && gasM3 > 0) {
          midGasM3 += gasM3;
          midCh4Tonnes += ch4Tonnes;
        } else if (seg === "upstream" && gasM3 > 0) {
          upGasM3 += gasM3;
          upCh4Tonnes += ch4Tonnes;
        }
        // "downstream" and unclassified records are intentionally excluded
        // from methane loss rate calculations.

        if (boe > 0) {
          wCh4Sum += (d.ch4_intensity || 0) * boe;
          tBoe += boe;
        }
      });

      // Methane density at the API Compendium standard conditions (60 F, 14.696 psia)
      const totalCh4VolM3 = (tCh4WithGas * 1000.0) / CH4_DENSITY_KG_M3;
      const avgLossRatePct =
        tGasM3 > 0 ? (totalCh4VolM3 / tGasM3) * 100.0 : 0.0;

      const upCh4VolM3 = (upCh4Tonnes * 1000.0) / CH4_DENSITY_KG_M3;
      const midCh4VolM3 = (midCh4Tonnes * 1000.0) / CH4_DENSITY_KG_M3;
      const upstreamLossRatePct =
        upGasM3 > 0 ? (upCh4VolM3 / upGasM3) * 100.0 : 0.0;
      const midstreamLossRatePct =
        midGasM3 > 0 ? (midCh4VolM3 / midGasM3) * 100.0 : 0.0;

      const avgFlaringRatePct =
        tGasM3 > 0 ? (tFlaringVol / tGasM3) * 100.0 : 0.0;

      let goldStatus = "Compliant";
      if (tGasM3 === 0 && tCh4Tonnes > 0) {
        goldStatus = "Pending Production";
      } else if (
        (upGasM3 > 0 && upstreamLossRatePct > upstreamTargetPct * 1.25) ||
        (midGasM3 > 0 && midstreamLossRatePct > midstreamTargetPct * 1.25) ||
        (tGasM3 > 0 && avgLossRatePct > upstreamTargetPct * 1.25)
      ) {
        goldStatus = "Non-Compliant";
      } else if (
        (upGasM3 > 0 && upstreamLossRatePct > upstreamTargetPct) ||
        (midGasM3 > 0 && midstreamLossRatePct > midstreamTargetPct) ||
        (tGasM3 > 0 && avgLossRatePct > upstreamTargetPct)
      ) {
        goldStatus = "Warning";
      }

      setStats({
        avgCh4Intensity: tBoe > 0 ? wCh4Sum / tBoe : 0,
        avgMethaneLossRatePct: avgLossRatePct,
        upstreamLossRatePct: upstreamLossRatePct,
        midstreamLossRatePct: midstreamLossRatePct,
        avgFlaringRatePct: avgFlaringRatePct,
        totalCh4Emissions: tCh4Tonnes,
        totalCh4VolumeM3: totalCh4VolM3,
        totalGasProductionM3: tGasM3,
        totalGasProductionMscf: tGasMscf,
        totalOilProduction: tOil,
        totalBoe: tBoe,
        totalFlaringVolume: tFlaringVol,
        totalFlaringEmissions: tFlaringEm,
        totalWecFeeUsd: tWecFee,
        wecAssessed,
        wecRate,
        wecReason,
        ogmpGoldStatus: goldStatus,
        upstreamGasM3: upGasM3,
        upstreamCh4Tonnes: upCh4Tonnes,
        midstreamGasM3: midGasM3,
        midstreamCh4Tonnes: midCh4Tonnes,
      });
    } catch (error) {
      console.error("Failed to load methane stats:", error);
      toast.error("Failed to load methane intensity metrics");
    } finally {
      setLoading(false);
      setIsUpdating(false);
      isFirstLoadRef.current = false;
    }
  };

  const loadOgmpData = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedYear && selectedYear !== "all")
        params.append("year", String(selectedYear));
      if (currentRegion && currentRegion !== "all")
        params.append("facilityId", currentRegion);
      if (currentSegment && currentSegment !== "all")
        params.append("segment", currentSegment);
      if (currentActivity && currentActivity !== "all")
        params.append("activity", currentActivity);
      if (currentDivision && currentDivision !== "all")
        params.append("division", currentDivision);
      const res = await api
        .get(`/data/ogmp-surveys?${params}`)
        .catch(() => ({ data: [] }));
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setOgmpSurveys(data);
    } catch (error) {
      console.error("OGMP load error:", error);
    }
  };

  const loadRoadmapData = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedYear && selectedYear !== "all")
        params.append("year", String(selectedYear));
      if (currentRegion && currentRegion !== "all")
        params.append("facilityId", currentRegion);
      if (currentSegment && currentSegment !== "all")
        params.append("segment", currentSegment);
      if (currentActivity && currentActivity !== "all")
        params.append("activity", currentActivity);
      if (currentDivision && currentDivision !== "all")
        params.append("division", currentDivision);
      const res = await api
        .get(`/dashboard/ogmp-metrics?${params}`)
        .catch(() => ({ data: {} }));
      if (res.data) {
        if (res.data.facilities) {
          setOgmpRoadmapData(res.data.facilities);
        }
        if (res.data.summary) {
          if (
            res.data.summary.global_default_base_year &&
            !selectedBaselineYear
          ) {
            setSelectedBaselineYear(
              Number(res.data.summary.global_default_base_year),
            );
          }
          if (res.data.summary.global_threshold) {
            setGlobalThreshold(Number(res.data.summary.global_threshold));
          }
          if (res.data.summary.upstream_target_pct !== undefined) {
            setUpstreamTargetPct(Number(res.data.summary.upstream_target_pct));
          }
          if (res.data.summary.midstream_target_pct !== undefined) {
            setMidstreamTargetPct(
              Number(res.data.summary.midstream_target_pct),
            );
          }
        }
      }
    } catch (error) {
      console.error("OGMP Roadmap load error:", error);
    }
  };

  const loadTrendData = async (endYear: string | number) => {
    const years: number[] = [];
    const parsed = parseInt(String(endYear));
    const yearInt = isNaN(parsed) ? new Date().getFullYear() : parsed;
    for (let i = 4; i >= 0; i--) years.push(yearInt - i);

    try {
      const params = new URLSearchParams();
      if (currentActivity && currentActivity !== "all") {
        params.append("activity", currentActivity);
      }
      if (currentDivision && currentDivision !== "all") {
        params.append("division", currentDivision);
      }
      if (currentSegment && currentSegment !== "all") {
        params.append("segment", currentSegment);
      }
      if (currentRegion && currentRegion !== "all") {
        params.append("facilityId", currentRegion);
      }
      params.append("years", years.join(","));
      const res = await api
        .get(`/dashboard/intensity-trend?${params}`)
        .catch(() => ({ data: [] }));
      const trendData: TrendItem[] = Array.isArray(res.data)
        ? res.data
        : res.data?.data || [];
      setRawTrendData(trendData);
    } catch (error) {
      console.error("Trend load error:", error);
    }
  };

  const handleExportExcel = async () => {
    try {
      setExporting(true);
      // "all years": the latest year with data (it was always 2024)
      const latest = [...availableYears].map(String).sort().pop() || String(new Date().getFullYear());
      const yr = selectedYear !== "all" ? String(selectedYear) : latest;
      const params = new URLSearchParams({ year: yr });
      if (currentRegion && currentRegion !== "all") {
        params.append("facility_id", currentRegion);
      }
      if (currentSegment && currentSegment !== "all") {
        params.append("segment", currentSegment);
      }
      if (currentActivity && currentActivity !== "all") {
        params.append("activity", currentActivity);
      }
      if (currentDivision && currentDivision !== "all") {
        params.append("division", currentDivision);
      }
      const res = await api.get(`/reports/ogmp-export?${params.toString()}`, {
        responseType: "blob",
      });
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `OGMP_2.0_Methane_Report_${yr}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`OGMP 2.0 Excel Report for ${yr} downloaded successfully!`);
    } catch (err) {
      console.error("Export error:", err);
      toast.error("Failed to export OGMP Excel report");
    } finally {
      setExporting(false);
    }
  };

  // Filter helpers
  const handleSegmentChange = (val: string) => {
    setCurrentSegment(val);
    setCurrentActivity("all");
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleActivityChange = (val: string) => {
    setCurrentActivity(val);
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleDivisionChange = (val: string) => {
    setCurrentDivision(val);
    setCurrentRegion("all");
  };

  const getSegmentOptions = () => [
    { value: "all", label: "All Supply Chains" },
    ...availableSegments.map((s) => ({ value: s, label: s })),
  ];

  const getActivityOptions = () => {
    const filtered = facilities.filter(
      (f) => currentSegment === "all" || f.segment === currentSegment,
    );
    const activities = new Set(filtered.map((f) => f.activity).filter(Boolean));
    return [
      { value: "all", label: "All Activities" },
      ...Array.from(activities)
        .sort()
        .map((a) => ({ value: a as string, label: a as string })),
    ];
  };

  const getDivisionOptions = () => {
    let divisions = [{ value: "all", label: "All Divisions" }];
    const filtered = facilities.filter(
      (f) =>
        (currentSegment === "all" || f.segment === currentSegment) &&
        (currentActivity === "all" || f.activity === currentActivity),
    );
    const divs = new Set(filtered.map((f) => f.division).filter(Boolean));
    divisions.push(
      ...Array.from(divs)
        .sort()
        .map((d) => ({ value: d as string, label: d as string })),
    );
    return divisions;
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

  // TopBar layout integration
  useEffect(() => {
    setTopBarLeft(
      <div className="dashboard-filters">
        <div className="filter-wrapper">
          <CustomDropdown
            options={[
              { value: "all", label: "All Years" },
              ...availableYears.map((y) => ({
                value: y.toString(),
                label: y.toString(),
              })),
            ]}
            value={selectedYear}
            onChange={setSelectedYear}
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
      </div>,
    );

    setTopBarRight(
      <button
        className="[display:inline-flex] [align-items:center] [gap:8px] [background:linear-gradient(135deg,_var(--color-green-700)_0%,_var(--color-green-700)_100%)] [color:var(--color-white)] [font-size:var(--text-base)] [font-weight:600] [padding:8px_16px] [border-radius:var(--radius-md)] [border:none] [cursor:pointer] [box-shadow:0_4px_12px_rgba(16,_185,_129,_0.25)] [transition:all_0.2s_ease] [&:hover:not(:disabled)]:[transform:translateY(-1px)] [&:hover:not(:disabled)]:[box-shadow:0_6px_18px_rgba(16,_185,_129,_0.35)] disabled:[opacity:0.6] disabled:[cursor:not-allowed]"
        onClick={handleExportExcel}
        disabled={exporting}
        title="Download 5-Tab OGMP 2.0 Disclosure Workbook (.xlsx)"
      >
        <Download size={16} />
        {exporting ? "Exporting..." : "Export OGMP 2.0 (Excel)"}
      </button>,
    );

    return () => {
      setTopBarLeft(null);
      setTopBarRight(null);
    };
  }, [
    availableYears,
    selectedYear,
    currentActivity,
    currentDivision,
    currentRegion,
    currentSegment,
    facilities,
    exporting,
  ]);

  // Trend chart data
  const trendChartData = useMemo(() => {
    return rawTrendData.map((item) => {
      let yearData = item.data || [];
      if (currentRegion !== "all") {
        yearData = yearData.filter(
          (d) => d.facility_id.toString() === currentRegion,
        );
      }

      let wCh4 = 0,
        tBoe = 0,
        tGasM3 = 0,
        tCh4VolM3 = 0;
      let upGas = 0,
        upCh4 = 0;
      let midGas = 0,
        midCh4 = 0;

      yearData.forEach((d) => {
        const boe = d.total_boe || 0;
        const gasM3 = d.total_gas_m3 || (d.total_gas || 0) * 28.3168;
        const ch4Tonnes = d.total_ch4 || 0;
        const volM3 = (ch4Tonnes * 1000.0) / CH4_DENSITY_KG_M3;
        const seg = d.segment_category || ""; // BUG-086

        tGasM3 += gasM3;
        if (gasM3 > 0) tCh4VolM3 += volM3;

        if (seg === "midstream" && gasM3 > 0) {
          midGas += gasM3;
          midCh4 += volM3;
        } else if (seg === "upstream" && gasM3 > 0) {
          upGas += gasM3;
          upCh4 += volM3;
        }

        if (boe > 0) {
          wCh4 += (d.ch4_intensity || 0) * boe;
          tBoe += boe;
        }
      });

      const lossRate = tGasM3 > 0 ? (tCh4VolM3 / tGasM3) * 100.0 : 0.0;
      const upLossRate = upGas > 0 ? (upCh4 / upGas) * 100.0 : 0.0;
      const midLossRate = midGas > 0 ? (midCh4 / midGas) * 100.0 : 0.0;

      return {
        year: item.year,
        ch4_intensity: tBoe > 0 ? wCh4 / tBoe : 0,
        loss_rate_pct: lossRate,
        loss_rate_upstream_pct: upLossRate,
        loss_rate_midstream_pct: midLossRate,
        target_020: upstreamTargetPct,
        target_005: midstreamTargetPct,
      };
    });
  }, [rawTrendData, currentRegion, upstreamTargetPct, midstreamTargetPct]);

  const getHeatmapClass = (val: number | null | undefined): string => {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "heat-null";
    if (val < 0.05) return "heat-lux";
    if (val < 0.15) return "heat-low";
    if (val < 0.25) return "heat-mid";
    if (val < 0.5) return "heat-high";
    return "heat-crit";
  };

  if (loading && regionalData.length === 0)
    return (
      <LoadingSpinner
        message="Calculating Methane Intensity & Loss Rates..."
        fullScreen
      />
    );

  return (
    <div
      className="intensity-content"
      style={{
        opacity: isUpdating ? 0.82 : 1,
        transition: "opacity 0.2s ease",
      }}
    >
      <div className="intensity-grid [display:flex] [flex-direction:column] [gap:32px] [max-width:1600px] [margin:0_auto]">
        {/* KPI HERO CARD */}
        <MethaneIntensityMethaneIntensity
          midstreamTargetPct={midstreamTargetPct}
          selectedYear={selectedYear}
          stats={stats}
          upstreamTargetPct={upstreamTargetPct}
        />

        {/* OGMP 2.0 GOLD STANDARD PATHWAY & ROADMAP */}
        <MethaneIntensityOGMP20Gold
          facilities={facilities}
          globalThreshold={globalThreshold}
          ogmpRoadmapData={ogmpRoadmapData}
          ogmpSurveys={ogmpSurveys}
          roadmapCollapsed={roadmapCollapsed}
          selectedBaselineYear={selectedBaselineYear}
          selectedYear={selectedYear}
          setRoadmapCollapsed={setRoadmapCollapsed}
          setSelectedBaselineYear={setSelectedBaselineYear}
        />

        {/* OGMP 2.0 LEVEL 4/5 TOP-DOWN SURVEY RECONCILIATION SECTION */}
        <MethaneIntensityOGMP20Level
          globalThreshold={globalThreshold}
          ogmpCollapsed={ogmpCollapsed}
          ogmpSurveys={ogmpSurveys}
          regionalData={regionalData}
          setOgmpCollapsed={setOgmpCollapsed}
        />

        {/* Regional Bar Charts */}
        <div className="chart-grid [display:grid] [grid-template-columns:repeat(auto-fit,_minmax(450px,_1fr))]! [gap:24px] [@media(max-width:768px)]:[grid-template-columns:1fr]!">
          <div className="card">
            <div className="chart-header">
              <div className="[display:flex] [flex-direction:column] [gap:8px]">
                <h3>Methane Loss Rate by Facility (% of Gas Produced)</h3>
                <div
                  className="[width:32px] [height:4px] [border-radius:var(--radius-sm)] bg-[color:#2563eb]!"
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData
                  .filter((d) => d.methane_loss_rate_pct != null) /* BUG-088: no gas production = no rate */
                  .map((d) => ({
                    name: d.facility_name,
                    value: d.methane_loss_rate_pct || 0,
                  }))}
                dataKey="value"
                xKey="name"
                color="#2563eb"
              />
            </div>
          </div>

          <div className="card">
            <div className="chart-header">
              <div className="[display:flex] [flex-direction:column] [gap:8px]">
                <h3>Methane Intensity by Facility (kg CH₄ / BOE)</h3>
                <div
                  className="[width:32px] [height:4px] [border-radius:var(--radius-sm)] bg-[color:#ff6600]!"
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  value: d.ch4_intensity || 0,
                }))}
                dataKey="value"
                xKey="name"
                color="#ff6600"
              />
            </div>
          </div>

          <div className="card">
            <div className="chart-header">
              <div className="[display:flex] [flex-direction:column] [gap:8px]">
                <h3>Total Methane Emissions (tCH₄)</h3>
                <div
                  className="[width:32px] [height:4px] [border-radius:var(--radius-sm)] bg-[color:#3b82f6]!"
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  value: d.total_ch4 || 0,
                }))}
                dataKey="value"
                xKey="name"
                color="#3b82f6"
              />
            </div>
          </div>

          <div className="card">
            <div className="chart-header">
              <div className="[display:flex] [flex-direction:column] [gap:8px]">
                <h3>Gas Flaring Volume by Facility (m³)</h3>
                <div
                  className="[width:32px] [height:4px] [border-radius:var(--radius-sm)] bg-[color:#ea580c]!"
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  value: d.flaring_volume || 0,
                }))}
                dataKey="value"
                xKey="name"
                color="#ea580c"
              />
            </div>
          </div>
        </div>

        {/* Historical Trends Section */}
        <MethaneIntensityHistoricalMethaneTrends
          getHeatmapClass={getHeatmapClass}
          midstreamTargetPct={midstreamTargetPct}
          rawTrendData={rawTrendData}
          regionalData={regionalData}
          setTrendView={setTrendView}
          trendChartData={trendChartData}
          trendView={trendView}
          upstreamTargetPct={upstreamTargetPct}
        />
      </div>
    </div>
  );
};

export default MethaneIntensity;
