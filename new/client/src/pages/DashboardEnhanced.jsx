import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import { SkeletonCard } from '../components/SkeletonLoader';
import { PieChart as PieChartWrapper, LineChart as LineChartWrapper } from '../components/charts';
import CustomDropdown from '../components/CustomDropdown';
import { formatCompactNumber, formatNumber, calculateTrend } from '../utils/formatters';
import { useLayout } from '../context/LayoutContext';
import { ChevronDown, ChevronUp } from 'lucide-react';
import './Dashboard.css';

// Simple Linear Regression for Forecasting
const calculateForecast = (data) => {
    if (data.length < 2) return [];

    const n = data.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

    data.forEach(p => {
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
    const [currentActivity, setCurrentActivity] = useState('all');
    const [currentDivision, setCurrentDivision] = useState('all');
    const [currentRegion, setCurrentRegion] = useState('all');
    const [currentSegment, setCurrentSegment] = useState('all');
    const [facilities, setFacilities] = useState([]);
    const [availableFilters, setAvailableFilters] = useState({ years: [], regions: [], segments: [] });

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
        other: 0
    });

    const [trendData, setTrendData] = useState([]);
    const [categoricalData, setCategoricalData] = useState([]);
    const [currentYear, setCurrentYear] = useState('all');
    const [expandedActivities, setExpandedActivities] = useState({});
    const [expandedDivisions, setExpandedDivisions] = useState({});
    const [goal, setGoal] = useState(null);
    const [baseYear, setBaseYear] = useState(null);
    const [intensity, setIntensity] = useState(0);
    const [loading, setLoading] = useState(true);
    const [isCompareMode, setIsCompareMode] = useState(false);
    const [variance, setVariance] = useState({ emissions: '—', intensity: '—' });
    const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    const [categoricalCollapsed, setCategoricalCollapsed] = useState(true);
    const [detailedBreakdownCollapsed, setDetailedBreakdownCollapsed] = useState(true);

    const navigate = useNavigate();

    // Load facilities and available filters
    useEffect(() => {
        const loadInitialData = async () => {
            try {
                const [facRes, filterRes] = await Promise.all([
                    api.get('/facilities'),
                    api.get('/filters/available')
                ]);
                setFacilities(facRes.data);
                setAvailableFilters(filterRes.data);

                // Set default year to 'all' (explicitly, though it initializes to 'all')
                // if (filterRes.data.years?.length > 0) {
                //     setCurrentYear(filterRes.data.years[0].toString());
                // }
            } catch (error) {
                console.error('Failed to load initial data:', error);
            }
        };
        loadInitialData();
    }, []);


    // Load dashboard data
    useEffect(() => {
        loadDashboardData();
    }, [currentActivity, currentDivision, currentRegion, currentYear, currentSegment, isCompareMode]);

    const loadDashboardData = async () => {
        try {
            setLoading(true);
            const queryParams = {
                facilityId: currentRegion,
                activity: currentActivity,
                division: currentDivision
            };
            if (currentSegment !== 'all') {
                queryParams.segment = currentSegment;
            }
            if (isCompareMode) {
                queryParams.groupBy = 'facility';
            }

            const filterParams = new URLSearchParams(queryParams);
            if (currentYear !== 'all') {
                filterParams.append('year', currentYear);
            }

            // Part 3: Optimized Batch Dashboard API Call
            const batchRes = await api.get(`/dashboard/batch-all?${filterParams}`);
            const batch = batchRes.data;

            const summaryData = batch.summary || [];
            const mitData = batch.mitigation || [];
            const s3Data = batch.scope3_summary || { total: 0 };
            const catData = batch.categorical_breakdown || [];
            const intensityData = batch.intensity_stats || [];
            const gObj = batch.goal;
            const bYearObj = batch.base_year;

            setGoal(gObj);
            setBaseYear(bYearObj);
            setCategoricalData(catData);

            let totals = {
                totalEmissions: 0,
                scope1: 0,
                scope2: 0,
                // BUG-UI-04 FIX: Apply year filter to Scope 3 just like Scope 1 & 2
                scope3: currentYear === 'all'
                    ? (s3Data.total || 0)
                    : (s3Data.by_year?.[currentYear] || s3Data.by_year?.[parseInt(currentYear)] || 0),
                mitigation: 0,
                methaneEmissions: 0,
                purchasedEnergy: 0,
                combustion: 0,
                flaring: 0,
                venting: 0,
                other: 0,
                totalProductionBoe: 0
            };

            const yearlyTrend = {};
            const facilityNames = {};
            if (isCompareMode) {
                facilities.forEach(f => { facilityNames[f.id] = f.name; });
            }

            summaryData.forEach(row => {
                const year = row.year;
                const fid = row.facility_id || 'total';
                const s1 = row.scope1_total || 0;
                const s2 = row.scope2_total || 0;
                const total = s1 + s2;

                // Handle Totals for Hero Card (Only if matches filter)
                // BUG FIX: Unconditionally aggregate totals so that Compare Mode correctly sums the selected regions,
                // instead of keeping totals at 0.
                if (currentYear === 'all' || year.toString() === currentYear) {
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

                if (isCompareMode && fid !== 'total') {
                    const name = facilityNames[fid] || `Facility ${fid}`;
                    yearlyTrend[year][name] = Number(((yearlyTrend[year][name] || 0) + total).toFixed(2));
                } else if (!isCompareMode && fid === 'total') {
                    yearlyTrend[year].emissions = Number(((yearlyTrend[year].emissions || 0) + total).toFixed(3));
                    yearlyTrend[year].scope1 = Number(((yearlyTrend[year].scope1 || 0) + s1).toFixed(3));
                    yearlyTrend[year].scope2 = Number(((yearlyTrend[year].scope2 || 0) + s2).toFixed(3));
                }
            });

            mitData.forEach(item => {
                if (currentYear === 'all' || item.year.toString() === currentYear) {
                    totals.mitigation += item.quantity_tco2e || 0;
                }
            });

            totals.netEmissions = totals.totalEmissions - totals.mitigation;

            // Weighted Intensity Calculation
            let weightedIntensity = 0;
            if (intensityData && intensityData.length > 0) {
                let totalEmissionsForIntensity = 0;
                let totalBoeForIntensity = 0;
                intensityData.forEach(d => {
                    if (d.total_boe > 0) {
                        totalEmissionsForIntensity += (d.co2_intensity * d.total_boe);
                        totalBoeForIntensity += d.total_boe;
                    }
                });
                if (totalBoeForIntensity > 0) {
                    weightedIntensity = totalEmissionsForIntensity / totalBoeForIntensity;
                }
            }
            setIntensity(weightedIntensity);

            // YoY Variance Calculation
            if (currentYear !== 'all') {
                const cy = parseInt(currentYear);
                const py = cy - 1;
                
                // BUG FIX: Calculate aggregate emissions dynamically from summaryData to support Compare Mode
                // because yearlyTrend uses facility names instead of 'emissions' key when in Compare Mode.
                let cyEmissions = 0, pyEmissions = 0;
                summaryData.forEach(row => {
                    const total = (row.scope1_total || 0) + (row.scope2_total || 0);
                    if (row.year === cy) cyEmissions += total;
                    if (row.year === py) pyEmissions += total;
                });

                if (pyEmissions > 0) {
                    setVariance({
                        emissions: calculateTrend(cyEmissions, pyEmissions),
                        intensity: '—' // Logic for intensity YoY if available
                    });
                } else {
                    setVariance({ emissions: '—', intensity: '—' });
                }
            } else {
                setVariance({ emissions: '—', intensity: '—' });
            }

            // Target Trajectory Calculation
            let trendArray = Object.values(yearlyTrend).sort((a, b) => a.year - b.year);

            if (gObj && bYearObj && !isCompareMode) {
                const baseEmissions = yearlyTrend[bYearObj.year]?.emissions || trendArray[0]?.emissions || 0;
                const startYear = bYearObj.year;
                const endYear = gObj.year;
                const targetVal = gObj.target_amount;

                // Pad trendArray with future years up to endYear if needed
                const lastYearWithData = trendArray.length > 0 ? trendArray[trendArray.length - 1].year : startYear;
                if (endYear > lastYearWithData) {
                    for (let y = lastYearWithData + 1; y <= endYear; y++) {
                        // Check if year already exists (e.g. from forecast)
                        if (!trendArray.find(t => t.year === y)) {
                            trendArray.push({ year: y });
                        }
                    }
                }

                // Sort again to be sure
                trendArray.sort((a, b) => a.year - b.year);

                trendArray.forEach(point => {
                    if (point.year >= startYear && point.year <= endYear) {
                        const progress = (point.year - startYear) / (endYear - startYear);
                        point.trajectory = Number((baseEmissions + (targetVal - baseEmissions) * progress).toFixed(2));
                    }
                });
            }

            // FORECAST LOGIC (Only in standard view, if no goals or even with goals?)
            // Let's add forecast if we have > 1 year of data and NOT in compare mode
            if (!isCompareMode) {
                const historicalData = trendArray.filter(d => d.emissions !== undefined).map(d => ({ year: d.year, emissions: d.emissions }));
                const forecastPoints = calculateForecast(historicalData);

                // Merge forecast into trendArray
                forecastPoints.forEach(fp => {
                    const existing = trendArray.find(t => t.year === fp.year);
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
            setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));

        } catch (error) {
            console.error('Dashboard load error:', error);
            toast.error('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    const loadCategoricalData = async () => {
        // Now integrated into loadDashboardData for performance
    };



    const getSegmentOptions = () => {
        const segments = availableFilters.segments || [];
        return [
            { value: 'all', label: 'All Supply Chains' },
            ...segments.map(s => ({ value: s, label: s }))
        ];
    };

    const getActivityOptions = () => {
        const filtered = availableFilters.regions.filter(r =>
            currentSegment === 'all' || r.segment === currentSegment
        );
        const activities = new Set(filtered.map(r => r.activity));
        return [
            { value: 'all', label: 'All Activities' },
            ...Array.from(activities).sort().map(a => ({ value: a, label: formatActivityName(a) }))
        ];
    };

    const getDivisionOptions = () => {
        let divisionsSet = new Set();
        const filtered = availableFilters.regions.filter(r =>
            (currentSegment === 'all' || r.segment === currentSegment) &&
            (currentActivity === 'all' || r.activity === currentActivity)
        );
        filtered.forEach(r => divisionsSet.add(r.division));
        return [
            { value: 'all', label: 'All Divisions' },
            ...Array.from(divisionsSet).sort().map(d => ({ value: d, label: d }))
        ];
    };

    const getRegionOptions = () => {
        const filtered = availableFilters.regions.filter(f =>
            (currentSegment === 'all' || f.segment === currentSegment) &&
            (currentActivity === 'all' || f.activity === currentActivity) &&
            (currentDivision === 'all' || f.division === currentDivision)
        );
        return [
            { value: 'all', label: 'All Regions' },
            ...filtered.map(f => ({
                value: f.id.toString(),
                label: f.name,
                subLabel: f.field
            }))
        ];
    };

    const getYearOptions = () => {
        return [
            { value: 'all', label: 'All Years' },
            ...availableFilters.years.sort((a, b) => b - a).map(y => ({ value: y.toString(), label: y.toString() }))
        ];
    };

    const handleSegmentChange = (value) => {
        setCurrentSegment(value);
        setCurrentActivity('all');
        setCurrentDivision('all');
        setCurrentRegion('all');
    };

    const handleActivityChange = (value) => {
        setCurrentActivity(value);
        setCurrentDivision('all');
        setCurrentRegion('all');
    };

    const handleDivisionChange = (value) => {
        setCurrentDivision(value);
        setCurrentRegion('all');
    };

    const sourceChartData = useMemo(() => [
        // BUG-UI-05 FIX: Guard with ?? 0 to prevent .toFixed() on undefined when stats update fails
        { name: 'Combustion', value: Number((stats.combustion ?? 0).toFixed(2)), color: '#10b981' },
        { name: 'Flaring', value: Number((stats.flaring ?? 0).toFixed(2)), color: '#ff6600' },
        { name: 'Venting', value: Number((stats.venting ?? 0).toFixed(2)), color: '#f59e0b' },
        { name: 'Other', value: Number((stats.other ?? 0).toFixed(2)), color: '#3b82f6' }
    ].filter(d => d.value > 0), [stats]);

    // Helper to map DB activity acronyms to readable legends
    const formatActivityName = (act) => {
        if (!act) return 'Other';
        const lower = act.toLowerCase().trim();
        if (lower === 'ep' || lower === 'e&p' || lower.includes('e&p')) return 'E&P (Upstream)';
        if (lower === 'lqs' || lower.includes('lqs')) return 'LQS (Liquefaction)';
        if (lower === 'rpc' || lower.includes('rpc')) return 'RPC (Refining)';
        if (lower === 'trc' || lower.includes('trc')) return 'TRC (Transport)';
        return act;
    };

    // Palette: one distinct color per activity
    const ACTIVITY_PALETTE = ['#f59e0b', '#3b82f6', '#10b981', '#6366f1', '#ef4444', '#ec4899', '#14b8a6', '#a855f7'];
    const ACTIVITY_COLOR_MAP = {
        'E&P (Upstream)':       '#f59e0b',  // amber
        'LQS (Liquefaction)':   '#3b82f6',  // blue
        'RPC (Refining)':       '#10b981',  // green
        'TRC (Transport)':      '#6366f1',  // indigo
    };

    const activityChartData = useMemo(() => {
        const acting = {};
        categoricalData.forEach(item => {
            const act = formatActivityName(item.activity);
            acting[act] = (acting[act] || 0) + (item.total_emissions || 0);
        });
        const entries = Object.entries(acting)
            .map(([name, value]) => ({ name, value: Number(value.toFixed(2)) }))
            .filter(d => d.value > 0);

        return entries.map((entry, index) => {
            return {
                ...entry,
                color: ACTIVITY_COLOR_MAP[entry.name] || ACTIVITY_PALETTE[index % ACTIVITY_PALETTE.length]
            };
        });
    }, [categoricalData]);

    // Set TopBar content
    useEffect(() => {
        setTopBarLeft(
            <div className="dashboard-filters">
                <div className="filter-wrapper">
                    <CustomDropdown options={getYearOptions()} value={currentYear} onChange={setCurrentYear} placeholder="Year" />
                </div>
                <div className="filter-wrapper">
                    <CustomDropdown options={getSegmentOptions()} value={currentSegment} onChange={handleSegmentChange} placeholder="Supply Chain" />
                </div>
                <div className="filter-wrapper">
                    <CustomDropdown options={getActivityOptions()} value={currentActivity} onChange={handleActivityChange} placeholder="Activity" />
                </div>
                <div className="filter-wrapper">
                    <CustomDropdown options={getDivisionOptions()} value={currentDivision} onChange={handleDivisionChange} placeholder="Division" />
                </div>
                <div className="filter-wrapper">
                    <CustomDropdown options={getRegionOptions()} value={currentRegion} onChange={setCurrentRegion} placeholder="Region" />
                </div>
            </div>
        );

        setTopBarRight(
            goal ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{
                        fontSize: '0.8rem', fontWeight: 600, color: '#6b7280',
                        display: 'flex', alignItems: 'center', gap: '6px'
                    }}>
                        Target {goal.year}:
                        <strong style={{ color: '#111827' }}>
                            {Number(goal.target_amount).toLocaleString()} tCO₂e
                        </strong>
                    </span>
                    <button
                        className="action-button secondary"
                        style={{ padding: '5px 12px', fontSize: '0.78rem' }}
                        onClick={() => navigate('/manage-data', { state: { tab: 'goals' } })}
                        title="Manage emission goals and base years in Manage Data"
                    >
                        Edit Goals
                    </button>
                </div>
            ) : (
                <button
                    className="action-button secondary"
                    style={{ padding: '5px 12px', fontSize: '0.78rem' }}
                    onClick={() => navigate('/manage-data', { state: { tab: 'goals' } })}
                    title="Set emission targets in Manage Data"
                >
                    + Set Emission Target
                </button>
            )
        );

        return () => { setTopBarLeft(null); setTopBarRight(null); };
    }, [currentActivity, currentDivision, currentRegion, currentYear, currentSegment, facilities, goal, navigate, setTopBarLeft, setTopBarRight]);

    const toggleActivity = (act) => {
        setExpandedActivities(prev => ({ ...prev, [act]: !prev[act] }));
    };

    const toggleDivision = (div) => {
        setExpandedDivisions(prev => ({ ...prev, [div]: !prev[div] }));
    };

    const getHierarchicalData = useMemo(() => {
        const hierarchy = {};
        categoricalData.forEach(item => {
            const act = item.activity || 'Unassigned';
            const div = item.division || 'Unknown';
            if (!hierarchy[act]) hierarchy[act] = { total: 0, divisions: {} };
            if (!hierarchy[act].divisions[div]) hierarchy[act].divisions[div] = { total: 0, regions: [] };
            hierarchy[act].total += item.total_emissions;
            hierarchy[act].divisions[div].total += item.total_emissions;
            hierarchy[act].divisions[div].regions.push(item);
        });
        return hierarchy;
    }, [categoricalData]);

    if (loading) {
        return <LoadingSpinner message="Loading Dashboard Data..." fullScreen />;
    }

    return (
        <div className="dashboard-content">
            <div className="dashboard-grid">
                <div className="dashboard-header-row">
                    <h1 className="grid-title">GHG Emissions Dashboard</h1>
                    <div className="live-badge">
                        <div className="pulse-dot"></div>
                        Live Content • Updated {lastUpdated}
                    </div>
                </div>

                {/* Hero Overview Card */}
                <div className="card hero-card">
                    <div className="hero-header">
                        <h2 className="hero-title">Emissions Overview</h2>
                        <div className="location-badge">
                            {currentRegion !== 'all' ? (facilities.find(f => f.id.toString() === currentRegion)?.name || 'Region') :
                                currentDivision !== 'all' ? currentDivision :
                                    currentActivity !== 'all' ? currentActivity : 'All Regions'}
                        </div>
                    </div>

                    <div className="hero-stats-grid">
                        <div className="stat-item">
                            <div className="stat-label">Gross Emissions</div>
                            <div className="stat-value-row">
                                <div className="stat-value">{formatCompactNumber(stats.totalEmissions)}</div>
                                <span className="stat-unit">tCO₂e</span>
                                {currentYear !== 'all' && variance.emissions !== '—' && (
                                    <span className={`variance-badge ${variance.emissions.startsWith('+') ? 'danger' : 'success'}`}>
                                        {variance.emissions}
                                    </span>
                                )}
                            </div>
                            {goal && goal.target_amount > 0 && (
                                <div className="stat-sublabel" style={{ marginTop: '8px' }}>
                                    <span className={`goal-progress-badge ${(stats.totalEmissions / goal.target_amount) > 1 ? 'danger' :
                                        (stats.totalEmissions / goal.target_amount) > 0.9 ? 'warning' : 'normal'
                                        }`}>
                                        {((stats.totalEmissions / goal.target_amount) * 100).toFixed(1)}% GOAL
                                    </span>
                                </div>
                            )}
                        </div>

                        <div className="stat-item border-left">
                            <div className="stat-label">Net Emissions</div>
                            <div className="stat-value-row">
                                <div className="stat-value success">{formatCompactNumber(stats.netEmissions)}</div>
                                <span className="stat-unit">tCO₂e</span>
                            </div>
                            <div className="stat-sublabel">Less <span className="success-text">{formatCompactNumber(stats.mitigation)}</span> Mitigation</div>
                        </div>

                        <div className="stat-item border-left">
                            <div className="stat-label">Total CH4 (Methane)</div>
                            <div className="stat-value-row">
                                <div className="stat-value warning">{formatCompactNumber(stats.methaneEmissions)}</div>
                                <span className="stat-unit">tCH₄</span>
                            </div>
                        </div>

                        <div className="stat-item border-left">
                            <div className="stat-label">Performance Intensity</div>
                            <div className="stat-value-row">
                                <div className="stat-value" style={{ color: '#8b5cf6' }}>{formatCompactNumber(intensity, 2)}</div>
                                <span className="stat-unit">kg/BOE</span>
                            </div>
                            <div className="stat-sublabel">CO₂e Intensity (Scope 1+2)</div>
                        </div>
                    </div>

                    <div className="scope-pills-row">
                        <div className="scope-pill scope-1">
                            <span className="pill-label">Scope 1 (Direct)</span>
                            <span className="pill-value">{formatCompactNumber(stats.scope1)} tCO₂e</span>
                        </div>
                        <div className="scope-pill scope-2">
                            <span className="pill-label">Scope 2 (Indirect)</span>
                            <span className="pill-value">{formatCompactNumber(stats.scope2)} tCO₂e</span>
                        </div>
                        <div className="scope-pill scope-3">
                            <span className="pill-label">Scope 3 (Supply Chain)</span>
                            <span className="pill-value">{formatCompactNumber(stats.scope3)} tCO₂e</span>
                        </div>
                    </div>
                </div>

                {/* --- NEW SECTION: Charts (Trend & Donut) --- */}
                <div className="charts-section">
                    {/* Trend Chart - Full Width or large */}
                    <div className="card trend-card-enhanced">
                        <div className="card-header-row">
                            <h3 className="card-title">Emissions Trend</h3>
                            <div className="card-header-actions">
                                {!isCompareMode && (
                                    <div className="card-info-badge">
                                        Over Time
                                    </div>
                                )}
                                <button
                                    className={`compare-toggle-btn ${isCompareMode ? 'active' : ''}`}
                                    onClick={() => setIsCompareMode(!isCompareMode)}
                                >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M18 20V10M12 20V4M6 20v-6" />
                                    </svg>
                                    {isCompareMode ? 'Standard View' : 'Compare Regions'}
                                </button>
                            </div>
                        </div>
                        <div className="chart-container" style={{ height: '600px', width: '100%', minWidth: 0, position: 'relative' }}>
                            <LineChartWrapper
                                data={trendData}
                                xKey="year"
                                lines={isCompareMode ?
                                    Object.keys(trendData[0] || {}).filter(k => k !== 'year' && k !== 'trajectory').map((k, i) => ({
                                        dataKey: k,
                                        name: k,
                                        color: `hsl(${i * 137.5 % 360}, 70%, 60%)`
                                    }))
                                    :
                                    [
                                        { dataKey: 'emissions', name: 'Total Emissions', color: '#ff6600' },
                                        { dataKey: 'scope1', name: 'Scope 1', color: '#3b82f6' },
                                        { dataKey: 'trajectory', name: 'Target Path', color: '#10b981', strokeDasharray: '5 5' },
                                        { dataKey: 'forecast', name: 'Forecast', color: '#8b5cf6', strokeDasharray: '3 3' }
                                    ]
                                }
                                height={600}
                            />
                        </div>
                    </div>

                    {/* Donut Charts - Side by Side */}
                    <div className="donuts-row">
                        <div className="card donut-card-enhanced">
                            <div className="donut-header">
                                <h3 className="donut-title activity">Emissions by Activity</h3>
                            </div>
                            <div className="chart-container" style={{ height: '300px', width: '100%', minWidth: 0, position: 'relative' }}>
                                <PieChartWrapper data={activityChartData} height={300} innerRadius={80} outerRadius={110} />
                            </div>
                        </div>
                        <div className="card donut-card-enhanced">
                            <div className="donut-header">
                                <h3 className="donut-title source">Emissions by Source</h3>
                            </div>
                            <div className="chart-container" style={{ height: '300px', width: '100%', minWidth: 0, position: 'relative' }}>
                                <PieChartWrapper data={sourceChartData} height={300} innerRadius={80} outerRadius={110} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Categorical Breakdown Cards */}

                <div className={`card categorical-card ${categoricalCollapsed ? 'collapsed-card' : ''}`}>
                    <div 
                        className="card-header-row clickable-card-header"
                        onClick={() => setCategoricalCollapsed(!categoricalCollapsed)}
                        style={{ cursor: 'pointer', userSelect: 'none', marginBottom: categoricalCollapsed ? '0' : '24px' }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <h3 className="card-subtitle">Categorical Emissions Overview</h3>
                            <div className="card-info-badge">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                                </svg>
                                Activity → Division → Region
                            </div>
                        </div>
                        <div className="collapse-toggle-icon" style={{ display: 'flex', alignItems: 'center', color: '#64748b' }}>
                            {categoricalCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
                        </div>
                    </div>
                    <div className={`collapsible-body-wrapper ${categoricalCollapsed ? 'collapsed' : ''}`}>
                        <div className="categorical-hierarchy-grid">
                            {getActivityOptions().filter(o => o.value !== 'all').map(opt => (
                                <div key={opt.value} className="activity-group">
                                    <div className="activity-group-header">{opt.label}</div>
                                    {getHierarchicalData[opt.value] ? (
                                        Object.entries(getHierarchicalData[opt.value].divisions).map(([div, divData]) => (
                                            <div key={div} className="division-group">
                                                <div className="division-group-header">{div}</div>
                                                <div className="region-cards-grid">
                                                    {divData.regions.map((reg, ridx) => (
                                                        <div key={ridx} className="region-compact-card">
                                                            <div className="region-name">{reg.region} {reg.field && <span className="region-field">- {reg.field}</span>}</div>
                                                            <div className="region-value">{formatCompactNumber(reg.total_emissions)} <span className="unit">tCO₂e</span></div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="no-data-msg">No emissions data for this activity</div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="main-dashboard-grid">
                    <div className="detailed-breakdown-section">
                        <div className={`card detailed-table-card ${detailedBreakdownCollapsed ? 'collapsed-card' : ''}`}>
                            <div 
                                className="table-header-row clickable-card-header"
                                onClick={() => setDetailedBreakdownCollapsed(!detailedBreakdownCollapsed)}
                                style={{ cursor: 'pointer', userSelect: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                            >
                                <h3 className="card-title" style={{ margin: 0 }}>Detailed Breakdown</h3>
                                <div className="collapse-toggle-icon" style={{ display: 'flex', alignItems: 'center', color: '#64748b' }}>
                                    {detailedBreakdownCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
                                </div>
                            </div>
                            <div className={`collapsible-body-wrapper ${detailedBreakdownCollapsed ? 'collapsed' : ''}`}>
                                <div className="table-container" style={{ marginTop: '16px' }}>
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
                                                <td className="text-right font-bold">{formatCompactNumber(stats.scope1)}</td>
                                            </tr>
                                            <tr className="detail-row">
                                                <td className="indent">Stationary Combustion</td>
                                                <td className="text-right">{formatCompactNumber(stats.combustion)}</td>
                                            </tr>
                                            <tr className="detail-row">
                                                <td className="indent">Flaring</td>
                                                <td className="text-right">{formatCompactNumber(stats.flaring)}</td>
                                            </tr>
                                            <tr className="detail-row">
                                                <td className="indent">Venting</td>
                                                <td className="text-right">{formatCompactNumber(stats.venting)}</td>
                                            </tr>
                                            <tr className="detail-row">
                                                <td className="indent">Other Sources</td>
                                                <td className="text-right">{formatCompactNumber(stats.other)}</td>
                                            </tr>
                                            <tr className="summary-row">
                                                <td>Scope 2 (Indirect - Energy)</td>
                                                <td className="text-right font-bold">{formatCompactNumber(stats.scope2)}</td>
                                            </tr>
                                            <tr className="summary-row">
                                                <td>Scope 3 (Supply Chain)</td>
                                                <td className="text-right font-bold">{formatCompactNumber(stats.scope3)}</td>
                                            </tr>
                                            <tr className="total-row">
                                                <td>Total Footprint</td>
                                                <td className="text-right">{formatCompactNumber(stats.totalEmissions)}</td>
                                            </tr>
                                            <tr className="total-row" style={{ color: '#10b981', borderTop: 'none' }}>
                                                <td>Net Footprint</td>
                                                <td className="text-right">{formatCompactNumber(stats.netEmissions)}</td>
                                            </tr>

                                            <tr className="header-divider">
                                                <td colSpan="2">Organizational Breakdown</td>
                                            </tr>
                                            {Object.entries(getHierarchicalData).map(([act, actData]) => (
                                                <React.Fragment key={act}>
                                                    <tr className="act-row clickable" onClick={() => toggleActivity(act)}>
                                                        <td>
                                                            <span className="toggle-icon">{expandedActivities[act] ? '▼' : '▶'}</span>
                                                            {formatActivityName(act)}
                                                        </td>
                                                        <td className="text-right font-bold">{formatCompactNumber(actData.total)}</td>
                                                    </tr>
                                                    {expandedActivities[act] && Object.entries(actData.divisions).map(([div, divData]) => (
                                                        <React.Fragment key={div}>
                                                            <tr className="div-row clickable" onClick={(e) => { e.stopPropagation(); toggleDivision(div); }}>
                                                                <td className="indent">
                                                                    <span className="toggle-icon">{expandedDivisions[div] ? '▼' : '▶'}</span>
                                                                    {div}
                                                                </td>
                                                                <td className="text-right">{formatCompactNumber(divData.total)}</td>
                                                            </tr>
                                                            {expandedDivisions[div] && divData.regions.map((reg, ridx) => (
                                                                <tr key={ridx} className="reg-row">
                                                                    <td className="indent-double">{reg.region}</td>
                                                                    <td className="text-right">{formatCompactNumber(reg.total_emissions)}</td>
                                                                </tr>
                                                            ))}
                                                        </React.Fragment>
                                                    ))}
                                                </React.Fragment>
                                            ))}
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
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.3 }}>
                                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                                </svg>
                            </div>
                            <div className="library-list">
                                <div className="library-item">
                                    <div className="dot blue"></div>
                                    API Compendium: 2021
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="9 18 15 12 9 6" /></svg>
                                </div>
                                <div className="library-item">
                                    <div className="dot green"></div>
                                    ISO 14064-1:2018
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="9 18 15 12 9 6" /></svg>
                                </div>
                                <div className="library-item">
                                    <div className="dot orange"></div>
                                    GRI 305 Standards
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="9 18 15 12 9 6" /></svg>
                                </div>
                            </div>
                            <button className="manage-factors-btn" onClick={() => window.location.href = '/manage-data?tab=factors'}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                                Manage Custom Factors
                            </button>
                        </div>
                    </div>
                </div>
            </div>


        </div >
    );
};

export default DashboardEnhanced;
