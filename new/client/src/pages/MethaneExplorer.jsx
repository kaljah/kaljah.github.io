import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  MapContainer,
  TileLayer,
  Marker,
  Circle,
  Tooltip,
  useMap,
  ZoomControl,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  Search,
  Filter,
  X,
  MapPin,
  Activity,
  Wind,
  Flame,
  TrendingUp,
  Info,
  Satellite,
  Radio,
  Layers,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Download,
  RefreshCw,
  Sliders,
  Zap,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Compass,
  Maximize2,
  Copy,
  Check,
  BarChart3,
  Target,
  RotateCcw,
  Calendar,
  Building,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { getUserOperationalDefaults, isUnrestrictedLocation } from "../utils/userDefaults";
import "./MethaneExplorer.css";

// Fix Leaflet tile sizing when mounted inside animated route transitions
const MapController = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    if (
      center &&
      Array.isArray(center) &&
      center.length === 2 &&
      !isNaN(center[0]) &&
      !isNaN(center[1])
    ) {
      map.flyTo(center, zoom, { duration: 1.2 });
    }
  }, [center, zoom, map]);

  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 350);
    return () => clearTimeout(timer);
  }, [map]);

  return null;
};

// Light-themed basemap options (no dark theme)
const BASE_MAPS = {
  streets: {
    name: "Standard Vector",
    url: "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=en&gl=DZ",
    attribution:
      '&copy; <a href="https://www.google.com/maps">Google Maps</a>',
    icon: Layers,
  },
};

const EmissionsMap = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast?.() || {
    success: console.log,
    error: console.error,
    info: console.log,
  };

  // Core Data States (All fetched from authentic backend endpoints)
  const [facilities, setFacilities] = useState([]);
  const [stats, setStats] = useState([]);
  const [filteredFacilities, setFilteredFacilities] = useState([]);
  const [selectedFacility, setSelectedFacility] = useState(null);
  const [mapCenter, setMapCenter] = useState([31.68, 6.07]); // Default centered on Algerian basin
  const [mapZoom, setMapZoom] = useState(6);
  const [availableYears, setAvailableYears] = useState([]);
  const [availableRegions, setAvailableRegions] = useState([]);
  const [availableActivities, setAvailableActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const isFirstLoadRef = useRef(true);

  // Filters (Search, Region, Year, Activity, Severity)
  const [filters, setFilters] = useState({
    search: "",
    region: "all",
    year: "all",
    activity: "all",
    severity: "all", // 'all' | 'high' | 'medium' | 'baseline'
  });
  const [viewMode, setViewMode] = useState("methane"); // 'methane' (CH4 default) or 'total' (CO2e)
  const [mapBaseLayer, setMapBaseLayer] = useState("streets"); // Default clean light vector
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);
  const [showPlumeRings, setShowPlumeRings] = useState(true);
  const [showLegend, setShowLegend] = useState(true);
  const [copiedCoords, setCopiedCoords] = useState(false);

  // Copernicus Sentinel-5P Satellite States & Real Database Surveys
  const [satelliteConfig, setSatelliteConfig] = useState(null);
  const [showSatelliteLayer, setShowSatelliteLayer] = useState(true);
  const [satelliteOpacity, setSatelliteOpacity] = useState(0.75);
  const [satelliteObservation, setSatelliteObservation] = useState(null);
  const [loadingSatelliteData, setLoadingSatelliteData] = useState(false);
  const [existingSurveys, setExistingSurveys] = useState([]);
  const [loadingSurveys, setLoadingSurveys] = useState(false);
  const [exportingOgmp, setExportingOgmp] = useState(false);
  const [satelliteAlert, setSatelliteAlert] = useState(null);
  const [lastPollTime, setLastPollTime] = useState(null);
  const satellitePollRef = useRef(null);
  const selectedFacilityRef = useRef(null);

  // Initial Data Fetch from real backend endpoints
  const fetchData = async () => {
    try {
      if (isFirstLoadRef.current) {
        setLoading(true);
      } else {
        setIsUpdating(true);
      }
      const params = new URLSearchParams();
      if (filters.year && filters.year !== "all") {
        params.append("year", filters.year);
      }

      // Fetch authentic facilities from /api/facilities, verified intensity stats from /api/dashboard/intensity-stats,
      // and available years from /api/dashboard/years
      const [facRes, statRes, yearRes, satConfigRes] = await Promise.all([
        api.get("/facilities"),
        api.get(`/dashboard/intensity-stats?${params.toString()}`),
        api.get("/dashboard/years"),
        api
          .get("/satellite/sentinel5p/layer-config")
          .catch(() => ({ data: null })),
      ]);

      const fetchedFacilities = facRes.data || [];
      setFacilities(fetchedFacilities);
      setStats(statRes.data || []);
      setAvailableYears(yearRes.data || []);
      if (satConfigRes && satConfigRes.data) {
        setSatelliteConfig(satConfigRes.data);
      }

      // Derive distinct regions and activities directly from the database facilities
      const regions = [
        ...new Set(fetchedFacilities.flatMap((f) => [f.region_identifier, f.location]).filter(Boolean)),
      ].sort();
      const userLoc = (user?.location || '').trim();
      if (userLoc && !isUnrestrictedLocation(userLoc) && !regions.includes(userLoc)) {
        regions.unshift(userLoc);
      }
      setAvailableRegions(regions);

      const acts = [
        ...new Set(fetchedFacilities.map((f) => f.activity).filter(Boolean)),
      ].sort();
      setAvailableActivities(acts);

      const opDefaults = getUserOperationalDefaults(user, fetchedFacilities);
      if (opDefaults.isRestricted || fetchedFacilities.length === 1) {
        setFilters((prev) => ({
          ...prev,
          region: prev.region === 'all' && opDefaults.defaultRegion ? opDefaults.defaultRegion : prev.region,
          activity: prev.activity === 'all' && opDefaults.defaultActivity ? opDefaults.defaultActivity : prev.activity,
        }));
      }
    } catch (error) {
      console.error("Failed to load explorer data:", error);
      toast.error("Failed to initialize facility data from server");
    } finally {
      setLoading(false);
      setIsUpdating(false);
      isFirstLoadRef.current = false;
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters.year]);

  // Helper to retrieve verified intensity stats for any facility
  const getIntensityData = useCallback(
    (facilityId) => {
      return (
        stats.find((s) => Number(s.facility_id) === Number(facilityId)) || {
          co2_intensity: 0,
          ch4_intensity: 0,
          api_flaring_intensity: 0,
          total_boe: 0,
          total_co2e: 0,
          total_ch4: 0,
        }
      );
    },
    [stats]
  );

  // Multi-criteria facility filtering (Search, Region, Activity, Coordinates, Severity)
  useEffect(() => {
    const searchLower = (filters.search || "").toLowerCase().trim();
    const highThreshold = viewMode === "total" ? 50000 : 500;
    const medThreshold = viewMode === "total" ? 10000 : 100;

    const filtered = facilities.filter((f) => {
      // Region Filter — use region_identifier (= f.region ?? f.name) so facilities
      // uploaded via bulk uploader (where region=NULL) still match correctly.
      const matchesRegion =
        filters.region === "all" ||
        f.region_identifier === filters.region;

      // Activity Filter
      const matchesActivity =
        filters.activity === "all" ||
        (f.activity && f.activity === filters.activity);

      // Search Filter
      const name = (f.name || "").toLowerCase();
      const region = (f.region_identifier || "").toLowerCase();
      const division = (f.division || "").toLowerCase();
      const matchesSearch =
        !searchLower ||
        name.includes(searchLower) ||
        region.includes(searchLower) ||
        division.includes(searchLower);

      // Valid Coordinates check
      const lat = Number(f.latitude);
      const lon = Number(f.longitude);
      const hasCoords = !isNaN(lat) && !isNaN(lon) && lat !== 0 && lon !== 0;

      // Severity Filter
      let matchesSeverity = true;
      if (filters.severity !== "all") {
        const facilityStats = getIntensityData(f.id);
        const val =
          viewMode === "total"
            ? facilityStats.total_co2e || 0
            : facilityStats.total_ch4 || 0;
        if (filters.severity === "high") {
          matchesSeverity = val >= highThreshold;
        } else if (filters.severity === "medium") {
          matchesSeverity = val >= medThreshold && val < highThreshold;
        } else if (filters.severity === "baseline") {
          matchesSeverity = val < medThreshold;
        }
      }

      return (
        matchesRegion &&
        matchesActivity &&
        matchesSearch &&
        hasCoords &&
        matchesSeverity
      );
    });

    setFilteredFacilities(filtered);
  }, [filters, facilities, viewMode, getIntensityData]);

  // Keep a ref to selected facility so background polling has access without stale closures
  useEffect(() => {
    selectedFacilityRef.current = selectedFacility;
  }, [selectedFacility]);

  // Fetch real satellite observation and authentic database OGMP surveys for selected facility
  const fetchFacilityData = useCallback(async (facility) => {
    if (!facility) return;
    const targetFacilityId = facility.id;

    // 1. Fetch real OGMP survey records from database (/api/data/ogmp-surveys)
    setLoadingSurveys(true);
    api
      .get("/data/ogmp-surveys", { params: { facilityId: targetFacilityId } })
      .then((res) => {
        if (selectedFacilityRef.current?.id === targetFacilityId) {
          setExistingSurveys(res.data || []);
        }
      })
      .catch((err) => {
        console.warn("Could not fetch facility OGMP surveys:", err);
        if (selectedFacilityRef.current?.id === targetFacilityId) {
          setExistingSurveys([]);
        }
      })
      .finally(() => {
        if (selectedFacilityRef.current?.id === targetFacilityId) {
          setLoadingSurveys(false);
        }
      });

    // 2. Fetch Copernicus Sentinel-5P satellite observation (/api/satellite/sentinel5p/facility-timeseries)
    if (facility.latitude == null || facility.longitude == null) {
      setSatelliteObservation(null);
      return;
    }

    try {
      setLoadingSatelliteData(true);
      const res = await api.get("/satellite/sentinel5p/facility-timeseries", {
        params: {
          facility_id: facility.id,
          latitude: facility.latitude,
          longitude: facility.longitude,
        },
      });
      if (selectedFacilityRef.current?.id === targetFacilityId) {
        setSatelliteObservation(res.data);
      }
    } catch (err) {
      console.error("Error fetching satellite observation:", err);
      if (selectedFacilityRef.current?.id === targetFacilityId) {
        setSatelliteObservation({
          status: "error",
          authenticated: false,
          message: "Failed to connect to Copernicus CDSE.",
        });
      }
    } finally {
      if (selectedFacilityRef.current?.id === targetFacilityId) {
        setLoadingSatelliteData(false);
      }
    }
  }, []);

  // Query authentic facility records whenever selection changes
  useEffect(() => {
    if (!selectedFacility) {
      setSatelliteObservation(null);
      setExistingSurveys([]);
      return;
    }
    fetchFacilityData(selectedFacility);
  }, [selectedFacility, fetchFacilityData]);

  // Background polling for new satellite passes (every 30 mins)
  const pollSatellitePasses = useCallback(async () => {
    try {
      const res = await api.post("/satellite/sentinel5p/poll-new-passes");
      const { new_passes = 0, detections = [] } = res.data || {};
      setLastPollTime(new Date());
      if (new_passes > 0 && Array.isArray(detections) && detections.length > 0) {
        const sorted = [...detections].sort(
          (a, b) => (b.anomaly_ppb || 0) - (a.anomaly_ppb || 0)
        );
        const top = sorted[0];
        if (top) {
          setSatelliteAlert({
            count: new_passes,
            facility: top.facility_name,
            date: top.pass_date,
            time: top.pass_time,
            anomaly: Number(top.anomaly_ppb || 0),
            type: top.stream_type,
          });
          setTimeout(() => setSatelliteAlert(null), 12000);
        }
        const curr = selectedFacilityRef.current;
        if (curr && detections.some((d) => d.facility_id === curr.id)) {
          fetchFacilityData(curr);
        }
      }
    } catch (err) {
      // Silently ignore background polling network blips
    }
  }, [fetchFacilityData]);

  useEffect(() => {
    const initialTimeout = setTimeout(pollSatellitePasses, 5000);
    satellitePollRef.current = setInterval(pollSatellitePasses, 30 * 60 * 1000);
    return () => {
      clearTimeout(initialTimeout);
      clearInterval(satellitePollRef.current);
    };
  }, [pollSatellitePasses]);

  // Facility selection handler
  const handleSelectFacility = (fac) => {
    if (fac && fac.latitude != null && fac.longitude != null) {
      const lat = Number(fac.latitude);
      const lon = Number(fac.longitude);
      if (!isNaN(lat) && !isNaN(lon)) {
        setSelectedFacility(fac);
        setMapCenter([lat, lon]);
        setMapZoom(9);
      }
    }
  };

  // Export & reconcile survey into OGMP 2.0 Level 5 database ledger
  const handleExportToOgmp = async () => {
    if (
      !selectedFacility ||
      !satelliteObservation ||
      !satelliteObservation.summary
    )
      return;
    try {
      setExportingOgmp(true);
      const res = await api.post("/satellite/sentinel5p/export-to-ogmp", {
        facility_id: selectedFacility.id,
        observation_date:
          satelliteObservation.summary.latest_observation_date ||
          new Date().toISOString().split("T")[0],
        ch4_column_ppb: satelliteObservation.summary.mean_ch4_column_ppb,
        anomaly_ppb: satelliteObservation.summary.max_anomaly_ppb,
        estimated_emission_rate_kg_hr:
          satelliteObservation.summary.estimated_emission_rate_kg_hr,
        qa_score: satelliteObservation.summary.mean_qa_score,
        notes: `Sentinel-5P Level-3 CH4 Top-Down observation reconciliation for ${selectedFacility.name}`,
      });

      if (
        res.data &&
        (res.data.success ||
          res.status === 201 ||
          res.data.id ||
          res.data.survey_id)
      ) {
        const surveyId = res.data.survey_id || res.data.id || "";
        toast.success(
          `Top-Down Satellite record reconciled with OGMP 2.0 Ledger!${surveyId ? ` (Survey #${surveyId})` : ""}`
        );
        // Refresh real surveys list from database
        fetchFacilityData(selectedFacility);
      } else {
        toast.error(res.data?.message || "Failed to export survey to OGMP");
      }
    } catch (err) {
      console.error("Export to OGMP failed:", err);
      toast.error(
        err.response?.data?.message ||
          err.response?.data?.error ||
          "Failed to reconcile with OGMP ledger"
      );
    } finally {
      setExportingOgmp(false);
    }
  };

  // Copy coordinates to clipboard safely with fallback
  const handleCopyCoords = async () => {
    if (!selectedFacility) return;
    const text = `${Number(selectedFacility.latitude).toFixed(4)}, ${Number(selectedFacility.longitude).toFixed(4)}`;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        throw new Error("Clipboard API unavailable");
      }
      setCopiedCoords(true);
      setTimeout(() => setCopiedCoords(false), 2000);
    } catch (err) {
      try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
        setCopiedCoords(true);
        setTimeout(() => setCopiedCoords(false), 2000);
      } catch (fallbackErr) {
        toast.info(`Coordinates: ${text}`);
      }
    }
  };

  // Reset all filters to default
  const handleResetFilters = () => {
    setFilters({
      search: "",
      region: "all",
      year: "all",
      activity: "all",
      severity: "all",
    });
  };

  // Formatting helpers
  const formatCompact = (num) => {
    if (num == null || isNaN(num)) return "0";
    const n = Number(num);
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return Math.round(n).toLocaleString();
  };

  const getSeverityLevel = (val) => {
    const threshold = viewMode === "total" ? 10000 : 100;
    if (val > threshold * 5) return "high"; // Super-emitter
    if (val > threshold) return "medium";
    return "low";
  };

  // Marker pulse classes and custom div icons
  const createPulsingIcon = (val) => {
    const level = getSeverityLevel(val);
    const radius = level === "high" ? 14 : level === "medium" ? 10 : 7;
    const pClass =
      level === "high"
        ? "pulse-red"
        : level === "medium"
          ? "pulse-amber"
          : "pulse-emerald";

    return L.divIcon({
      className: `marker-pulse ${pClass}`,
      iconSize: [radius * 3.2, radius * 3.2],
      iconAnchor: [radius * 1.6, radius * 1.6],
    });
  };

  const createSolidIcon = (val, isSelected) => {
    const level = getSeverityLevel(val);
    const color =
      level === "high"
        ? "#ef4444"
        : level === "medium"
          ? "#f59e0b"
          : "#10b981";
    const baseRadius = level === "high" ? 8 : level === "medium" ? 6 : 5;
    const radius = isSelected ? baseRadius + 3 : baseRadius;
    const border = isSelected ? "2.5px solid #ff6600" : "2px solid #ffffff";
    const glow = isSelected
      ? "0 0 12px rgba(255,102,0,0.8)"
      : "0 1px 4px rgba(0,0,0,0.3)";

    return L.divIcon({
      className: `solid-marker ${isSelected ? "marker-selected" : ""}`,
      html: `<div style="
        width: ${radius * 2}px;
        height: ${radius * 2}px;
        border-radius: 50%;
        background: ${color};
        border: ${border};
        box-shadow: ${glow};
        transition: all 0.2s ease;
      "></div>`,
      iconSize: [radius * 2, radius * 2],
      iconAnchor: [radius, radius],
    });
  };

  // Aggregate Mission Telemetry Metrics from real DB intensity data
  const telemetryMetrics = useMemo(() => {
    let totalMethane = 0;
    let totalGhg = 0;
    let totalBoe = 0;
    let superEmitters = 0;

    filteredFacilities.forEach((f) => {
      const s = getIntensityData(f.id);
      totalMethane += Number(s.total_ch4 || 0);
      totalGhg += Number(s.total_co2e || 0);
      totalBoe += Number(s.total_boe || 0);
      if (Number(s.total_ch4 || 0) >= 500) {
        superEmitters += 1;
      }
    });

    const avgMethaneIntensity =
      totalBoe > 0 ? ((totalMethane * 1000) / totalBoe).toFixed(3) : "0.000";

    return {
      activeAssets: filteredFacilities.length,
      totalMethane,
      totalGhg,
      totalBoe,
      avgMethaneIntensity,
      superEmitters,
    };
  }, [filteredFacilities, getIntensityData]);

  // Reconciliation analysis for selected facility
  const reconciliationAnalysis = useMemo(() => {
    if (!selectedFacility || !satelliteObservation?.summary) return null;
    const s = getIntensityData(selectedFacility.id);
    const reportedCh4Tonnes = Number(s.total_ch4 || 0);
    const satelliteFluxTonnes = Number(
      satelliteObservation.summary.annualized_ch4_tonnes || 0
    );

    if (reportedCh4Tonnes <= 0 && satelliteFluxTonnes <= 0) {
      return {
        status: "baseline",
        label: "Baseline / Undetected",
        ratio: 1.0,
        deltaText: "Atmospheric concentrations within natural background.",
        color: "#10b981",
      };
    }

    if (reportedCh4Tonnes <= 0 && satelliteFluxTonnes > 0) {
      return {
        status: "unreported_anomaly",
        label: "Unreported Top-Down Flux",
        ratio: 99.0,
        deltaText: `Satellite detects ${satelliteFluxTonnes.toFixed(1)} tCH₄/yr with zero reported bottom-up emissions.`,
        color: "#ef4444",
      };
    }

    const ratio = satelliteFluxTonnes / reportedCh4Tonnes;
    if (ratio >= 1.35) {
      const pctExcess = Math.round((ratio - 1) * 100);
      return {
        status: "excess",
        label: "Satellite Detects Excess",
        ratio,
        deltaText: `Satellite top-down flux is +${pctExcess}% above reported inventory. Possible fugitive venting or flare malfunction.`,
        color: "#f59e0b",
      };
    } else if (ratio <= 0.65) {
      const pctDeficit = Math.round((1 - ratio) * 100);
      return {
        status: "deficit",
        label: "Below Satellite Detection",
        ratio,
        deltaText: `Satellite observation is -${pctDeficit}% lower than reported. May reflect intermittent operational shutdowns.`,
        color: "#0284c7",
      };
    } else {
      return {
        status: "concordant",
        label: "Reconciled (±35%)",
        ratio,
        deltaText: "Top-down observation confirms bottom-up accounting within acceptable scientific uncertainty.",
        color: "#10b981",
      };
    }
  }, [selectedFacility, satelliteObservation, getIntensityData]);

  const selectedStats = selectedFacility
    ? getIntensityData(selectedFacility.id)
    : null;
  const isSatelliteConnected = satelliteConfig && satelliteConfig.connected;

  if (loading) {
    return (
      <div className="methane-explorer-loading">
        <div className="telemetry-loader">
          <div className="scanner-line"></div>
          <Satellite size={34} className="spin-slow" color="#ff6600" />
        </div>
        <div className="loading-title">LOADING METHANE EXPLORER</div>
        <div className="loading-subtitle">
          Fetching operational facilities and emission inventories...
        </div>
      </div>
    );
  }

  return (
    <div
      className="methane-explorer"
      style={{
        opacity: isUpdating ? 0.92 : 1,
        transition: "opacity 0.2s ease",
      }}
    >
      {/* 1. TOP MISSION TELEMETRY HUD BAR (WHITE LIGHT THEME) */}
      <header className="mission-hud">
        <div className="hud-left">
          <div className="hud-brand">
            <div className="radar-ping">
              <span className="ping-core"></span>
              <span className="ping-wave"></span>
            </div>
            <div>
              <div className="brand-title">METHANE RECON COCKPIT</div>
              <div className="brand-sub">COPERNICUS SENTINEL-5P TROPOMI</div>
            </div>
          </div>

          <div className="hud-status-badge">
            {isSatelliteConnected ? (
              <span className="status-pill live" title="Connected to Copernicus Data Space">
                <Radio size={12} className="pulse-icon" /> S5P STREAM LIVE
              </span>
            ) : (
              <button
                className="status-pill offline"
                onClick={() => navigate("/settings")}
                title="Configure CDSE API credentials in Settings"
              >
                <Satellite size={12} /> CONFIGURE S5P
              </button>
            )}
          </div>
        </div>

        {/* Real-time KPI Counters */}
        <div className="hud-kpis">
          <div className="kpi-item">
            <span className="kpi-label">Monitored Assets</span>
            <span className="kpi-value">{telemetryMetrics.activeAssets}</span>
          </div>
          <div className="kpi-divider"></div>
          <div className="kpi-item">
            <span className="kpi-label">
              {viewMode === "methane" ? "Regional Methane" : "Regional GHG"}
            </span>
            <span className="kpi-value highlight-accent">
              {viewMode === "methane"
                ? `${formatCompact(telemetryMetrics.totalMethane)} t`
                : `${formatCompact(telemetryMetrics.totalGhg)} t`}
            </span>
          </div>
          <div className="kpi-divider"></div>
          <div className="kpi-item">
            <span className="kpi-label">Mean Loss Intensity</span>
            <span className="kpi-value">
              {telemetryMetrics.avgMethaneIntensity}{" "}
              <span className="kpi-unit">kg/boe</span>
            </span>
          </div>
          <div className="kpi-divider"></div>
          <div className="kpi-item">
            <span className="kpi-label">Super-Emitters</span>
            <span
              className={`kpi-value ${telemetryMetrics.superEmitters > 0 ? "kpi-alert" : ""}`}
            >
              {telemetryMetrics.superEmitters}
            </span>
          </div>
        </div>

        {/* View Mode & Basemap Selector */}
        <div className="hud-actions">
          {/* Mode Switcher */}
          <div className="segmented-control mode-selector">
            <button
              className={`seg-btn ${viewMode === "methane" ? "active" : ""}`}
              onClick={() => setViewMode("methane")}
              title="Focus on Methane (CH4) emissions"
            >
              <Flame size={13} />
              <span>CH₄ Flux</span>
            </button>
            <button
              className={`seg-btn ${viewMode === "total" ? "active" : ""}`}
              onClick={() => setViewMode("total")}
              title="Focus on Total GHG (CO2e) emissions"
            >
              <TrendingUp size={13} />
              <span>Total GHG</span>
            </button>
          </div>

          {/* Basemap Switcher */}
          <div className="segmented-control basemap-selector">
            {Object.entries(BASE_MAPS).map(([key, mapInfo]) => {
              const IconComp = mapInfo.icon;
              return (
                <button
                  key={key}
                  className={`seg-btn ${mapBaseLayer === key ? "active" : ""}`}
                  onClick={() => setMapBaseLayer(key)}
                  title={`Switch to ${mapInfo.name}`}
                >
                  <IconComp size={13} />
                  <span>{mapInfo.name.split(" ")[0]}</span>
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* 2. SATELLITE NEW-PASS OVERPASS TOAST */}
      {satelliteAlert && (
        <aside className="satellite-alert-toast" role="alert">
          <div className="toast-header">
            <div className="toast-title">
              {satelliteAlert.anomaly >= 30 ? (
                <span className="badge-danger">
                  <AlertCircle size={14} /> HIGH CH₄ ANOMALY DETECTED
                </span>
              ) : (
                <span className="badge-info">
                  <Satellite size={14} /> NEW S5P OVERPASS
                </span>
              )}
            </div>
            <button
              className="toast-close-btn"
              onClick={() => setSatelliteAlert(null)}
              title="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
          <div className="toast-body">
            <strong>{satelliteAlert.facility}</strong> • {satelliteAlert.date} at{" "}
            {satelliteAlert.time || "11:30 UTC"}
          </div>
          <div className="toast-meta">
            <span className="stat-pill">
              ΔCH₄ +{satelliteAlert.anomaly.toFixed(1)} ppb
            </span>
            <span className="stat-pill stream">
              ● {satelliteAlert.type || "NRTI"}
            </span>
            {satelliteAlert.count > 1 && (
              <span className="stat-pill count">
                +{satelliteAlert.count - 1} more
              </span>
            )}
          </div>
        </aside>
      )}

      {/* 3. LEAFLET INTERACTIVE GEOSPATIAL MAP CANVAS */}
      <div className="explorer-map-container">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          zoomControl={false}
          style={{ height: "100%", width: "100%" }}
        >
          {/* Dynamic Light Basemap Layer */}
          <TileLayer
            key={mapBaseLayer}
            url={(BASE_MAPS[mapBaseLayer] || BASE_MAPS.streets).url}
            attribution={(BASE_MAPS[mapBaseLayer] || BASE_MAPS.streets).attribution}
            subdomains={(BASE_MAPS[mapBaseLayer] || BASE_MAPS.streets).subdomains || "abc"}
          />

          {/* Sentinel-5P Methane Column WMS / Tile Overlay */}
          {showSatelliteLayer && satelliteConfig?.tile_layer_template && (
            <TileLayer
              key={satelliteConfig.tile_layer_template}
              url={satelliteConfig.tile_layer_template}
              opacity={satelliteOpacity}
              zIndex={400}
              attribution='&copy; <a href="https://dataspace.copernicus.eu" target="_blank" rel="noopener noreferrer">Copernicus Sentinel-5P (ESA/EU)</a>'
            />
          )}

          <MapController center={mapCenter} zoom={mapZoom} />
          <ZoomControl position="bottomright" />

          {/* Facility Plume Dispersion Envelopes & Markers */}
          {filteredFacilities.map((fac) => {
            if (!fac.latitude || !fac.longitude) return null;
            const coords = [Number(fac.latitude), Number(fac.longitude)];
            const facilityStats = getIntensityData(fac.id);
            const val =
              viewMode === "total"
                ? facilityStats.total_co2e || 0
                : facilityStats.total_ch4 || 0;

            const isSelected = selectedFacility?.id === fac.id;
            const severity = getSeverityLevel(val);

            // Radius in meters for multi-ring concentric plume envelopes
            const outerRadius =
              severity === "high" ? 22000 : severity === "medium" ? 14000 : 7500;
            const coreRadius = Math.round(outerRadius * 0.45);

            const plumeColor =
              severity === "high"
                ? "#ef4444"
                : severity === "medium"
                  ? "#f59e0b"
                  : "#10b981";

            return (
              <React.Fragment key={fac.id}>
                {/* Simulated Atmospheric Plume Dispersion Rings */}
                {showPlumeRings && (
                  <>
                    {/* Outer atmospheric dispersion boundary */}
                    <Circle
                      center={coords}
                      radius={outerRadius}
                      pathOptions={{
                        color: plumeColor,
                        fillColor: plumeColor,
                        fillOpacity: satelliteOpacity * 0.12,
                        weight: 1,
                        dashArray: "4, 6",
                      }}
                    />
                    {/* High-density plume core */}
                    <Circle
                      center={coords}
                      radius={coreRadius}
                      pathOptions={{
                        color: plumeColor,
                        fillColor: plumeColor,
                        fillOpacity: satelliteOpacity * 0.28,
                        weight: 1.5,
                      }}
                    />
                  </>
                )}

                {/* Pulsing Sonar Beacon Marker */}
                <Marker
                  position={coords}
                  icon={createPulsingIcon(val)}
                  interactive={false}
                />

                {/* Interactive Clickable Marker */}
                <Marker
                  position={coords}
                  icon={createSolidIcon(val, isSelected)}
                  eventHandlers={{
                    click: () => handleSelectFacility(fac),
                  }}
                >
                  <Tooltip
                    direction="top"
                    offset={[0, -10]}
                    opacity={0.98}
                    className="custom-leaflet-tooltip"
                  >
                    <div className="marker-tooltip-card">
                      <div className="tooltip-header">
                        <span className="tooltip-name">{fac.name}</span>
                        <span className={`tooltip-badge ${severity}`}>
                          {severity.toUpperCase()}
                        </span>
                      </div>
                      <div className="tooltip-sub">
                        {fac.region || "Region"} •{" "}
                        {fac.activity || fac.division || "Facility"}
                      </div>
                      <div className="tooltip-emission">
                        <Flame size={12} />
                        <span>
                          {viewMode === "methane"
                            ? `${formatCompact(val)} tCH₄/yr`
                            : `${formatCompact(val)} tCO₂e/yr`}
                        </span>
                      </div>
                    </div>
                  </Tooltip>
                </Marker>
              </React.Fragment>
            );
          })}
        </MapContainer>
      </div>

      {/* 4. COLLAPSIBLE LEFT INTELLIGENCE & RECON DRAWER (WHITE LIGHT THEME) */}
      <div className={`drawer-container left-drawer ${isDrawerOpen ? "open" : "collapsed"}`}>
        <button
          className="drawer-toggle-tab"
          onClick={() => setIsDrawerOpen(!isDrawerOpen)}
          title={isDrawerOpen ? "Collapse drawer" : "Expand drawer"}
          aria-label={isDrawerOpen ? "Collapse drawer" : "Expand drawer"}
        >
          {isDrawerOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>

        {isDrawerOpen && (
          <div className="drawer-inner">
            {/* Drawer Header */}
            <div className="drawer-header">
              <div className="title-row">
                <Sliders size={17} color="#ff6600" />
                <h3>Target Reconnaissance</h3>
              </div>
              <span className="target-count-badge">
                {filteredFacilities.length} ASSETS
              </span>
            </div>

            {/* Quick Search */}
            <div className="filter-group">
              <label className="filter-title">Search Asset / Field</label>
              <div className="search-input-wrapper">
                <Search size={15} className="search-icon" />
                <input
                  type="text"
                  placeholder="Search name, region, division..."
                  value={filters.search}
                  onChange={(e) =>
                    setFilters({ ...filters, search: e.target.value })
                  }
                  className="recon-input"
                  id="recon-search-input"
                />
                {filters.search && (
                  <button
                    className="clear-search-btn"
                    onClick={() => setFilters({ ...filters, search: "" })}
                    title="Clear search"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>

            {/* Filter Row 1: Region & Accounting Year */}
            <div className="filter-row">
              {/* Region Filter */}
              <div className="filter-group flex-1">
                <label className="filter-title">Region / Basin</label>
                <select
                  value={filters.region}
                  onChange={(e) =>
                    setFilters({ ...filters, region: e.target.value })
                  }
                  className="recon-select"
                  id="filter-region-select"
                >
                  <option value="all">All Regions</option>
                  {availableRegions.map((reg) => (
                    <option key={reg} value={reg}>
                      {reg}
                    </option>
                  ))}
                </select>
              </div>

              {/* Year Filter */}
              <div className="filter-group flex-1">
                <label className="filter-title">Accounting Year</label>
                <select
                  value={filters.year}
                  onChange={(e) =>
                    setFilters({ ...filters, year: e.target.value })
                  }
                  className="recon-select"
                  id="filter-year-select"
                >
                  <option value="all">All Years</option>
                  {availableYears.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Filter Row 2: Activity */}
            <div className="filter-group">
              <label className="filter-title">Activity Type</label>
              <select
                value={filters.activity}
                onChange={(e) =>
                  setFilters({ ...filters, activity: e.target.value })
                }
                className="recon-select"
                id="filter-activity-select"
              >
                <option value="all">All Activities</option>
                {availableActivities.map((act) => (
                  <option key={act} value={act}>
                    {act}
                  </option>
                ))}
              </select>
            </div>

            {/* Severity Filter Pills */}
            <div className="filter-group">
              <label className="filter-title">Anomaly Severity</label>
              <div className="severity-pills">
                {[
                  { id: "all", label: "All" },
                  { id: "high", label: "Super-Emitters", color: "#ef4444" },
                  { id: "medium", label: "Moderate", color: "#f59e0b" },
                  { id: "baseline", label: "Baseline", color: "#10b981" },
                ].map((pill) => (
                  <button
                    key={pill.id}
                    className={`pill-btn ${filters.severity === pill.id ? "active" : ""}`}
                    onClick={() =>
                      setFilters({ ...filters, severity: pill.id })
                    }
                  >
                    {pill.color && (
                      <span
                        className="pill-dot"
                        style={{ backgroundColor: pill.color }}
                      ></span>
                    )}
                    <span>{pill.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Sentinel-5P Satellite Overlay Controls Card */}
            <div className="sat-overlay-card">
              <div className="sat-card-top">
                <div className="sat-card-title">
                  <Satellite size={15} color="#0284c7" />
                  <span>Sentinel-5P Overlay</span>
                </div>
                <label className="switch-toggle">
                  <input
                    type="checkbox"
                    checked={showSatelliteLayer}
                    onChange={(e) => setShowSatelliteLayer(e.target.checked)}
                    id="toggle-sat-layer-checkbox"
                  />
                  <span className="slider round"></span>
                </label>
              </div>

              {showSatelliteLayer && (
                <div className="sat-card-controls">
                  <div className="slider-row">
                    <span className="control-label">
                      Opacity: {Math.round(satelliteOpacity * 100)}%
                    </span>
                    <input
                      type="range"
                      min="0.15"
                      max="1.0"
                      step="0.05"
                      value={satelliteOpacity}
                      onChange={(e) =>
                        setSatelliteOpacity(Number(e.target.value))
                      }
                      className="recon-range-slider"
                      id="satellite-opacity-slider"
                    />
                  </div>

                  <div className="toggles-subrow">
                    <label className="recon-checkbox-label">
                      <input
                        type="checkbox"
                        checked={showPlumeRings}
                        onChange={(e) => setShowPlumeRings(e.target.checked)}
                      />
                      <span>Plume Footprints</span>
                    </label>

                    <label className="recon-checkbox-label">
                      <input
                        type="checkbox"
                        checked={showLegend}
                        onChange={(e) => setShowLegend(e.target.checked)}
                      />
                      <span>Legend</span>
                    </label>
                  </div>
                </div>
              )}
            </div>

            {/* Target Asset List Header */}
            <div className="target-list-heading">
              <span>Facility Inventory</span>
              <span className="subtext">Click to inspect</span>
            </div>

            {/* Neat Target Facility Cards */}
            <div className="target-cards-scroll">
              {filteredFacilities.length === 0 ? (
                <div className="empty-target-state">
                  <AlertCircle size={22} color="#94a3b8" />
                  <span>No assets match current reconnaissance filters.</span>
                  <button
                    className="btn-reset-filters"
                    onClick={handleResetFilters}
                  >
                    <RotateCcw size={12} />
                    <span>Reset All Filters</span>
                  </button>
                </div>
              ) : (
                filteredFacilities.map((fac) => {
                  const facilityStats = getIntensityData(fac.id);
                  const isSelected = selectedFacility?.id === fac.id;
                  const val =
                    viewMode === "methane"
                      ? facilityStats.total_ch4 || 0
                      : facilityStats.total_co2e || 0;
                  const severity = getSeverityLevel(val);

                  return (
                    <div
                      key={fac.id}
                      className={`target-card ${isSelected ? "selected" : ""}`}
                      onClick={() => handleSelectFacility(fac)}
                    >
                      <div className="target-card-left">
                        <span className={`beacon-dot ${severity}`}></span>
                        <div className="target-card-info">
                          <div className="target-card-title">{fac.name}</div>
                          <div className="target-card-meta">
                            {fac.region && (
                              <span className="region-tag">{fac.region}</span>
                            )}
                            <span className="activity-text">
                              {fac.activity || fac.division || "Industrial Asset"}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="target-card-right">
                        <span className="target-card-val">
                          {formatCompact(val)}
                        </span>
                        <span className="target-card-unit">
                          {viewMode === "methane" ? "tCH₄" : "tCO₂e"}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* 5. CALIBRATED SPECTRAL ABSORPTION RAMP LEGEND (WHITE LIGHT THEME) */}
      {showSatelliteLayer && showLegend && (
        <aside className="spectral-legend-card" role="region" aria-label="Spectral Legend">
          <div className="legend-header">
            <div className="legend-title">
              <Satellite size={14} color="#0284c7" />
              <span>TROPOMI CH₄ Column Mole Fraction</span>
            </div>
            <button
              className="legend-close"
              onClick={() => setShowLegend(false)}
              title="Hide Legend"
            >
              <X size={12} />
            </button>
          </div>
          <div className="spectral-gradient-track"></div>
          <div className="spectral-scale-ticks">
            <span>&lt;1,750</span>
            <span>1,800</span>
            <span>1,850</span>
            <span>1,900</span>
            <span>&ge;1,950 ppb</span>
          </div>
          <div className="legend-footer-info">
            <span>SWIR Band 7/8 (2.3 µm) • L3 5.5×7 km</span>
            <a
              href="https://dataspace.copernicus.eu"
              target="_blank"
              rel="noopener noreferrer"
              className="cdse-portal-link"
            >
              CDSE Hub <ExternalLink size={10} />
            </a>
          </div>
        </aside>
      )}

      {/* 6. SLIDE-IN RIGHT FACILITY RECONNAISSANCE DOSSIER (WHITE LIGHT THEME) */}
      {selectedFacility && (
        <section className="facility-dossier-panel" aria-label="Facility Reconnaissance Dossier">
          {/* Dossier Header */}
          <div className="dossier-header">
            <button
              className="dossier-close-btn"
              onClick={() => setSelectedFacility(null)}
              title="Close Dossier"
            >
              <X size={16} />
            </button>

            <div className="dossier-tag">
              <span className="target-pulse"></span>
              <span>FACILITY RECONNAISSANCE DOSSIER</span>
            </div>
            <h3 className="dossier-facility-name">{selectedFacility.name}</h3>

            <div className="dossier-geo-row">
              <div className="geo-location">
                <MapPin size={13} color="#ff6600" />
                <span>
                  {selectedFacility.region ? `${selectedFacility.region} Region` : "Algeria"} •{" "}
                  {selectedFacility.activity || selectedFacility.division || "Facility"}
                </span>
              </div>
              <button
                className="coords-badge"
                onClick={handleCopyCoords}
                title="Copy coordinates to clipboard"
              >
                {copiedCoords ? (
                  <>
                    <Check size={11} color="#10b981" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={11} />
                    <span>
                      {Number(selectedFacility.latitude || 0).toFixed(4)}°N,{" "}
                      {Number(selectedFacility.longitude || 0).toFixed(4)}°E
                    </span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* SATELLITE TOP-DOWN INTELLIGENCE SECTION */}
          <div className="dossier-sat-card">
            <div className="sat-card-top-bar">
              <div className="sat-label-left">
                <Satellite size={16} color="#0284c7" />
                <strong>Copernicus Sentinel-5P Overpass</strong>
              </div>
              {loadingSatelliteData ? (
                <div className="sat-loading-indicator">
                  <RefreshCw size={12} className="spin-fast" color="#0284c7" />
                  <span>STAC Query...</span>
                </div>
              ) : (
                satelliteObservation?.summary?.stream_type && (
                  <span className="stream-badge">
                    ● {satelliteObservation.summary.stream_type}
                  </span>
                )
              )}
            </div>

            {loadingSatelliteData ? (
              <div className="sat-skeleton-loader">
                <div className="skeleton-line"></div>
                <div className="skeleton-line short"></div>
              </div>
            ) : satelliteObservation &&
              satelliteObservation.authenticated &&
              satelliteObservation.summary ? (
              <div className="sat-telemetry-body">
                {/* 4-Stat Telemetry Matrix */}
                <div className="telemetry-grid">
                  <div className="telemetry-box">
                    <span className="box-label">Mean CH₄ Column</span>
                    <span className="box-val">
                      {Number(
                        satelliteObservation.summary.mean_ch4_column_ppb || 0
                      ).toFixed(1)}{" "}
                      <span className="val-unit">ppb</span>
                    </span>
                  </div>

                  <div className="telemetry-box">
                    <span className="box-label">Max Anomaly (&Delta;CH₄)</span>
                    <span
                      className={`box-val ${
                        Number(satelliteObservation.summary.max_anomaly_ppb || 0) >= 25
                          ? "alert-red"
                          : "alert-amber"
                      }`}
                    >
                      +
                      {Number(
                        satelliteObservation.summary.max_anomaly_ppb || 0
                      ).toFixed(1)}{" "}
                      <span className="val-unit">ppb</span>
                    </span>
                  </div>

                  <div className="telemetry-box">
                    <span className="box-label">Inferred Emission Rate</span>
                    <span className="box-val highlight-amber">
                      {Number(
                        satelliteObservation.summary.estimated_emission_rate_kg_hr || 0
                      ) > 0
                        ? `${Number(
                            satelliteObservation.summary
                              .estimated_emission_rate_kg_hr
                          ).toFixed(1)} kg/hr`
                        : "Background"}
                    </span>
                  </div>

                  <div className="telemetry-box">
                    <span className="box-label">Annualized Satellite Flux</span>
                    <span className="box-val">
                      {Number(
                        satelliteObservation.summary.annualized_ch4_tonnes || 0
                      ) > 0
                        ? `${Number(
                            satelliteObservation.summary.annualized_ch4_tonnes
                          ).toFixed(1)} t/yr`
                        : "0.0 t/yr"}
                    </span>
                  </div>
                </div>

                {/* Overpass Metadata Strip */}
                <div className="sat-pass-meta">
                  <div className="meta-item">
                    <span className="meta-title">Overpass:</span>
                    <span className="meta-data">
                      {satelliteObservation.summary.latest_observation_date}{" "}
                      {satelliteObservation.summary.latest_observation_time
                        ? `(${satelliteObservation.summary.latest_observation_time})`
                        : ""}
                    </span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-title">QA Confidence:</span>
                    <span className="meta-data">
                      {(
                        Number(satelliteObservation.summary.mean_qa_score || 0) *
                        100
                      ).toFixed(0)}
                      %
                    </span>
                  </div>
                </div>

                {/* TOP-DOWN vs BOTTOM-UP RECONCILIATION BENCHMARK */}
                {reconciliationAnalysis && (
                  <div
                    className="reconciliation-meter-box"
                    style={{ borderColor: `${reconciliationAnalysis.color}50` }}
                  >
                    <div className="meter-header">
                      <div className="meter-title">
                        <Activity size={13} color={reconciliationAnalysis.color} />
                        <span>OGMP 2.0 Reconciliation Gap</span>
                      </div>
                      <span
                        className="recon-status-badge"
                        style={{
                          backgroundColor: `${reconciliationAnalysis.color}15`,
                          color: reconciliationAnalysis.color,
                          borderColor: `${reconciliationAnalysis.color}40`,
                        }}
                      >
                        {reconciliationAnalysis.label}
                      </span>
                    </div>
                    <div className="meter-explanation">
                      {reconciliationAnalysis.deltaText}
                    </div>
                  </div>
                )}

                {/* Level 5 OGMP Reconciliation Button */}
                <button
                  className="btn-reconcile-ogmp"
                  onClick={handleExportToOgmp}
                  disabled={exportingOgmp}
                  id="reconcile-ogmp-btn"
                >
                  {exportingOgmp ? (
                    <>
                      <span className="recon-spinner"></span>
                      <span>Recording Level 5 Verification...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck size={16} />
                      <span>Reconcile into OGMP 2.0 Ledger</span>
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="sat-unconfigured-card">
                <AlertCircle size={18} color="#d97706" />
                <div className="unconfigured-text">
                  <div className="unconf-title">Copernicus Live Feed Unconfigured</div>
                  <div className="unconf-desc">
                    Connect your free Copernicus Data Space Ecosystem (CDSE)
                    credentials in Settings to stream verified Sentinel-5P overpasses.
                  </div>
                  <button
                    className="btn-link-settings"
                    onClick={() => navigate("/settings")}
                  >
                    Configure in Settings &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* REAL DATABASE VERIFIED OGMP SURVEYS SECTION (IF RECORDED) */}
          {existingSurveys.length > 0 && (
            <div className="dossier-surveys-card">
              <div className="card-section-title">
                <ShieldCheck size={15} color="#10b981" />
                <span>Verified OGMP Surveys in Database ({existingSurveys.length})</span>
              </div>
              <div className="surveys-list">
                {existingSurveys.slice(0, 3).map((survey) => (
                  <div key={survey.id} className="survey-item">
                    <div className="survey-item-top">
                      <span className="survey-type">{survey.survey_type || survey.surveyType}</span>
                      <span className="survey-date">{survey.survey_date || survey.surveyDate}</span>
                    </div>
                    <div className="survey-item-metrics">
                      <span>Rate: <strong>{Number(survey.measured_rate_kg_hr || survey.measuredRateKgHr || 0).toFixed(1)} kg/hr</strong></span>
                      <span>Annual: <strong>{Number(survey.estimated_annual_tch4 || survey.estimatedAnnualTch4 || 0).toFixed(1)} tCH₄</strong></span>
                      <span className="survey-status-badge">{survey.reconciliation_status || "Recorded"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* BOTTOM-UP REPORTED ENGINEERING INVENTORY METRICS (REAL DATABASE VALUES) */}
          <div className="dossier-bottomup-card">
            <div className="card-section-title">
              <BarChart3 size={15} color="#ff6600" />
              <span>Bottom-Up Reported Inventory</span>
            </div>

            <div className="bottomup-metrics-grid">
              {/* Main Emission Highlight */}
              <div className="stat-card span-2 main-accent">
                <span className="stat-card-title">
                  {viewMode === "methane"
                    ? "Reported Methane (CH₄)"
                    : "Reported Total GHG"}
                </span>
                <span className="stat-card-number">
                  {viewMode === "methane"
                    ? `${formatCompact(selectedStats.total_ch4)} tCH₄`
                    : `${formatCompact(selectedStats.total_co2e)} tCO₂e`}
                </span>
                <span className="stat-card-sub">
                  Verified Bottom-Up Engineering Ledger
                </span>
              </div>

              {/* Hydrocarbon Production */}
              <div className="stat-card">
                <span className="stat-card-title">Production</span>
                <span className="stat-card-number emerald">
                  {formatCompact(selectedStats.total_boe)}
                </span>
                <span className="stat-card-sub">BOE / Year</span>
              </div>

              {/* Carbon / Methane Intensity */}
              <div className="stat-card">
                <span className="stat-card-title">
                  {viewMode === "methane"
                    ? "Methane Intensity"
                    : "Carbon Intensity"}
                </span>
                <span className="stat-card-number amber">
                  {viewMode === "methane"
                    ? Number(selectedStats.ch4_intensity || 0).toFixed(3)
                    : Number(selectedStats.co2_intensity || 0).toFixed(2)}
                </span>
                <span className="stat-card-sub">
                  {viewMode === "methane" ? "kgCH₄/boe" : "kgCO₂e/boe"}
                </span>
              </div>

              {/* Flaring Intensity */}
              <div className="stat-card">
                <span className="stat-card-title">Flaring Intensity</span>
                <span className="stat-card-number danger">
                  {Number(selectedStats.api_flaring_intensity || 0).toFixed(2)}
                </span>
                <span className="stat-card-sub">kgCO₂e/boe</span>
              </div>

              {/* Asset Division Identifier */}
              <div className="stat-card">
                <span className="stat-card-title">Asset Code</span>
                <span className="stat-card-number mono">
                  {selectedFacility.code || "N/A"}
                </span>
                <span className="stat-card-sub">Database Ref</span>
              </div>
            </div>
          </div>

          {/* QUICK FOCUS ACTION BUTTONS */}
          <div className="dossier-actions">
            <button
              className="btn-action-focus"
              onClick={() => {
                const lat = Number(selectedFacility.latitude);
                const lon = Number(selectedFacility.longitude);
                if (!isNaN(lat) && !isNaN(lon)) {
                  setMapZoom(11);
                  setMapCenter([lat, lon]);
                }
              }}
            >
              <Target size={16} />
              <span>Center Aerial Camera (Zoom 11x)</span>
            </button>
          </div>
        </section>
      )}
    </div>
  );
};

export default EmissionsMap;
