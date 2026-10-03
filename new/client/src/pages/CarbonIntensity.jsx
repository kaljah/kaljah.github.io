import CarbonIntensityCarbonIntensity from "./carbon-intensity/CarbonIntensityCarbonIntensity";
import { useAnalyticsFilter } from "../filters/useAnalyticsFilter";
import React, { useState, useEffect, useMemo, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { BarChart, LineChart } from "../components/charts";
import { useLayout } from "../context/LayoutContext";
import CustomDropdown from "../components/CustomDropdown";
import { formatNumber } from "../utils/formatters";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import {
  Cloud,
  Flame,
  Activity,
  BarChart2,
  Grid,
  Layers,
  ShieldCheck,
  FileText,
  ToggleLeft,
  ToggleRight,
  ArrowUpRight } from "lucide-react";
import "./CarbonIntensity.css";
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

  const GAS_TO_BOE = 0.178;

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

  const getHeatmapClass = (val) => {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "heat-null";
    if (val < 18) return "heat-lux";
    if (val < 28) return "heat-low";
    if (val < 38) return "heat-mid";
    if (val < 48) return "heat-high";
    return "heat-crit";
  };

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
      <div className="[margin-top:8px]! [font-size:var(--text-sm)]! [color:var(--warning-color,_var(--color-amber-700))]!">
        {formatNumber(excluded)} t from years without production are not in this intensity
      </div>
    );
  };

  if (loading && regionalData.length === 0)
    return (
      <LoadingSpinner message="Calculating Carbon Intensity..." fullScreen />
    );

  return (
    <div
      className="intensity-content"
      style={{
        opacity: isUpdating ? 0.82 : 1,
        transition: "opacity 0.2s ease" }}
    >
      <div className="intensity-grid [display:flex]! [flex-direction:column] [gap:32px] [max-width:1600px]! [margin:0_auto]!">
        {/* KPI HERO CARD */}
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

                {/* EU CBAM COMPLIANCE & PRODUCT EMBODIMENT SECTION */}
                <div className="card cbam-section [display:flex]! [flex-direction:column]! [gap:16px]!">
                    <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [margin-bottom:24px]! [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:600]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]!">
                        <div>
                            <h3 className="flex! items-center! gap-[8px]!">
                                <FileText size={20} color="var(--accent-color)" />
                                EU CBAM Product Specific Embedded Emissions
                            </h3>
                            <p className="text-[color:var(--text-secondary)]! text-[length:0.875rem]! m-[4px_0_0_0]!">
                                Direct & indirect specific embedded emissions per export product (EU Regulation 2023/956)
                            </p>
                        </div>
                        <div className="cbam-benchmark-badge [background:rgba(255,_102,_0,_0.1)]! [color:var(--color-link)]! [padding:6px_14px]! [border-radius:var(--radius-md)]! [font-size:var(--text-sm)]! [font-weight:600]! [border:1px_solid_rgba(255,_102,_0,_0.2)]!">
                            EU ETS Benchmark (Product-Specific): ~0.025 - 1.2 tCO₂e/t
                        </div>
                    </div>

                    {cbamProducts.length > 0 ? (
                        <div className="table-responsive mt-[16px]!">
                            <table className="custom-table [width:100%]! [border-collapse:collapse]! [font-size:var(--text-base)]! [&_th]:[text-align:left]! [&_th]:[padding:12px_16px]! [&_th]:[color:var(--text-secondary)]! [&_th]:[font-weight:600]! [&_th]:[font-size:var(--text-sm)]! [&_th]:[text-transform:uppercase]! [&_th]:[letter-spacing:0.05em]! [&_th]:[border-bottom:2px_solid_var(--border-color)]! [&_td]:[padding:14px_16px]! [&_td]:[border-bottom:1px_solid_var(--border-color)]! [&_td]:[color:var(--text-primary)]! [&_tr:hover]:[background:var(--bg-hover)]!">
                                <thead>
                                    <tr>
                                        <th>Facility</th>
                                        <th>Product Name</th>
                                        <th>EU CN Code</th>
                                        <th>Period</th>
                                        <th>Export Qty (t)</th>
                                        <th>Destination</th>
                                        <th>Direct Intensity (tCO₂e/t)</th>
                                        <th>Indirect Intensity (tCO₂e/t)</th>
                                        <th>Total Embedded (tCO₂e)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {cbamProducts.map((p, idx) => {
                                        const fac = facilities.find(f => String(f.id) === String(p.facility_id));
                                        const facName = fac ? fac.name : (p.facilityName || p.facility_name || '—');
                                        const prodName = p.productName || p.product_name || '—';
                                        const cn = p.cnCode || p.cn_code || '—';
                                        const qty = p.quantityTonnes ?? p.quantity_tonnes ?? 0;
                                        const dest = p.exportDestination || p.export_destination || 'EU';
                                        const directInt = p.specificEmbeddedDirect ?? p.specific_embedded_direct;
                                        const indirInt = p.specificEmbeddedIndirect ?? p.specific_embedded_indirect;
                                        const totEmb = p.totalEmbeddedEmissions ?? p.total_embedded_emissions ?? (qty * ((directInt || 0) + (indirInt || 0)));
                                        return (
                                            <tr key={p.id || idx}>
                                                <td className="font-semibold!">{facName}</td>
                                                <td>{prodName}</td>
                                                <td><span className="code-pill [background:var(--bg-hover)]! [padding:3px_8px]! [border-radius:var(--radius-sm)]! [font-family:monospace]! [font-size:var(--text-sm)]! [color:var(--text-primary)]! [border:1px_solid_var(--border-color)]!">{cn}</span></td>
                                                <td>{p.year}-{String(p.month || 1).padStart(2, '0')}</td>
                                                <td>{formatNumber(qty, 0)}</td>
                                                <td>{dest}</td>
                                                <td><strong className="text-[color:#c2410c]!">{typeof directInt === 'number' ? directInt.toFixed(4) : '—'}</strong></td>
                                                <td>{typeof indirInt === 'number' ? indirInt.toFixed(4) : '—'}</td>
                                                <td><strong>{formatNumber(totEmb, 1)}</strong></td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="[display:flex]! [flex-direction:column] [align-items:center] [justify-content:center] [padding:40px_20px]! [color:var(--text-secondary)]! [font-size:var(--text-base)]!">
                            <p>No CBAM product export records registered for the selected filters. Track exports via <strong>Manage Data &gt; CBAM Products</strong>.</p>
                        </div>
                    )}
                </div>

        {/* Regional Bar Charts */}
        <div className="chart-grid [display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(450px,_1fr))] [gap:24px] [@media(max-width:768px)]:[grid-template-columns:1fr]!">
          <div className="card">
            <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [margin-bottom:24px]! [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:600]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]!">
              <div className="[display:flex]! [flex-direction:column] [gap:8px]">
                <h3>GHG Intensity by Facility (kg CO₂e / BOE)</h3>
                <div
                  className="[width:32px]! [height:4px]! [border-radius:var(--radius-sm)]! bg-[color:#ff6600]!"
                 
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  value:
                    gwpHorizon === "20"
                      ? d.co2_intensity_gwp20 || d.co2_intensity
                      : d.co2_intensity }))}
                dataKey="value"
                xKey="name"
                color="#ff6600"
              />
            </div>
          </div>

          <div className="card">
            <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [margin-bottom:24px]! [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:600]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]!">
              <div className="[display:flex]! [flex-direction:column] [gap:8px]">
                <h3>Scope 1 Direct vs Scope 2 Intensity</h3>
                <div
                  className="[width:32px]! [height:4px]! [border-radius:var(--radius-sm)]! bg-[color:#2563eb]!"
                 
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  scope1: Number(
                    (
                      (gwpHorizon === "20"
                        ? d.scope1_intensity_gwp20 || d.scope1_intensity
                        : d.scope1_intensity) || 0
                    ).toFixed(2)
                  ),
                  scope2: Number((d.scope2_intensity || 0).toFixed(2)) }))}
                bars={[
                  {
                    dataKey: "scope1",
                    name: gwpHorizon === "20" ? "Scope 1 (GWP₂₀ Direct)" : "Scope 1 (Direct)",
                    color: "#2563eb" },
                  { dataKey: "scope2", name: "Scope 2 (Indirect)", color: "#0ea5e9" },
                ]}
                xKey="name"
              />
            </div>
          </div>

          <div className="card">
            <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [margin-bottom:24px]! [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:600]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]!">
              <div className="[display:flex]! [flex-direction:column] [gap:8px]">
                <h3>Oil BOE Contribution by Facility</h3>
                <div
                  className="[width:32px]! [height:4px]! [border-radius:var(--radius-sm)]! bg-[color:#ea580c]!"
                 
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  value: d.total_oil || 0 }))}
                dataKey="value"
                xKey="name"
                color="#ea580c"
              />
            </div>
          </div>

          <div className="card">
            <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [margin-bottom:24px]! [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:600]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]!">
              <div className="[display:flex]! [flex-direction:column] [gap:8px]">
                <h3>Gas BOE Contribution by Facility</h3>
                <div
                  className="[width:32px]! [height:4px]! [border-radius:var(--radius-sm)]! bg-[color:#8b5cf6]!"
                 
                ></div>
              </div>
            </div>
            <div className="h-[300px]!">
              <BarChart
                data={regionalData.map((d) => ({
                  name: d.facility_name,
                  value: (d.total_gas || 0) * GAS_TO_BOE }))}
                dataKey="value"
                xKey="name"
                color="#8b5cf6"
              />
            </div>
          </div>
        </div>

        {/* Historical Trends Section */}
        <div className="card trend-section [margin-top:8px]!">
          <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [margin-bottom:24px]! [&_h3]:[font-size:var(--text-lg)]! [&_h3]:[font-weight:600]! [&_h3]:[color:var(--text-primary)]! [&_h3]:[margin:0]!">
            <div>
              <h3 className="mb-[4px]!">
                Historical Carbon Intensity Trends
              </h3>
              <p
                className="text-[color:var(--text-secondary)]! text-[length:0.9rem]! m-[0px]!"
              >
                5-Year Performance Track (kg CO₂e / BOE)
              </p>
            </div>
            <div className="[display:flex]! [gap:12px] [align-items:center]">
              <div className="[background:var(--bg-hover)]! [padding:4px]! [border-radius:var(--radius-md)]! [display:flex]! [gap:4px] [border:1px_solid_var(--border-color)]!">
                <button
                  className={`view-btn [border:none]! [padding:6px_16px]! [&&]:[border-radius:var(--radius-sm)]! [cursor:pointer]! [font-size:var(--text-base)]! [font-weight:500]! [transition:all_0.2s]! [background:transparent]! [color:var(--text-secondary)]! [display:flex]! [align-items:center]! [gap:6px]! [&.active]:[background:var(--bg-card)]! [&.active]:[color:var(--text-primary)]! [&.active]:[box-shadow:var(--card-shadow)]! [&.active]:[font-weight:600]! ${trendView === "chart" ? "active" : ""}`}
                  onClick={() => setTrendView("chart")}
                >
                  <BarChart2 size={16} /> Chart
                </button>
                <button
                  className={`view-btn [border:none]! [padding:6px_16px]! [&&]:[border-radius:var(--radius-sm)]! [cursor:pointer]! [font-size:var(--text-base)]! [font-weight:500]! [transition:all_0.2s]! [background:transparent]! [color:var(--text-secondary)]! [display:flex]! [align-items:center]! [gap:6px]! [&.active]:[background:var(--bg-card)]! [&.active]:[color:var(--text-primary)]! [&.active]:[box-shadow:var(--card-shadow)]! [&.active]:[font-weight:600]! ${trendView === "heatmap" ? "active" : ""}`}
                  onClick={() => setTrendView("heatmap")}
                >
                  <Grid size={16} /> Heatmap
                </button>
              </div>
            </div>
          </div>

          {trendView === "chart" ? (
            <div className="h-[350px]!">
              <LineChart
                data={trendChartData}
                xKey="year"
                series={[
                  {
                    key: "co2_100",
                    color: "#c2410c",
                    name: `GHG Intensity (${activeGwpStandard} 100-Yr GWP)` },
                  {
                    key: "co2_20",
                    color: "#ea580c",
                    name: `GHG Intensity (${activeGwpStandard} 20-Yr GWP)`,
                    dash: "5 5" },
                ]}
              />
            </div>
          ) : (
            <div className="heatmap-container [margin-top:24px]! [overflow-x:auto]! [background:var(--bg-app)]! [border-radius:var(--radius-md)]! [border:1px_solid_var(--border-color)]! [padding:16px]!">
              <div className="heatmap-header [display:grid]! [grid-template-columns:200px_repeat(5,_1fr)] [gap:12px] [margin-bottom:16px]! [padding:0_12px]!">
                <div
                  className="[font-size:var(--text-sm)]! [font-weight:700]! [color:var(--text-secondary)]! [text-transform:uppercase]! [text-align:center]! [letter-spacing:0.05em] text-left!"
                 
                >
                  FACILITY / REGION
                </div>
                {rawTrendData.map((d) => (
                  <div key={d.year} className="[font-size:var(--text-sm)]! [font-weight:700]! [color:var(--text-secondary)]! [text-transform:uppercase]! [text-align:center]! [letter-spacing:0.05em]">
                    {d.year}
                  </div>
                ))}
              </div>
              <div className="heatmap-body">
                {regionalData.length > 0 ? (
                  regionalData.map((facData) => (
                    <div key={facData.facility_id} className="heatmap-row [display:grid]! [grid-template-columns:200px_repeat(5,_1fr)] [gap:12px] [padding:12px]! [border-bottom:1px_solid_var(--border-color)]! [align-items:center] [transition:background-color_0.2s]! last:[border-bottom:none]! hover:[background:var(--bg-card)]! hover:[border-radius:var(--radius-md)]! hover:[box-shadow:var(--shadow-xs)]!">
                      <div className="[font-weight:600]! [font-size:var(--text-base)]! [color:var(--text-primary)]!">
                        {facData.facility_name}
                      </div>
                      {rawTrendData.map((yData) => {
                        const record = yData.data.find(
                          (r) => r.facility_id === facData.facility_id,
                        );
                        const rawVal = record
                          ? gwpHorizon === "20"
                            ? record.co2_intensity_gwp20 || record.co2_intensity
                            : record.co2_intensity
                          : 0;
                        const numVal = Number(rawVal);
                        const val = isFinite(numVal) ? numVal : 0;
                        return (
                          <div
                            key={yData.year}
                            className={`[padding:10px]! [border-radius:var(--radius-sm)]! [text-align:center]! [font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-white)]! [transition:transform_0.2s_ease,_filter_0.2s_ease]! [cursor:default]! [display:flex]! [align-items:center]! [justify-content:center]! [min-height:40px]! hover:[transform:scale(1.02)]! hover:[filter:brightness(1.1)]! ${getHeatmapClass(val)}`}
                            title={`${yData.year} Intensity: ${val.toFixed(3)} kg CO2e/BOE`}
                          >
                            {val > 0 ? val.toFixed(2) : "-"}
                          </div>
                        );
                      })}
                    </div>
                  ))
                ) : (
                  <p
                    className="text-center! p-[40px]! text-[color:var(--text-secondary)]!"
                  >
                    No regional data available
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CarbonIntensity;
