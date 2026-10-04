import CarbonIntensityCarbonIntensity from "./carbon-intensity/CarbonIntensityCarbonIntensity";
import { useAnalyticsFilter } from "../filters/useAnalyticsFilter";
import React, { useState, useEffect, useMemo, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { cn } from "../ui/cn";
import { CbamSection, RegionalCharts, TrendSection } from "./carbon-intensity/CarbonIntensitySections";
import { useLayout } from "../context/LayoutContext";
import CustomDropdown from "../components/CustomDropdown";
import { formatNumber } from "../utils/formatters";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import "./TopBarFilters.css";

const CarbonIntensity = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();

  // Filter states
  const [currentActivity, setCurrentActivity] = useAnalyticsFilter("activity");
  const [currentDivision, setCurrentDivision] = useAnalyticsFilter("division");
  const [currentRegion, setCurrentRegion] = useAnalyticsFilter("region");
  const [currentSegment, setCurrentSegment] = useAnalyticsFilter("segment");
  const [selectedYear, setSelectedYear] = useAnalyticsFilter("year");
  const [facilities, setFacilities] = useState([]);
  const [availableYears, setAvailableYears] = useState([]);
  const [availableSegments, setAvailableSegments] = useState([]);

  // GWP Horizon State: '100' or '20' & Active Standard
  const [gwpHorizon, setGwpHorizon] = useState("100");
  const [activeGwpStandard, setActiveGwpStandard] = useState("AR5");

  // View states
  const [trendView, setTrendView] = useState("chart"); // 'chart' or 'heatmap'

  // Data states
  const [stats, setStats] = useState({
    avgCo2Intensity: 0,
    avgCo2IntensityGwp20: 0,
    avgScope1Intensity: 0,
    avgScope1IntensityGwp20: 0,
    avgScope2Intensity: 0,
    avgScope3Intensity: 0,
    avgFlaringIntensity: 0,
    totalCo2Emissions: 0,
    totalCo2EmissionsGwp20: 0,
    totalScope1: 0,
    totalScope1Gwp20: 0,
    totalScope2: 0,
    totalScope3: 0,
    totalFlaringEmissions: 0,
    totalOilProduction: 0,
    totalGasProduction: 0,
    totalBoe: 0,
    totalFlaringVolume: 0 });

  const [isReady, setIsReady] = useState(false);
  const [regionalData, setRegionalData] = useState([]);
  const [rawTrendData, setRawTrendData] = useState([]);
  const [cbamProducts, setCbamProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const isFirstLoadRef = useRef(true);

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        const [facRes, filterRes, settingsRes] = await Promise.all([
          api.get("/facilities"),
          api.get("/filters/available"),
          api.get("/auth/settings").catch(() => ({ data: {} })),
        ]);
        const facilitiesData = Array.isArray(facRes.data)
          ? facRes.data
          : facRes.data?.data || [];
        setFacilities(facilitiesData);

        if (settingsRes?.data?.gwp_standard) {
          setActiveGwpStandard(settingsRes.data.gwp_standard);
        }

        if (filterRes.data && filterRes.data.years) {
          setAvailableYears(filterRes.data.years);
        } else {
          setAvailableYears([]); // no invented years when the filter list is unavailable
        }
        if (filterRes.data && filterRes.data.segments) {
          setAvailableSegments(filterRes.data.segments);
        }

        const opDefaults = getUserOperationalDefaults(user, facilitiesData);
        if (opDefaults.isRestricted || facilitiesData.length === 1) {
          if (opDefaults.defaultActivity) setCurrentActivity(opDefaults.defaultActivity);
          if (opDefaults.defaultDivision) setCurrentDivision(opDefaults.defaultDivision);
          if (opDefaults.defaultFacilityId) setCurrentRegion(opDefaults.defaultFacilityId);
        }
        setIsReady(true);
      } catch (error) {
        console.error("Initialization error:", error);
        setIsReady(true);
      }
    };
    init();
  }, [user]);

  // Load data on filter changes
  useEffect(() => {
    if (!isReady) return;
    loadIntensityData();
  }, [
    isReady,
    currentActivity,
    currentDivision,
    currentRegion,
    selectedYear,
    currentSegment,
  ]);

  // Load trend data
  useEffect(() => {
    if (!isReady) return;
    if (selectedYear) {
      loadTrendData(selectedYear);
    }
  }, [isReady, selectedYear, currentActivity, currentDivision, currentSegment, currentRegion]);

  useEffect(() => {
    if (!isReady) return;
    loadCbamData();
  }, [isReady, selectedYear, currentRegion, currentActivity, currentDivision, currentSegment]);

  const loadCbamData = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedYear && selectedYear !== 'all') params.append('year', selectedYear);
      if (currentRegion && currentRegion !== 'all') params.append('facilityId', currentRegion);
      if (currentActivity && currentActivity !== 'all') params.append('activity', currentActivity);
      if (currentDivision && currentDivision !== 'all') params.append('division', currentDivision);
      if (currentSegment && currentSegment !== 'all') params.append('segment', currentSegment);
      const res = await api.get(`/data/cbam-exports?${params.toString()}`);
      setCbamProducts(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error('Failed to load CBAM exports:', error);
    }
  };

  const loadIntensityData = async () => {
    try {
      if (isFirstLoadRef.current) {
        setLoading(true);
      } else {
        setIsUpdating(true);
      }
      const params = new URLSearchParams({
        year: selectedYear,
        facilityId: currentRegion,
        activity: currentActivity,
        division: currentDivision });
      if (currentSegment !== "all") {
        params.append("segment", currentSegment);
      }

      const res = await api.get(`/dashboard/intensity-stats?${params}`);
      const data = Array.isArray(res.data) ? res.data : res.data?.data || [];
      setRegionalData(data);

      let tOil = 0,
        tGas = 0,
        tBoe = 0,
        tFlaringVol = 0,
        tFlaringEm = 0;
      let wCo2Sum = 0,
        wCo2Gwp20Sum = 0,
        wS1Sum = 0,
        wS1Gwp20Sum = 0,
        wS2Sum = 0,
        wS3Sum = 0,
        wFlaringSum = 0;
      let tScope1 = 0,
        tScope1Gwp20 = 0,
        tScope2 = 0,
        tScope3 = 0,
        tCo2e = 0,
        tCo2eGwp20 = 0;

      data.forEach((d) => {
        const boe = d.total_boe || 0;
        tOil += d.total_oil || 0;
        tGas += d.total_gas || 0;
        tFlaringVol += d.flaring_volume || 0;
        tFlaringEm += d.flaring_emissions || 0;
        tScope1 += d.total_scope1 || 0;
        tScope1Gwp20 += d.total_scope1_gwp20 ?? d.total_scope1 ?? 0;
        tScope2 += d.total_scope2 || 0;
        tScope3 += d.total_scope3 || 0;
        tCo2e += d.total_co2e || 0;
        tCo2eGwp20 += d.total_co2e_gwp20 || d.total_co2e || 0;

        if (boe > 0) {
          wCo2Sum += (d.co2_intensity || 0) * boe;
          wCo2Gwp20Sum += (d.co2_intensity_gwp20 || d.co2_intensity || 0) * boe;
          wS1Sum += (d.scope1_intensity || 0) * boe;
          wS1Gwp20Sum += (d.scope1_intensity_gwp20 ?? d.scope1_intensity ?? 0) * boe;
          wS2Sum += (d.scope2_intensity || 0) * boe;
          wS3Sum += (d.scope3_intensity || 0) * boe;
          wFlaringSum += (d.api_flaring_intensity || 0) * boe;
          tBoe += boe;
        }
      });

      setStats({
        avgCo2Intensity: tBoe > 0 ? wCo2Sum / tBoe : (tCo2e > 0 ? null : 0),
        avgCo2IntensityGwp20: tBoe > 0 ? wCo2Gwp20Sum / tBoe : (tCo2eGwp20 > 0 ? null : 0),
        avgScope1Intensity: tBoe > 0 ? wS1Sum / tBoe : (tScope1 > 0 ? null : 0),
        avgScope1IntensityGwp20: tBoe > 0 ? wS1Gwp20Sum / tBoe : (tScope1Gwp20 > 0 ? null : 0),
        avgScope2Intensity: tBoe > 0 ? wS2Sum / tBoe : (tScope2 > 0 ? null : 0),
        avgScope3Intensity: tBoe > 0 ? wS3Sum / tBoe : (tScope3 > 0 ? null : 0),
        avgFlaringIntensity: tBoe > 0 ? wFlaringSum / tBoe : (tFlaringEm > 0 ? null : 0),
        totalCo2Emissions: tCo2e,
        totalCo2EmissionsGwp20: tCo2eGwp20,
        totalScope1: tScope1,
        totalScope1Gwp20: tScope1Gwp20,
        totalScope2: tScope2,
        totalScope3: tScope3,
        totalFlaringEmissions: tFlaringEm,
        totalOilProduction: tOil,
        totalGasProduction: tGas,
        totalBoe: tBoe,
        totalFlaringVolume: tFlaringVol,
        // the intensity numerators: facility-years with production only (the totals cover every year)
        usedCo2e: wCo2Sum / 1000,
        usedCo2eGwp20: wCo2Gwp20Sum / 1000,
        usedScope1: wS1Sum / 1000,
        usedScope1Gwp20: wS1Gwp20Sum / 1000,
        usedScope3: wS3Sum / 1000,
        usedFlaring: wFlaringSum / 1000 });
    } catch (error) {
      console.error("Failed to load intensity stats:", error);
      toast.error("Failed to load carbon intensity metrics");
    } finally {
      setLoading(false);
      setIsUpdating(false);
      isFirstLoadRef.current = false;
    }
  };

  const loadTrendData = async (endYear) => {
    const years = [];
    const yearInt = isNaN(parseInt(endYear))
      ? new Date().getFullYear()
      : parseInt(endYear);
    for (let i = 4; i >= 0; i--) years.push(yearInt - i);

    try {
      const params = new URLSearchParams({
        activity: currentActivity,
        division: currentDivision });
      if (currentSegment !== "all") {
        params.append("segment", currentSegment);
      }
      if (currentRegion && currentRegion !== "all") {
        params.append("facilityId", currentRegion);
      }
      params.append("years", years.join(","));
      const res = await api
        .get(`/dashboard/intensity-trend?${params}`)
        .catch(() => ({ data: [] }));
      const trendData = Array.isArray(res.data)
        ? res.data
        : res.data?.data || [];
      setRawTrendData(trendData);
    } catch (error) {
      console.error("Trend load error:", error);
    }
  };

  // Filter helpers
  const handleSegmentChange = (val) => {
    setCurrentSegment(val);
    setCurrentActivity("all");
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleActivityChange = (val) => {
    setCurrentActivity(val);
    setCurrentDivision("all");
    setCurrentRegion("all");
  };

  const handleDivisionChange = (val) => {
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
    const activities = new Set(filtered.map((f) => f.activity));
    return [
      { value: "all", label: "All Activities" },
      ...Array.from(activities)
        .sort()
        .map((a) => ({ value: a, label: a })),
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
        .map((d) => ({ value: d, label: d })),
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
        subLabel: f.field })),
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
                label: y.toString() })),
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
  ]);

  // Trend chart data based on active GWP toggle
  const trendChartData = useMemo(() => {
    return rawTrendData.map((item) => {
      let yearData = item.data;
      if (currentRegion !== "all") {
        yearData = yearData.filter(
          (d) => d.facility_id.toString() === currentRegion,
        );
      }

      let wCo2 = 0,
        wCo2Gwp20 = 0,
        tBoe = 0;
      yearData.forEach((d) => {
        const boe = d.total_boe || 0;
        if (boe > 0) {
          wCo2 += (d.co2_intensity || 0) * boe;
          wCo2Gwp20 += (d.co2_intensity_gwp20 || d.co2_intensity || 0) * boe;
          tBoe += boe;
        }
      });

      return {
        year: item.year,
        co2_100: tBoe > 0 ? wCo2 / tBoe : 0,
        co2_20: tBoe > 0 ? wCo2Gwp20 / tBoe : 0,
        active_co2:
          tBoe > 0 ? (gwpHorizon === "20" ? wCo2Gwp20 / tBoe : wCo2 / tBoe) : 0 };
    });
  }, [rawTrendData, currentRegion, gwpHorizon]);

  const currentDisplayCo2Intensity =
    gwpHorizon === "20" ? stats.avgCo2IntensityGwp20 : stats.avgCo2Intensity;
  const currentDisplayTotalCo2e =
    gwpHorizon === "20"
      ? stats.totalCo2EmissionsGwp20
      : stats.totalCo2Emissions;
  const currentDisplayScope1Intensity =
    gwpHorizon === "20" ? stats.avgScope1IntensityGwp20 : stats.avgScope1Intensity;
  const currentDisplayTotalScope1 =
    gwpHorizon === "20" ? stats.totalScope1Gwp20 : stats.totalScope1;
  const currentUsedCo2e = gwpHorizon === "20" ? stats.usedCo2eGwp20 : stats.usedCo2e;
  const currentUsedScope1 = gwpHorizon === "20" ? stats.usedScope1Gwp20 : stats.usedScope1;

  // A card's total covers every year while its intensity only uses years with production: say how much
  // of the total is outside the intensity (the Scope 3 card showed 1.49 Gt next to 0.41 kg/BOE)
  const excludedNote = (total, used) => {
    const excluded = (total || 0) - (used || 0);
    if (!(excluded > Math.max(0.5, Math.abs(total || 0) * 1e-6))) return null;
    return (
      <p className="m-0 mt-2 text-sm text-warning-fg">{formatNumber(excluded)} t from years without production are not in this intensity</p>
    );
  };

  if (loading && regionalData.length === 0)
    return (
      <LoadingSpinner message="Calculating Carbon Intensity..." fullScreen />
    );

  return (
    <div className={cn("intensity-content min-h-[calc(100vh-64px)] bg-ink-50 p-4 transition-opacity duration-200 md:p-8", isUpdating && "opacity-80")}>
      <div className="intensity-grid mx-auto flex max-w-[1600px] flex-col gap-8">
        <CarbonIntensityCarbonIntensity
          activeGwpStandard={activeGwpStandard}
          currentDisplayCo2Intensity={currentDisplayCo2Intensity}
          currentDisplayScope1Intensity={currentDisplayScope1Intensity}
          currentDisplayTotalCo2e={currentDisplayTotalCo2e}
          currentDisplayTotalScope1={currentDisplayTotalScope1}
          currentUsedCo2e={currentUsedCo2e}
          currentUsedScope1={currentUsedScope1}
          excludedNote={excludedNote}
          gwpHorizon={gwpHorizon}
          selectedYear={selectedYear}
          setGwpHorizon={setGwpHorizon}
          stats={stats}
        />
        <CbamSection products={cbamProducts} facilities={facilities} />
        <RegionalCharts data={regionalData} gwpHorizon={gwpHorizon} />
        <TrendSection
          view={trendView}
          onView={setTrendView}
          trendChartData={trendChartData}
          rawTrendData={rawTrendData}
          regionalData={regionalData}
          gwpHorizon={gwpHorizon}
          activeGwpStandard={activeGwpStandard}
        />
      </div>
    </div>
  );
};

export default CarbonIntensity;
