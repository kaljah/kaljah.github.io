import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Circle, Tooltip, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
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
    Zap
} from 'lucide-react';
import api from '../api';
import { useToast } from '../components/Toast';
import './MethaneExplorer.css';

const MapController = ({ center, zoom }) => {
    const map = useMap();
    useEffect(() => {
        if (center) {
            map.flyTo(center, zoom, { duration: 1.5 });
        }
    }, [center, zoom, map]);
    return null;
};

const EmissionsMap = () => {
    const navigate = useNavigate();
    const toast = useToast?.() || { success: console.log, error: console.error, info: console.log };

    const [facilities, setFacilities] = useState([]);
    const [stats, setStats] = useState([]);
    const [filteredFacilities, setFilteredFacilities] = useState([]);
    const [selectedFacility, setSelectedFacility] = useState(null);
    const [mapCenter, setMapCenter] = useState([28.0, 2.5]);
    const [mapZoom, setMapZoom] = useState(5);
    const [filters, setFilters] = useState({ activity: 'all', search: '', year: 'all' });
    const [viewMode, setViewMode] = useState('total'); // 'total' (GHG) or 'methane'
    const [availableYears, setAvailableYears] = useState([]);
    const [loading, setLoading] = useState(true);
    const [availableActivities, setAvailableActivities] = useState([]);

    // Copernicus Sentinel-5P Satellite States
    const [satelliteConfig, setSatelliteConfig] = useState(null);
    const [showSatelliteLayer, setShowSatelliteLayer] = useState(true);
    const [satelliteOpacity, setSatelliteOpacity] = useState(0.75);
    const [satelliteObservation, setSatelliteObservation] = useState(null);
    const [loadingSatelliteData, setLoadingSatelliteData] = useState(false);
    const [exportingOgmp, setExportingOgmp] = useState(false);
    const [showLegend, setShowLegend] = useState(true);
    const [satelliteAlert, setSatelliteAlert] = useState(null); // in-page new-pass toast
    const [lastPollTime, setLastPollTime] = useState(null);
    const satellitePollRef = useRef(null);
    const selectedFacilityRef = useRef(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams({
                year: filters.year
            });

            const [facRes, statRes, yearRes, satConfigRes] = await Promise.all([
                api.get('/facilities'),
                api.get(`/dashboard/intensity-stats?${params}`),
                api.get('/dashboard/years'),
                api.get('/satellite/sentinel5p/layer-config').catch(() => ({ data: null }))
            ]);

            setFacilities(facRes.data || []);
            setStats(statRes.data || []);
            setAvailableYears(yearRes.data || []);
            if (satConfigRes && satConfigRes.data) {
                setSatelliteConfig(satConfigRes.data);
            }

            // Derive unique activities from what's actually in the DB
            const acts = [...new Set(
                (facRes.data || [])
                    .map(f => f.activity)
                    .filter(Boolean)
            )].sort();
            setAvailableActivities(acts);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load explorer data:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [filters.year]);

    useEffect(() => {
        const filtered = facilities.filter(f => {
            const matchesActivity = filters.activity === 'all' || f.activity === filters.activity;
            const matchesSearch = f.name.toLowerCase().includes(filters.search.toLowerCase());
            return matchesActivity && matchesSearch && f.latitude && f.longitude;
        });
        setFilteredFacilities(filtered);
    }, [filters, facilities]);

    // Keep a ref to selected facility so the polling callback can access it without stale closure
    useEffect(() => {
        selectedFacilityRef.current = selectedFacility;
    }, [selectedFacility]);

    // Fetch satellite observation for a facility (reusable)
    const fetchSatelliteObservation = useCallback(async (facility) => {
        if (!facility || !facility.latitude || !facility.longitude) return;
        try {
            setLoadingSatelliteData(true);
            const res = await api.get('/satellite/sentinel5p/facility-timeseries', {
                params: {
                    facility_id: facility.id,
                    latitude: facility.latitude,
                    longitude: facility.longitude
                }
            });
            setSatelliteObservation(res.data);
        } catch (err) {
            console.error('Error fetching satellite observation:', err);
            setSatelliteObservation({
                status: 'error',
                authenticated: false,
                message: 'Failed to connect to Copernicus CDSE.'
            });
        } finally {
            setLoadingSatelliteData(false);
        }
    }, []);

    // Query live Copernicus Sentinel-5P observation whenever facility selection changes
    useEffect(() => {
        if (!selectedFacility || !selectedFacility.latitude || !selectedFacility.longitude) {
            setSatelliteObservation(null);
            return;
        }
        fetchSatelliteObservation(selectedFacility);
    }, [selectedFacility, fetchSatelliteObservation]);

    // Poll backend for new satellite passes — runs every 30 minutes
    const pollSatellitePasses = useCallback(async () => {
        try {
            const res = await api.post('/satellite/sentinel5p/poll-new-passes');
            const { new_passes, detections } = res.data;
            setLastPollTime(new Date());
            if (new_passes > 0) {
                // Show in-page alert with details of the most notable detection
                const top = detections.sort((a, b) => b.anomaly_ppb - a.anomaly_ppb)[0];
                setSatelliteAlert({
                    count: new_passes,
                    facility: top.facility_name,
                    date: top.pass_date,
                    time: top.pass_time,
                    anomaly: top.anomaly_ppb,
                    type: top.stream_type
                });
                // Auto-dismiss after 12 seconds
                setTimeout(() => setSatelliteAlert(null), 12000);
                // Refresh the currently-selected facility panel if it was updated
                const curr = selectedFacilityRef.current;
                if (curr && detections.some(d => d.facility_id === curr.id)) {
                    fetchSatelliteObservation(curr);
                }
            }
        } catch (err) {
            // Silently ignore poll errors (auth not set up, network blip, etc.)
        }
    }, [fetchSatelliteObservation]);

    // Start polling on mount, clear on unmount
    useEffect(() => {
        // Initial poll after 5 seconds (allow page to settle)
        const initialTimeout = setTimeout(pollSatellitePasses, 5000);
        // Recurring every 30 minutes (Sentinel-5P revisit ~1–2 days, NRTI available within 3h)
        satellitePollRef.current = setInterval(pollSatellitePasses, 30 * 60 * 1000);
        return () => {
            clearTimeout(initialTimeout);
            clearInterval(satellitePollRef.current);
        };
    }, [pollSatellitePasses]);

    const getIntensityData = (facilityId) => {
        return stats.find(s => s.facility_id === facilityId) || {
            co2_intensity: 0,
            ch4_intensity: 0,
            api_flaring_intensity: 0,
            total_boe: 0
        };
    };

    const handleSelectFacility = (fac) => {
        if (fac.latitude && fac.longitude) {
            setSelectedFacility(fac);
            setMapCenter([fac.latitude, fac.longitude]);
            setMapZoom(9);
        }
    };

    const handleExportToOgmp = async () => {
        if (!selectedFacility || !satelliteObservation || !satelliteObservation.summary) return;
        try {
            setExportingOgmp(true);
            const res = await api.post('/satellite/sentinel5p/export-to-ogmp', {
                facility_id: selectedFacility.id,
                observation_date: satelliteObservation.summary.latest_observation_date || new Date().toISOString().split('T')[0],
                ch4_column_ppb: satelliteObservation.summary.mean_ch4_column_ppb,
                anomaly_ppb: satelliteObservation.summary.max_anomaly_ppb,
                estimated_emission_rate_kg_hr: satelliteObservation.summary.estimated_emission_rate_kg_hr,
                qa_score: satelliteObservation.summary.mean_qa_score,
                notes: `Sentinel-5P Level-3 CH4 Top-Down observation reconciliation for ${selectedFacility.name}`
            });

            if (res.data && res.data.success) {
                toast.success(`Top-Down Satellite record successfully reconciled with OGMP 2.0 Ledger! (Survey #${res.data.survey_id})`);
            } else {
                toast.error(res.data?.message || 'Failed to export survey to OGMP');
            }
        } catch (err) {
            console.error('Export to OGMP failed:', err);
            toast.error(err.response?.data?.message || 'Failed to reconcile with OGMP ledger');
        } finally {
            setExportingOgmp(false);
        }
    };

    const formatCompact = (num) => {
        if (!num) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return Math.round(num).toLocaleString();
    };

    const getPulseClass = (val) => {
        const threshold = viewMode === 'total' ? 10000 : 500; // Tonnes CO2e or CH4
        if (val > threshold * 10) return 'pulse-red';
        if (val > threshold) return 'pulse-yellow';
        return 'pulse-green';
    };

    const createPulsingIcon = (val) => {
        const pClass = getPulseClass(val);
        const threshold = viewMode === 'total' ? 10000 : 500;
        const radius = val > threshold * 10 ? 12 : (val > threshold ? 9 : 6);
        return L.divIcon({
            className: `marker-pulse ${pClass}`,
            iconSize: [radius * 3, radius * 3],
            iconAnchor: [radius * 1.5, radius * 1.5]
        });
    };

    const createSolidIcon = (val) => {
        const threshold = viewMode === 'total' ? 10000 : 500;
        const color = val > threshold * 10 ? '#ef4444' : (val > threshold ? '#f59e0b' : '#10b981');
        const radius = val > threshold * 10 ? 8 : (val > threshold ? 6 : 4);
        return L.divIcon({
            className: 'solid-marker',
            html: `<div style="width: ${radius * 2}px; height: ${radius * 2}px; border-radius: 50%; background: ${color}; border: 2px solid #fff; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
            iconSize: [radius * 2, radius * 2],
            iconAnchor: [radius, radius]
        });
    };

    if (loading) return (
        <div className="methane-explorer-loading">
            <div className="spinner-large"></div>
            <span>Loading Copernicus Satellite Map & Facility Infrastructure...</span>
        </div>
    );

    const selectedStats = selectedFacility ? getIntensityData(selectedFacility.id) : null;
    const isSatelliteConnected = satelliteConfig && satelliteConfig.connected;

    return (
        <div className="methane-explorer">
            {/* Satellite new-pass floating alert toast */}
            {satelliteAlert && (
                <div style={{
                    position: 'fixed',
                    top: '72px',
                    right: '24px',
                    zIndex: 9999,
                    background: satelliteAlert.anomaly >= 30 ? 'linear-gradient(135deg, #7f1d1d, #991b1b)' : 'linear-gradient(135deg, #1e3a5f, #0c2340)',
                    border: `1px solid ${satelliteAlert.anomaly >= 30 ? '#ef4444' : '#0284c7'}`,
                    borderRadius: '12px',
                    padding: '14px 18px',
                    minWidth: '320px',
                    maxWidth: '400px',
                    boxShadow: `0 8px 32px ${satelliteAlert.anomaly >= 30 ? 'rgba(239,68,68,0.35)' : 'rgba(2,132,199,0.35)'}`,
                    animation: 'slideInRight 0.3s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: satelliteAlert.anomaly >= 30 ? '#fca5a5' : '#7dd3fc', fontWeight: 700, fontSize: '13px' }}>
                        <span style={{ fontSize: '16px' }}>{satelliteAlert.anomaly >= 30 ? '⚠' : '🛰'}</span>
                        <span>{satelliteAlert.anomaly >= 30 ? 'High CH₄ Anomaly Detected' : 'New S5P Overpass'}</span>
                        <button onClick={() => setSatelliteAlert(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '14px', padding: '0 2px' }}>✕</button>
                    </div>
                    <div style={{ color: '#cbd5e1', fontSize: '12px', lineHeight: '1.5' }}>
                        <strong style={{ color: '#f1f5f9' }}>{satelliteAlert.facility}</strong> — {satelliteAlert.date} {satelliteAlert.time}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '2px' }}>
                        <span style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '5px', padding: '2px 8px', fontSize: '11px', color: '#e2e8f0' }}>
                            ΔCH₄ <strong>+{satelliteAlert.anomaly.toFixed(1)} ppb</strong>
                        </span>
                        <span style={{ background: satelliteAlert.type === 'NRTI' ? 'rgba(5,150,105,0.2)' : 'rgba(2,132,199,0.2)', borderRadius: '5px', padding: '2px 8px', fontSize: '11px', color: satelliteAlert.type === 'NRTI' ? '#6ee7b7' : '#7dd3fc' }}>
                            ● {satelliteAlert.type}
                        </span>
                        {satelliteAlert.count > 1 && (
                            <span style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '5px', padding: '2px 8px', fontSize: '11px', color: '#94a3b8' }}>
                                +{satelliteAlert.count - 1} more
                            </span>
                        )}
                    </div>
                    <div style={{ marginTop: '4px', fontSize: '11px', color: '#64748b' }}>
                        Notification added to your bell — check the panel for details.
                    </div>
                </div>
            )}
            <div className="explorer-map-container">
                <MapContainer
                    center={mapCenter}
                    zoom={mapZoom}
                    zoomControl={false}
                    style={{ height: '100%', width: '100%' }}
                >
                    {/* Base Map Layer */}
                    <TileLayer
                        url="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=en&gl=DZ"
                        attribution='&copy; <a href="https://www.google.com/maps">Google Maps</a>'
                    />

                    {/* Copernicus Sentinel-5P Methane Column Raster Overlay */}
                    {showSatelliteLayer && satelliteConfig?.tile_layer_template && (
                        <TileLayer
                            key={satelliteConfig.tile_layer_template}
                            url={satelliteConfig.tile_layer_template}
                            opacity={satelliteOpacity}
                            zIndex={500}
                            attribution='&copy; <a href="https://dataspace.copernicus.eu" target="_blank" rel="noopener noreferrer">Copernicus Sentinel-5P (ESA/EU)</a>'
                        />
                    )}

                    <MapController center={mapCenter} zoom={mapZoom} />
                    <ZoomControl position="bottomright" />

                    {/* Facility Markers & Visual Plume Radii */}
                    {filteredFacilities.map(fac => {
                        const facilityStats = getIntensityData(fac.id);
                        if (!fac.latitude || !fac.longitude) return null;
                        const coords = [fac.latitude, fac.longitude];
                        const val = viewMode === 'total' ? (facilityStats.total_co2e || 0) : (facilityStats.total_ch4 || 0);

                        return (
                            <React.Fragment key={fac.id}>
                                {showSatelliteLayer && (
                                    <Circle
                                        center={coords}
                                        radius={val > 5000 ? 20000 : (val > 500 ? 14000 : 8000)}
                                        pathOptions={{
                                            color: val > 5000 ? '#d73027' : (val > 500 ? '#fdae61' : '#4575b4'),
                                            fillColor: val > 5000 ? '#d73027' : (val > 500 ? '#fdae61' : '#313695'),
                                            fillOpacity: satelliteOpacity * 0.3,
                                            weight: 1.5,
                                            dashArray: '3, 4'
                                        }}
                                    />
                                )}
                                <Marker
                                    position={coords}
                                    icon={createPulsingIcon(val)}
                                    interactive={false}
                                />
                                <Marker
                                    position={coords}
                                    icon={createSolidIcon(val)}
                                    eventHandlers={{
                                        click: () => handleSelectFacility(fac)
                                    }}
                                >
                                    <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                                        <div style={{ fontWeight: 'bold', color: '#0f172a' }}>{fac.name}</div>
                                        <div style={{ fontSize: '0.75rem', color: '#475569' }}>{fac.activity || fac.division || 'Industrial Facility'}</div>
                                        <div style={{ fontSize: '0.8rem', color: '#059669', fontWeight: 600, marginTop: '2px' }}>
                                            {viewMode === 'total' ? `${formatCompact(val)} tCO₂e/yr` : `${formatCompact(val)} tCH₄/yr`}
                                        </div>
                                    </Tooltip>
                                </Marker>
                            </React.Fragment>
                        );
                    })}
                </MapContainer>
            </div>

            {/* Left Filter & Satellite Controls Panel */}
            <div className="floating-panel left-filter-panel">
                <div className="panel-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Layers size={20} color="#10b981" />
                        <h3>Emissions Map &amp; S5P</h3>
                    </div>
                    {isSatelliteConnected ? (
                        <span className="badge-satellite-live" title="Connected to Copernicus CDSE">
                            <Radio size={11} className="pulse-icon" /> Live S5P
                        </span>
                    ) : (
                        <button 
                            className="badge-satellite-offline-btn" 
                            onClick={() => navigate('/settings')}
                            title="Configure Copernicus Credentials in Settings"
                        >
                            <Satellite size={11} /> Config S5P
                        </button>
                    )}
                </div>

                {/* Satellite Layer Controls */}
                <div className="satellite-layer-box">
                    <div className="satellite-toggle-row">
                        <label className="checkbox-label">
                            <input 
                                type="checkbox"
                                checked={showSatelliteLayer}
                                onChange={(e) => setShowSatelliteLayer(e.target.checked)}
                                id="toggle-satellite-layer"
                            />
                            <span className="checkbox-text">
                                <strong>Sentinel-5P CH₄ Layer</strong>
                            </span>
                        </label>
                        <span className="s5p-badge">ESA TROPOMI</span>
                    </div>

                    {showSatelliteLayer && (
                        <div className="satellite-slider-row">
                            <span className="slider-label">Opacity: {Math.round(satelliteOpacity * 100)}%</span>
                            <input 
                                type="range" 
                                min="0.2" 
                                max="1.0" 
                                step="0.05"
                                value={satelliteOpacity}
                                onChange={(e) => setSatelliteOpacity(Number(e.target.value))}
                                className="range-slider-small"
                                id="satellite-opacity-slider"
                            />
                        </div>
                    )}
                </div>

                <div className="filter-section">
                    <label className="filter-label">Search Facility</label>
                    <div style={{ position: 'relative' }}>
                        <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                        <input
                            type="text"
                            placeholder="Type facility name..."
                            value={filters.search}
                            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                            className="explorer-input-search"
                            id="search-facility-input"
                        />
                    </div>
                </div>

                <div className="filter-section">
                    <label className="filter-label">Year</label>
                    <select
                        value={filters.year}
                        onChange={(e) => setFilters({ ...filters, year: e.target.value })}
                        className="explorer-select"
                        id="filter-year-select"
                    >
                        <option value="all">All Years</option>
                        {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
                    </select>
                </div>

                <div className="filter-section">
                    <label className="filter-label">Activity</label>
                    <select
                        value={filters.activity}
                        onChange={(e) => setFilters({ ...filters, activity: e.target.value })}
                        className="explorer-select"
                        id="filter-activity-select"
                    >
                        <option value="all">All Activities</option>
                        {availableActivities.map(act => (
                            <option key={act} value={act}>{act}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-section">
                    <label className="filter-label">Visualization Mode</label>
                    <div className="view-mode-toggle">
                        <button className={viewMode === 'total' ? 'active' : ''} onClick={() => setViewMode('total')}>Total GHG</button>
                        <button className={viewMode === 'methane' ? 'active' : ''} onClick={() => setViewMode('methane')}>Methane (CH₄)</button>
                    </div>
                </div>

                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Visible Facilities</span>
                    <span style={{ color: '#10b981', fontWeight: 700 }}>{filteredFacilities.length}</span>
                </div>

                {/* Region List */}
                <div className="region-list-container">
                    {filteredFacilities.map(fac => {
                        const facilityStats = getIntensityData(fac.id);
                        return (
                            <div
                                key={fac.id}
                                className={`region-list-item ${selectedFacility?.id === fac.id ? 'active' : ''}`}
                                onClick={() => handleSelectFacility(fac)}
                            >
                                <div className="region-name">{fac.name}</div>
                                <div className="region-emission-val" style={{ color: getPulseClass(viewMode === 'total' ? (facilityStats.total_co2e || 0) : (facilityStats.total_ch4 || 0)) === 'pulse-red' ? '#ef4444' : (getPulseClass(viewMode === 'total' ? (facilityStats.total_co2e || 0) : (facilityStats.total_ch4 || 0)) === 'pulse-yellow' ? '#f59e0b' : '#10b981') }}>
                                    {viewMode === 'total' ? formatCompact(facilityStats.total_co2e) : formatCompact(facilityStats.total_ch4)} {viewMode === 'total' ? 'tCO₂e' : 'tCH₄'}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Bottom-Left Sentinel-5P Methane Legend */}
            {showSatelliteLayer && showLegend && (
                <div className="floating-panel satellite-legend-panel">
                    <div className="legend-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Satellite size={14} color="#0284c7" />
                            <strong>Sentinel-5P CH₄ Column Mixing Ratio</strong>
                        </div>
                        <button className="legend-close-btn" onClick={() => setShowLegend(false)} title="Hide Legend">
                            <X size={12} />
                        </button>
                    </div>
                    <div className="legend-gradient-bar"></div>
                    <div className="legend-labels">
                        <span>&lt; 1,750 ppb</span>
                        <span>1,800</span>
                        <span>1,850</span>
                        <span>1,900</span>
                        <span>&ge; 1,950 ppb</span>
                    </div>
                    <div className="legend-footer">
                        <span>L3 Dry Air Mole Fraction • 5.5×7km</span>
                        <a href="https://dataspace.copernicus.eu" target="_blank" rel="noopener noreferrer" className="legend-link">
                            CDSE <ExternalLink size={10} />
                        </a>
                    </div>
                </div>
            )}

            {/* Right Detail Panel for Selected Facility */}
            {selectedFacility && (
                <div className="floating-panel right-detail-panel">
                    <button className="close-detail-btn" onClick={() => setSelectedFacility(null)} title="Close">
                        <X size={16} />
                    </button>

                    <div className="detail-header">
                        <h4>{selectedFacility.name}</h4>
                        <div className="detail-location">
                            <MapPin size={13} />
                            {selectedFacility.activity} • {selectedFacility.country || 'Algeria'}
                        </div>
                        <div className="coords-tag">
                            {selectedFacility.latitude?.toFixed(4)}°N, {selectedFacility.longitude?.toFixed(4)}°E
                        </div>
                    </div>

                    {/* Satellite Top-Down Section */}
                    <div className="satellite-facility-card">
                        <div className="satellite-card-header">
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <Satellite size={16} color="#0284c7" />
                                <strong>Top-Down Satellite Pass (S5P)</strong>
                            </div>
                            {loadingSatelliteData && <RefreshCw size={13} className="spin-fast" color="#0284c7" />}
                        </div>

                        {loadingSatelliteData ? (
                            <div className="sat-loading-state">
                                <span>Querying Copernicus STAC Catalog...</span>
                            </div>
                        ) : satelliteObservation && satelliteObservation.authenticated && satelliteObservation.summary ? (
                            <div className="sat-data-body">
                                <div className="sat-stat-row">
                                    <div className="sat-stat">
                                        <span className="sat-label">Mean CH₄ Column</span>
                                        <span className="sat-val">{satelliteObservation.summary.mean_ch4_column_ppb.toFixed(1)} ppb</span>
                                    </div>
                                    <div className="sat-stat">
                                        <span className="sat-label">Max Anomaly (&Delta;CH₄)</span>
                                        <span className="sat-val highlight-amber">+{satelliteObservation.summary.max_anomaly_ppb.toFixed(1)} ppb</span>
                                    </div>
                                </div>

                                <div className="sat-stat-row">
                                    <div className="sat-stat">
                                        <span className="sat-label">Est. Emission Rate</span>
                                        <span className="sat-val highlight-red">
                                            {satelliteObservation.summary.estimated_emission_rate_kg_hr > 0 
                                                ? `${satelliteObservation.summary.estimated_emission_rate_kg_hr.toFixed(1)} kg/hr`
                                                : 'Background Baseline'}
                                        </span>
                                    </div>
                                    <div className="sat-stat">
                                        <span className="sat-label">Annualized Flux</span>
                                        <span className="sat-val">
                                            {satelliteObservation.summary.annualized_ch4_tonnes > 0
                                                ? `${satelliteObservation.summary.annualized_ch4_tonnes.toFixed(1)} tCH₄/yr`
                                                : '0.0 t/yr'}
                                        </span>
                                    </div>
                                </div>

                                <div className="sat-meta-row">
                                    <span>
                                        Latest Pass: <strong>{satelliteObservation.summary.latest_observation_date}</strong>
                                        {satelliteObservation.summary.latest_observation_time && (
                                            <> at {satelliteObservation.summary.latest_observation_time}</>
                                        )}
                                    </span>
                                    <span>QA: {(satelliteObservation.summary.mean_qa_score * 100).toFixed(0)}%</span>
                                </div>
                                <div className="sat-meta-row" style={{ marginTop: '4px' }}>
                                    {satelliteObservation.summary.stream_type && (
                                        <span style={{
                                            background: satelliteObservation.summary.stream_type.includes('Near Real') ? 'rgba(5,150,105,0.15)' : 'rgba(2,132,199,0.15)',
                                            color: satelliteObservation.summary.stream_type.includes('Near Real') ? '#059669' : '#0284c7',
                                            border: `1px solid ${satelliteObservation.summary.stream_type.includes('Near Real') ? '#059669' : '#0284c7'}`,
                                            borderRadius: '4px',
                                            padding: '1px 7px',
                                            fontSize: '10px',
                                            fontWeight: 600,
                                            letterSpacing: '0.03em'
                                        }}>
                                            ● {satelliteObservation.summary.stream_type}
                                        </span>
                                    )}
                                    {satelliteObservation.summary.total_recent_passes > 0 && (
                                        <span style={{ color: '#94a3b8', fontSize: '11px' }}>
                                            {satelliteObservation.summary.total_recent_passes} passes in window
                                        </span>
                                    )}
                                </div>

                                <button 
                                    className="btn-export-ogmp"
                                    onClick={handleExportToOgmp}
                                    disabled={exportingOgmp}
                                    id="reconcile-ogmp-btn"
                                >
                                    {exportingOgmp ? (
                                        <>
                                            <span className="spinner-small"></span>
                                            <span>Reconciling with OGMP 2.0...</span>
                                        </>
                                    ) : (
                                        <>
                                            <ShieldCheck size={15} />
                                            <span>Record in OGMP Level 5 Ledger</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        ) : (
                            <div className="sat-unconfigured-notice">
                                <AlertCircle size={15} color="#d97706" />
                                <div>
                                    <p className="notice-title">Live S5P Stream Unconfigured</p>
                                    <p className="notice-desc">
                                        Configure your free Copernicus Data Space account in Settings to stream authentic Sentinel-5P observations and reconcile Level 5 surveys.
                                    </p>
                                    <button 
                                        className="btn-configure-satellite"
                                        onClick={() => navigate('/settings')}
                                    >
                                        Configure Copernicus in Settings &rarr;
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Bottom-Up Activity Emissions Grid */}
                    <div className="stats-grid" style={{ marginTop: '14px' }}>
                        {/* Total emissions — full-width highlight box */}
                        <div className="stat-box full">
                            <div className="stat-label">{viewMode === 'total' ? 'Reported GHG Emissions' : 'Reported Methane'}</div>
                            <div className="stat-value highlight">
                                {viewMode === 'total' ? formatCompact(selectedStats.total_co2e) : formatCompact(selectedStats.total_ch4)}
                            </div>
                            <div className="stat-unit">{viewMode === 'total' ? 'tCO₂e / Year (Bottom-Up)' : 'tCH₄ / Year (Bottom-Up)'}</div>
                        </div>

                        {/* Total Production */}
                        <div className="stat-box">
                            <div className="stat-label">Total Production</div>
                            <div className="stat-value" style={{ color: '#059669' }}>{formatCompact(selectedStats.total_boe)}</div>
                            <div className="stat-unit">BOE / Year</div>
                        </div>

                        {/* Carbon / Methane Intensity */}
                        <div className="stat-box">
                            <div className="stat-label">{viewMode === 'total' ? 'Carbon Intensity' : 'Methane Intensity'}</div>
                            <div className="stat-value" style={{ color: viewMode === 'total' ? '#0284c7' : '#d97706' }}>
                                {viewMode === 'total' ? (selectedStats.co2_intensity ?? 0).toFixed(2) : (selectedStats.ch4_intensity ?? 0).toFixed(3)}
                            </div>
                            <div className="stat-unit">{viewMode === 'total' ? 'kgCO₂e/boe' : 'kgCH₄/boe'}</div>
                        </div>

                        {/* Flaring Intensity */}
                        <div className="stat-box">
                            <div className="stat-label">Flaring Int.</div>
                            <div className="stat-value" style={{ color: '#dc2626' }}>{(selectedStats.api_flaring_intensity ?? 0).toFixed(2)}</div>
                            <div className="stat-unit">kgCO₂e/boe</div>
                        </div>

                        {/* Field ID */}
                        <div className="stat-box">
                            <div className="stat-label">Field ID</div>
                            <div className="stat-value" style={{ fontSize: '1rem', color: '#475569' }}>{selectedFacility.code || 'N/A'}</div>
                            <div className="stat-unit">Reference</div>
                        </div>
                    </div>

                    <button className="zoom-button" onClick={() => { setMapZoom(11); setMapCenter([selectedFacility.latitude, selectedFacility.longitude]); }}>
                        <Activity size={18} />
                        Focus Facility Top-Down
                    </button>
                </div>
            )}
        </div>
    );
};

export default EmissionsMap;
