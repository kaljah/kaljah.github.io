import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Search, Filter, X, MapPin, Activity, Wind, Flame, TrendingUp, Info } from 'lucide-react';
import api from '../api';
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

    const fetchData = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams({
                year: filters.year
            });

            const [facRes, statRes, yearRes] = await Promise.all([
                api.get('/facilities'),
                api.get(`/dashboard/intensity-stats?${params}`),
                api.get('/dashboard/years')
            ]);
            setFacilities(facRes.data);
            setStats(statRes.data);
            setAvailableYears(yearRes.data);
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

    if (loading) return <div className="methane-explorer" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1e293b', fontSize: '1.2rem', fontWeight: 600 }}>Loading Satellite Data...</div>;

    const selectedStats = selectedFacility ? getIntensityData(selectedFacility.id) : null;

    return (
        <div className="methane-explorer">
            <div className="explorer-map-container">
                <MapContainer
                    center={mapCenter}
                    zoom={mapZoom}
                    zoomControl={false}
                    style={{ height: '100%', width: '100%' }}
                >
                    <TileLayer
                        url="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=en&gl=DZ"
                        attribution='&copy; <a href="https://www.google.com/maps">Google Maps</a>'
                    />
                    <MapController center={mapCenter} zoom={mapZoom} />
                    <ZoomControl position="bottomright" />

                    {filteredFacilities.map(fac => {
                        const facilityStats = getIntensityData(fac.id);
                        if (!fac.latitude || !fac.longitude) return null;
                        const coords = [fac.latitude, fac.longitude];
                        const val = viewMode === 'total' ? (facilityStats.total_co2e || 0) : (facilityStats.total_ch4 || 0);

                        return (
                            <React.Fragment key={fac.id}>
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
                                />
                            </React.Fragment>
                        );
                    })}
                </MapContainer>
            </div>

            {/* Left Filter Panel */}
            <div className="floating-panel left-filter-panel">
                <div className="panel-header">
                    <h3>Emissions MAP</h3>
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
                            style={{ width: '100%', background: 'rgba(0,0,0,0.05)', border: '1px solid rgba(0,0,0,0.1)', borderRadius: '10px', padding: '10px 10px 10px 40px', color: '#1e293b', fontSize: '0.9rem', outline: 'none' }}
                        />
                    </div>
                </div>

                <div className="filter-section">
                    <label className="filter-label">Year</label>
                    <select
                        value={filters.year}
                        onChange={(e) => setFilters({ ...filters, year: e.target.value })}
                        style={{ width: '100%', background: 'rgba(0,0,0,0.05)', border: '1px solid rgba(0,0,0,0.1)', borderRadius: '10px', padding: '10px', color: '#1e293b', fontSize: '0.9rem', outline: 'none' }}
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
                        style={{ width: '100%', background: 'rgba(0,0,0,0.05)', border: '1px solid rgba(0,0,0,0.1)', borderRadius: '10px', padding: '10px', color: '#1e293b', fontSize: '0.9rem', outline: 'none' }}
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

                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Visible Regions</span>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>{filteredFacilities.length}</span>
                </div>

                {/* No-coordinates warning */}
                {filteredFacilities.length === 0 && facilities.length > 0 && (
                    <div style={{ margin: '10px 0', padding: '10px 12px', background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px', fontSize: '0.78rem', color: '#92400e' }}>
                        <strong>⚠ No map markers</strong><br />
                        {facilities.filter(f => !f.latitude || !f.longitude).length} facilit{facilities.filter(f => !f.latitude || !f.longitude).length === 1 ? 'y has' : 'ies have'} no coordinates set. Set latitude &amp; longitude in Manage Data → Facilities to display them on the map.
                    </div>
                )}

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

            {/* Right Detail Panel */}
            {selectedFacility && (
                <div className="floating-panel right-detail-panel">
                    <button className="close-detail-btn" onClick={() => setSelectedFacility(null)} title="Close">
                        <X size={16} />
                    </button>

                    <div className="detail-header">
                        <h4>{selectedFacility.name}</h4>
                        <div className="detail-location">
                            <MapPin size={13} />
                            {selectedFacility.activity} • {selectedFacility.division}
                        </div>
                    </div>

                    <div className="stats-grid">
                        {/* Total emissions — full-width highlight box */}
                        <div className="stat-box full">
                            <div className="stat-label">{viewMode === 'total' ? 'Total GHG Emissions' : 'Methane Emissions'}</div>
                            <div className="stat-value highlight">
                                {viewMode === 'total' ? formatCompact(selectedStats.total_co2e) : formatCompact(selectedStats.total_ch4)}
                            </div>
                            <div className="stat-unit">{viewMode === 'total' ? 'tCO₂e / Year' : 'tCH₄ / Year'}</div>
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
                        Focus High-Res Analytics
                    </button>

                </div>
            )}
        </div>
    );
};

export default EmissionsMap;
