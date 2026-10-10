import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
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
  Flame,
  Map as MapIcon,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { getUserOperationalDefaults, isUnrestrictedLocation } from "../utils/userDefaults";
import { cn } from "../ui";
import ExplorerHud from "./explorer/ExplorerHud";
import ExplorerDrawer from "./explorer/ExplorerDrawer";
import ExplorerDossier from "./explorer/ExplorerDossier";
import "./MethaneExplorer.css";
import { t } from "../i18n";

interface MapControllerProps {
  center: [number, number];
  zoom: number;
}

// Fix Leaflet tile sizing when mounted inside animated route transitions
const MapController: React.FC<MapControllerProps> = ({ center, zoom }) => {
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
// Basemap tiles come from the server (MAP_TILE_URL): none on an offline install, never a public tile
// server by default (pilot check 2026-10-09, F5: the map used Google's tile server without an API key).
interface MapTiles {
  tile_url: string | null;
  attribution: string | null;
  subdomains: string | null;
}

interface FacilityRecord {
  id: number | string;
  name: string;
  latitude?: number | string;
  longitude?: number | string;
  region?: string;
  region_identifier?: string;
  location?: string;
  activity?: string;
  division?: string;
  [key: string]: any;
}

interface FacilityIntensityStats {
  facility_id: number | string;
  co2_intensity?: number;
  ch4_intensity?: number;
  api_flaring_intensity?: number;
  total_boe?: number;
  total_co2e?: number;
  total_ch4?: number;
  [key: string]: any;
}

interface FilterState {
  search: string;
  region: string;
  year: string | number;
  activity: string;
  severity: "all" | "high" | "medium" | "baseline" | string;
}

const EmissionsMap: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast?.() || {
    success: console.log,
    error: console.error,
    info: console.log,
  };

  // Core Data States (All fetched from authentic backend endpoints)
  const [facilities, setFacilities] = useState<FacilityRecord[]>([]);
  const [stats, setStats] = useState<FacilityIntensityStats[]>([]);
  const [filteredFacilities, setFilteredFacilities] = useState<FacilityRecord[]>([]);
  const [selectedFacility, setSelectedFacility] = useState<FacilityRecord | null>(null);
  const [mapCenter, setMapCenter] = useState<[number, number]>([31.68, 6.07]); // Default centered on Algerian basin
  const [mapZoom, setMapZoom] = useState<number>(6);
  const [availableYears, setAvailableYears] = useState<(number | string)[]>([]);
  const [availableRegions, setAvailableRegions] = useState<string[]>([]);
  const [availableActivities, setAvailableActivities] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const isFirstLoadRef = useRef<boolean>(true);

  // Filters (Search, Region, Year, Activity, Severity)
  const [filters, setFilters] = useState<FilterState>({
    search: "",
    region: "all",
    year: "all",
    activity: "all",
    severity: "all", // 'all' | 'high' | 'medium' | 'baseline'
  });
  const [viewMode, setViewMode] = useState<string>("methane"); // 'methane' (CH4 default) or 'total' (CO2e)
  const [mapTiles, setMapTiles] = useState<MapTiles | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);
  const [showPlumeRings, setShowPlumeRings] = useState<boolean>(true);
  const [copiedCoords, setCopiedCoords] = useState<boolean>(false);

  // OGMP 2.0 site-level surveys recorded for the selected facility
  const [existingSurveys, setExistingSurveys] = useState<any[]>([]);
  const [loadingSurveys, setLoadingSurveys] = useState<boolean>(false);
  const selectedFacilityRef = useRef<FacilityRecord | null>(null);

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
        params.append("year", String(filters.year));
      }

      // Fetch authentic facilities from /api/facilities, verified intensity stats from /api/dashboard/intensity-stats,
      // and available years from /api/dashboard/years
      const [facRes, statRes, yearRes] = await Promise.all([
        api.get("/facilities"),
        api.get(`/dashboard/intensity-stats?${params.toString()}`),
        api.get("/dashboard/years"),
      ]);

      const fetchedFacilities: FacilityRecord[] = facRes.data || [];
      setFacilities(fetchedFacilities);
      setStats(statRes.data || []);
      setAvailableYears(yearRes.data || []);

      // Derive distinct regions and activities directly from the database facilities
      const regions = [
        ...new Set(fetchedFacilities.flatMap((f) => [f.region_identifier, f.location]).filter(Boolean) as string[]),
      ].sort();
      const userLoc = (user?.location || "").trim();
      if (userLoc && !isUnrestrictedLocation(userLoc) && !regions.includes(userLoc)) {
        regions.unshift(userLoc);
      }
      setAvailableRegions(regions);

      const acts = [
        ...new Set(fetchedFacilities.map((f) => f.activity).filter(Boolean) as string[]),
      ].sort();
      setAvailableActivities(acts);

      const opDefaults = getUserOperationalDefaults(user, fetchedFacilities);
      if (opDefaults.isRestricted || fetchedFacilities.length === 1) {
        setFilters((prev) => ({
          ...prev,
          region: prev.region === "all" && opDefaults.defaultRegion ? opDefaults.defaultRegion : prev.region,
          activity: prev.activity === "all" && opDefaults.defaultActivity ? opDefaults.defaultActivity : prev.activity,
        }));
      }
    } catch (error) {
      console.error("Failed to load explorer data:", error);
      toast.error(t("Failed to initialize facility data from server"));
    } finally {
      setLoading(false);
      setIsUpdating(false);
      isFirstLoadRef.current = false;
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters.year]);

  useEffect(() => {
    api
      .get("/map-config")
      .then((res) => setMapTiles(res.data))
      .catch(() => setMapTiles({ tile_url: null, attribution: null, subdomains: null }));
  }, []);

  // Helper to retrieve verified intensity stats for any facility
  const getIntensityData = useCallback(
    (facilityId: number | string) => {
      return (
        stats.find((s) => Number(s.facility_id) === Number(facilityId)) || {
          facility_id: facilityId,
          co2_intensity: 0,
          ch4_intensity: 0,
          api_flaring_intensity: 0,
          total_boe: 0,
          total_co2e: 0,
          total_ch4: 0,
        }
      );
    },
    [stats],
  );

  // Multi-criteria facility filtering (Search, Region, Activity, Coordinates, Severity)
  useEffect(() => {
    const searchLower = (filters.search || "").toLowerCase().trim();
    const highThreshold = viewMode === "total" ? 50000 : 500;
    const medThreshold = viewMode === "total" ? 10000 : 100;

    const filtered = facilities.filter((f) => {
      // Region Filter — use region_identifier (= f.region ?? f.name) so facilities
      // uploaded via bulk uploader (where region=NULL) still match correctly. The options also list
      // locations (and a regional user's scope can be a location), so a location matches too.
      const matchesRegion =
        filters.region === "all" ||
        f.region_identifier === filters.region ||
        f.location === filters.region;

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

  // Keep a ref to the selected facility so a late survey response does not overwrite a newer selection
  useEffect(() => {
    selectedFacilityRef.current = selectedFacility;
  }, [selectedFacility]);

  // Fetch the OGMP surveys recorded for the selected facility
  const fetchFacilityData = useCallback((facility: FacilityRecord | null) => {
    if (!facility) return;
    const targetFacilityId = facility.id;

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
  }, []);

  // Query authentic facility records whenever selection changes
  useEffect(() => {
    if (!selectedFacility) {
      setExistingSurveys([]);
      return;
    }
    fetchFacilityData(selectedFacility);
  }, [selectedFacility, fetchFacilityData]);

  // Facility selection handler
  const handleSelectFacility = (fac: FacilityRecord) => {
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
    } catch {
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
      } catch {
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
  const formatCompact = (num: any): string => {
    if (num == null || isNaN(num)) return "0";
    const n = Number(num);
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return Math.round(n).toLocaleString();
  };

  const getSeverityLevel = (val: number): string => {
    const threshold = viewMode === "total" ? 10000 : 100;
    if (val > threshold * 5) return "high"; // Super-emitter
    if (val > threshold) return "medium";
    return "low";
  };

  // Marker pulse classes and custom div icons
  const createPulsingIcon = (val: number) => {
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

  // The marker is a keyboard button (Leaflet sets role="button"); this hidden text is its accessible name.
  const escapeHtml = (text: string) =>
    text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);

  const createSolidIcon = (val: number, isSelected: boolean, label: string) => {
    const level = getSeverityLevel(val);
    const color =
      level === "high"
        ? "var(--color-red-500)"
        : level === "medium"
          ? "var(--color-amber-500)"
          : "var(--color-green-500)";
    const baseRadius = level === "high" ? 8 : level === "medium" ? 6 : 5;
    const radius = isSelected ? baseRadius + 3 : baseRadius;
    const border = isSelected ? "2.5px solid var(--color-brand-500)" : "2px solid var(--color-white)";
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
      "></div><span class="sr-only">${escapeHtml(label)}</span>`,
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

  const selectedStats = selectedFacility
    ? getIntensityData(selectedFacility.id)
    : null;

  if (loading) {
    return (
      <div className="[display:flex] [flex-direction:column] [align-items:center] [justify-content:center] [height:calc(100vh_-_72px)] [gap:16px] [background:var(--color-ink-50)] [color:var(--color-ink-900)]">
        <div className="[position:relative] [width:80px] [height:80px] [border:2px_solid_rgba(255,_102,_0,_0.2)] [&&]:[border-radius:50%] [display:flex] [align-items:center] [justify-content:center] [box-shadow:0_4px_20px_rgba(255,_102,_0,_0.15)]">
          <div className="[position:absolute] [inset:0] [border-radius:50%] [border-top:3px_solid_var(--color-brand-500)] [animation:spin_1.2s_cubic-bezier(0.5,_0,_0.5,_1)_infinite]"></div>
          <MapIcon size={34} color="var(--color-brand-500)" />
        </div>
        <div className="[font-size:var(--text-md)] [font-weight:800] [letter-spacing:0.08em] [color:var(--color-ink-900)]">{t("LOADING METHANE EXPLORER")}</div>
        <div className="[font-size:var(--text-sm)] [color:var(--color-ink-500)] [max-width:420px] [text-align:center] [line-height:1.5]">
          {t("Fetching operational facilities and emission inventories...")}
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
      <ExplorerHud
        metrics={telemetryMetrics}
        viewMode={viewMode}
        onViewMode={setViewMode}
        formatCompact={formatCompact}
      />

      {/* 3. LEAFLET INTERACTIVE GEOSPATIAL MAP CANVAS */}
      <div className="[position:absolute] [inset:0] [width:100%] [height:100%] [z-index:1]">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          zoomControl={false}
          // without a basemap the map shows a light neutral ground, not Leaflet's grey (contrast of the panels on top)
          className={cn("h-full! w-full!", mapTiles && !mapTiles.tile_url && "bg-ink-50!")}
        >
          {mapTiles?.tile_url && (
            <TileLayer
              url={mapTiles.tile_url}
              attribution={mapTiles.attribution || ""}
              subdomains={mapTiles.subdomains || "abc"}
            />
          )}

          <MapController center={mapCenter} zoom={mapZoom} />
          <ZoomControl position="bottomright" />

          {/* Facility severity rings & markers (a visual scale by emission severity, not a dispersion model) */}
          {filteredFacilities.map((fac) => {
            if (!fac.latitude || !fac.longitude) return null;
            const coords: [number, number] = [Number(fac.latitude), Number(fac.longitude)];
            const facilityStats = getIntensityData(fac.id);
            const val =
              viewMode === "total"
                ? facilityStats.total_co2e || 0
                : facilityStats.total_ch4 || 0;

            const isSelected = selectedFacility?.id === fac.id;
            const severity = getSeverityLevel(val);

            // Fixed ring radius per severity class: a map symbol only, no atmospheric dispersion is modelled
            const outerRadius =
              severity === "high" ? 22000 : severity === "medium" ? 14000 : 7500;
            const coreRadius = Math.round(outerRadius * 0.45);

            const plumeColor =
              severity === "high"
                ? "var(--color-red-500)"
                : severity === "medium"
                  ? "var(--color-amber-500)"
                  : "var(--color-green-500)";

            return (
              <React.Fragment key={fac.id}>
                {/* Severity rings (symbol size by severity class) */}
                {showPlumeRings && (
                  <>
                    {/* Outer ring */}
                    <Circle
                      center={coords}
                      radius={outerRadius}
                      pathOptions={{
                        color: plumeColor,
                        fillColor: plumeColor,
                        fillOpacity: 0.09,
                        weight: 1,
                        dashArray: "4, 6",
                      }}
                    />
                    {/* Inner ring */}
                    <Circle
                      center={coords}
                      radius={coreRadius}
                      pathOptions={{
                        color: plumeColor,
                        fillColor: plumeColor,
                        fillOpacity: 0.21,
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
                  keyboard={false}
                />

                {/* Interactive Clickable Marker */}
                <Marker
                  position={coords}
                  icon={createSolidIcon(val, isSelected, `${fac.name} (${severity} severity)`)}
                  eventHandlers={{
                    click: () => handleSelectFacility(fac),
                    // Leaflet makes the marker a focusable button but does not turn Enter or Space into a click.
                    keydown: (e: L.LeafletKeyboardEvent) => {
                      const key = e.originalEvent.key;
                      if (key === "Enter" || key === " ") {
                        e.originalEvent.preventDefault();
                        handleSelectFacility(fac);
                      }
                    },
                  }}
                >
                  <Tooltip
                    direction="top"
                    offset={[0, -10]}
                    opacity={0.98}
                    className="[background:rgba(255,_255,_255,_0.98)]! [backdrop-filter:blur(14px)]! [border:1px_solid_rgba(255,_102,_0,_0.4)]! [&&]:[border-radius:var(--radius-md)]! [box-shadow:var(--shadow-card)]! [padding:8px_12px]! [color:var(--color-ink-900)]! before:[border-top-color:rgba(255,_255,_255,_0.98)]!"
                  >
                    <div className="[display:flex] [flex-direction:column] [gap:3px]">
                      <div className="[display:flex] [align-items:center] [gap:8px]">
                        <span className="[font-size:var(--text-sm)] [font-weight:800] [color:var(--color-ink-900)]">{fac.name}</span>
                        <span className={`tooltip-badge ${severity}`}>
                          {severity.toUpperCase()}
                        </span>
                      </div>
                      <div className="[font-size:var(--text-xs)] [color:var(--color-ink-500)]">
                        {fac.region || t("Region")} •{" "}
                        {fac.activity || fac.division || t("Facility")}
                      </div>
                      <div className="[display:flex] [align-items:center] [gap:5px] [font-size:var(--text-sm)] [font-weight:700] [color:var(--color-link)] [margin-top:2px]">
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
        {mapTiles && !mapTiles.tile_url && (
          <p className="absolute bottom-7 left-1/2 z-500 m-0 -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-surface/90 px-2.5 py-1 text-xs text-text-secondary">
            {t("No basemap: facilities are shown at their coordinates")}
          </p>
        )}
      </div>

      {/* 4. COLLAPSIBLE LEFT INTELLIGENCE & RECON DRAWER (WHITE LIGHT THEME) */}
      <div
        className={cn(
          "pointer-events-none absolute bottom-5 left-4 top-[78px] z-950 w-[340px] transition-transform duration-300 ease-out",
          !isDrawerOpen && "-translate-x-[346px]",
        )}
      >
        <button
          type="button"
          className="pointer-events-auto absolute -right-9 top-3.5 flex h-11 w-9 cursor-pointer items-center justify-center rounded-r-md border border-l-0 border-border bg-surface text-brand-700 shadow-md hover:bg-ink-50"
          onClick={() => setIsDrawerOpen(!isDrawerOpen)}
          title={isDrawerOpen ? t("Collapse drawer") : t("Expand drawer")}
          aria-label={isDrawerOpen ? t("Collapse drawer") : t("Expand drawer")}
        >
          {isDrawerOpen ? <ChevronLeft className="size-4" aria-hidden="true" /> : <ChevronRight className="size-4" aria-hidden="true" />}
        </button>

        {isDrawerOpen && (
          <ExplorerDrawer
            filters={filters}
            onFilters={setFilters}
            regions={availableRegions}
            years={availableYears}
            activities={availableActivities}
            count={filteredFacilities.length}
            rings={showPlumeRings}
            onRings={setShowPlumeRings}
            facilities={filteredFacilities}
            selectedId={selectedFacility?.id ?? null}
            viewMode={viewMode}
            getStats={getIntensityData}
            getSeverity={getSeverityLevel}
            formatCompact={formatCompact}
            onSelect={handleSelectFacility}
            onReset={handleResetFilters}
          />
        )}
      </div>

      {selectedFacility && (
        <ExplorerDossier
          facility={selectedFacility}
          stats={selectedStats || {}}
          viewMode={viewMode}
          formatCompact={formatCompact}
          copiedCoords={copiedCoords}
          onCopyCoords={handleCopyCoords}
          onClose={() => setSelectedFacility(null)}
          loadingSurveys={loadingSurveys}
          surveys={existingSurveys}
          onCenter={() => {
            const lat = Number(selectedFacility.latitude);
            const lon = Number(selectedFacility.longitude);
            if (!isNaN(lat) && !isNaN(lon)) {
              setMapZoom(11);
              setMapCenter([lat, lon]);
            }
          }}
        />
      )}
    </div>
  );
};

export default EmissionsMap;
