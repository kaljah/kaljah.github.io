import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import { BarChart, LineChart } from '../components/charts';
import { useLayout } from '../context/LayoutContext';
import CustomDropdown from '../components/CustomDropdown';
import { formatNumber } from '../utils/formatters';
import { getActiveGwpFactors } from '../constants';
import { Cloud, Flame, Activity, BarChart2, Grid, Layers, ShieldCheck, FileText, ToggleLeft, ToggleRight, ArrowUpRight } from 'lucide-react';
import './CarbonIntensity.css';

const CarbonIntensity = () => {
    const { user } = useAuth();
    const toast = useToast();
    const { setTopBarLeft, setTopBarRight } = useLayout();

    // Filter states
    const [currentActivity, setCurrentActivity] = useState('all');
    const [currentDivision, setCurrentDivision] = useState('all');
    const [currentRegion, setCurrentRegion] = useState('all');
    const [selectedYear, setSelectedYear] = useState('all');
    const [facilities, setFacilities] = useState([]);
    const [availableYears, setAvailableYears] = useState([]);

    // GWP Horizon State: '100' or '20' & Active Standard
    const [gwpHorizon, setGwpHorizon] = useState('100');
    const [activeGwpStandard, setActiveGwpStandard] = useState('AR5');

    // View states
    const [trendView, setTrendView] = useState('chart'); // 'chart' or 'heatmap'

    // Data states
    const [stats, setStats] = useState({
        avgCo2Intensity: 0,
        avgCo2IntensityGwp20: 0,
        avgScope1Intensity: 0,
        avgScope2Intensity: 0,
        avgScope3Intensity: 0,
        avgFlaringIntensity: 0,
        totalCo2Emissions: 0,
        totalCo2EmissionsGwp20: 0,
        totalScope1: 0,
        totalScope2: 0,
        totalScope3: 0,
        totalFlaringEmissions: 0,
        totalOilProduction: 0,
        totalGasProduction: 0,
        totalBoe: 0,
        totalFlaringVolume: 0
    });

    const [regionalData, setRegionalData] = useState([]);
    const [rawTrendData, setRawTrendData] = useState([]);
    const [loading, setLoading] = useState(true);

    const GAS_TO_BOE = 0.178;

    const HIERARCHY = {
        'EP': ['Production', 'Association'],
        'LQS': ['LSH'],
        'RPC': ['Raffinage', 'Petrochimie'],
        'TRC': ['Make']
    };

    // Initial load
    useEffect(() => {
        const init = async () => {
            try {
                const [facRes, filterRes, settingsRes] = await Promise.all([
                    api.get('/facilities'),
                    api.get('/filters/available'),
                    api.get('/auth/settings').catch(() => ({ data: {} }))
                ]);
                setFacilities(facRes.data);

                if (settingsRes?.data?.gwp_standard) {
                    setActiveGwpStandard(settingsRes.data.gwp_standard);
                }

                if (filterRes.data && filterRes.data.years) {
                    setAvailableYears(filterRes.data.years);
                } else {
                    setAvailableYears(['2023', '2024', '2025', '2026']);
                }
                setSelectedYear('all');
            } catch (error) {
                console.error('Initialization error:', error);
            }
        };
        init();
    }, []);

    // Load data on filter changes
    useEffect(() => {
        loadIntensityData();
    }, [currentActivity, currentDivision, currentRegion, selectedYear]);

    // Load trend data
    useEffect(() => {
        if (selectedYear) {
            loadTrendData(selectedYear);
        }
    }, [selectedYear, currentActivity, currentDivision]);

    const loadIntensityData = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams({
                year: selectedYear,
                facilityId: currentRegion,
                activity: currentActivity,
                division: currentDivision
            });

            const res = await api.get(`/dashboard/intensity-stats?${params}`);
            const data = res.data || [];
            setRegionalData(data);

            let tOil = 0, tGas = 0, tBoe = 0, tFlaringVol = 0, tFlaringEm = 0;
            let wCo2Sum = 0, wCo2Gwp20Sum = 0, wS1Sum = 0, wS2Sum = 0, wS3Sum = 0;
            let tScope1 = 0, tScope2 = 0, tScope3 = 0;

            data.forEach(d => {
                const boe = d.total_boe || 0;
                tOil += d.total_oil || 0;
                tGas += d.total_gas || 0;
                tFlaringVol += d.flaring_volume || 0;
                tFlaringEm += d.flaring_emissions || 0;
                tScope1 += d.total_scope1 || 0;
                tScope2 += d.total_scope2 || 0;
                tScope3 += d.total_scope3 || 0;

                if (boe > 0) {
                    wCo2Sum += ((d.co2_intensity || 0) * boe);
                    wCo2Gwp20Sum += ((d.co2_intensity_gwp20 || d.co2_intensity || 0) * boe);
                    wS1Sum += ((d.scope1_intensity || 0) * boe);
                    wS2Sum += ((d.scope2_intensity || 0) * boe);
                    wS3Sum += ((d.scope3_intensity || 0) * boe);
                    tBoe += boe;
                }
            });

            setStats({
                avgCo2Intensity:      tBoe > 0 ? (wCo2Sum / tBoe) : 0,
                avgCo2IntensityGwp20:  tBoe > 0 ? (wCo2Gwp20Sum / tBoe) : 0,
                avgScope1Intensity:   tBoe > 0 ? (wS1Sum / tBoe) : 0,
                avgScope2Intensity:   tBoe > 0 ? (wS2Sum / tBoe) : 0,
                avgScope3Intensity:   tBoe > 0 ? (wS3Sum / tBoe) : 0,
                avgFlaringIntensity:  tBoe > 0 ? (tFlaringEm * 1000 / tBoe) : 0,
                totalCo2Emissions:    wCo2Sum / 1000,
                totalCo2EmissionsGwp20: wCo2Gwp20Sum / 1000,
                totalScope1:          tScope1,
                totalScope2:          tScope2,
                totalScope3:          tScope3,
                totalFlaringEmissions: tFlaringEm,
                totalOilProduction:   tOil,
                totalGasProduction:   tGas,
                totalBoe:             tBoe,
                totalFlaringVolume:   tFlaringVol
            });
        } catch (error) {
            console.error('Failed to load intensity stats:', error);
            toast.error('Failed to load carbon intensity metrics');
        } finally {
            setLoading(false);
        }
    };


    const loadTrendData = async (endYear) => {
        const years = [];
        const yearInt = isNaN(parseInt(endYear)) ? new Date().getFullYear() : parseInt(endYear);
        for (let i = 4; i >= 0; i--) years.push(yearInt - i);

        try {
            const params = new URLSearchParams({
                activity: currentActivity,
                division: currentDivision
            });
            params.append('years', years.join(','));
            const res = await api.get(`/dashboard/intensity-trend?${params}`).catch(() => ({ data: [] }));
            setRawTrendData(res.data || []);
        } catch (error) {
            console.error('Trend load error:', error);
        }
    };

    // Filter helpers
    const handleActivityChange = (val) => {
        setCurrentActivity(val);
        setCurrentDivision('all');
        setCurrentRegion('all');
    };

    const handleDivisionChange = (val) => {
        setCurrentDivision(val);
        setCurrentRegion('all');
    };

    const getActivityOptions = () => [
        { value: 'all', label: 'All Activities' },
        { value: 'EP', label: 'EP' },
        { value: 'LQS', label: 'LQS' },
        { value: 'RPC', label: 'RPC' },
        { value: 'TRC', label: 'TRC' }
    ];

    const getDivisionOptions = () => {
        let divisions = [{ value: 'all', label: 'All Divisions' }];
        if (currentActivity === 'all') {
            const allDivisions = new Set(facilities.map(f => f.division).filter(Boolean));
            divisions.push(...Array.from(allDivisions).sort().map(d => ({ value: d, label: d })));
        } else if (HIERARCHY[currentActivity]) {
            divisions.push(...HIERARCHY[currentActivity].map(d => ({ value: d, label: d })));
        }
        return divisions;
    };

    const getRegionOptions = () => {
        const filtered = facilities.filter(f =>
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

    // TopBar layout integration
    useEffect(() => {
        setTopBarLeft(
            <div className="dashboard-filters">
                <div style={{ width: '120px' }}>
                    <CustomDropdown
                        options={[
                            { value: 'all', label: 'All Years' },
                            ...availableYears.map(y => ({ value: y.toString(), label: y.toString() }))
                        ]}
                        value={selectedYear}
                        onChange={setSelectedYear}
                        placeholder="Year"
                    />
                </div>
                <div style={{ width: '160px' }}>
                    <CustomDropdown options={getActivityOptions()} value={currentActivity} onChange={handleActivityChange} placeholder="Activity" />
                </div>
                <div style={{ width: '160px' }}>
                    <CustomDropdown options={getDivisionOptions()} value={currentDivision} onChange={handleDivisionChange} placeholder="Division" disabled={currentActivity === 'all'} />
                </div>
                <div style={{ width: '220px' }}>
                    <CustomDropdown options={getRegionOptions()} value={currentRegion} onChange={setCurrentRegion} placeholder="Region" disabled={currentDivision === 'all'} />
                </div>
            </div>
        );

        return () => { setTopBarLeft(null); setTopBarRight(null); };
    }, [availableYears, selectedYear, currentActivity, currentDivision, currentRegion, facilities]);

    // Trend chart data based on active GWP toggle
    const trendChartData = useMemo(() => {
        return rawTrendData.map(item => {
            let yearData = item.data;
            if (currentRegion !== 'all') {
                yearData = yearData.filter(d => d.facility_id.toString() === currentRegion);
            }

            let wCo2 = 0, wCo2Gwp20 = 0, tBoe = 0;
            yearData.forEach(d => {
                const boe = d.total_boe || 0;
                if (boe > 0) {
                    wCo2 += ((d.co2_intensity || 0) * boe);
                    wCo2Gwp20 += ((d.co2_intensity_gwp20 || d.co2_intensity || 0) * boe);
                    tBoe += boe;
                }
            });

            return {
                year: item.year,
                co2_100: tBoe > 0 ? (wCo2 / tBoe) : 0,
                co2_20: tBoe > 0 ? (wCo2Gwp20 / tBoe) : 0,
                active_co2: tBoe > 0 ? (gwpHorizon === '20' ? (wCo2Gwp20 / tBoe) : (wCo2 / tBoe)) : 0
            };
        });
    }, [rawTrendData, currentRegion, gwpHorizon]);

    const getHeatmapClass = (val) => {
        if (val === null || val === 0) return 'heat-null';
        if (val < 18) return 'heat-lux';
        if (val < 28) return 'heat-low';
        if (val < 38) return 'heat-mid';
        if (val < 48) return 'heat-high';
        return 'heat-crit';
    };

    const currentDisplayCo2Intensity = gwpHorizon === '20' ? stats.avgCo2IntensityGwp20 : stats.avgCo2Intensity;
    const currentDisplayTotalCo2e = gwpHorizon === '20' ? stats.totalCo2EmissionsGwp20 : stats.totalCo2Emissions;

    if (loading && regionalData.length === 0) return <LoadingSpinner message="Calculating Carbon Intensity..." fullScreen />;

    return (
        <div className="intensity-content">
            <div className="intensity-grid">

                {/* KPI HERO CARD */}
                <div className="hero-card">
                    <div className="hero-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <h2 className="grid-title">
                                <Activity size={24} color="var(--accent-color)" />
                                Carbon Intensity & Product Embodiment
                            </h2>
                            <div className="year-badge">
                                {selectedYear} Performance
                            </div>
                        </div>

                        {/* GWP Time Horizon Toggle */}
                        <div className="gwp-toggle-container">
                            <span className="gwp-toggle-label">GWP Horizon:</span>
                            <div className="gwp-pill-group">
                                {(() => {
                                    const f100 = getActiveGwpFactors(activeGwpStandard, '100');
                                    const f20 = getActiveGwpFactors(activeGwpStandard, '20');
                                    return (
                                        <>
                                            <button
                                                className={`gwp-pill ${gwpHorizon === '100' ? 'active' : ''}`}
                                                onClick={() => setGwpHorizon('100')}
                                                title={`IPCC ${activeGwpStandard} 100-Year GWP (CH4: ${f100.CH4}, N2O: ${f100.N2O})`}
                                            >
                                                {activeGwpStandard} 100-Yr
                                            </button>
                                            <button
                                                className={`gwp-pill ${gwpHorizon === '20' ? 'active' : ''}`}
                                                onClick={() => setGwpHorizon('20')}
                                                title={`IPCC ${activeGwpStandard} 20-Year GWP (CH4: ${f20.CH4}, N2O: ${f20.N2O})`}
                                            >
                                                {activeGwpStandard} 20-Yr
                                            </button>
                                        </>
                                    );
                                })()}
                            </div>
                        </div>
                    </div>

                    {/* Horizontal 4-KPI Grid */}
                    <div className="kpi-grid-4">
                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon co2"><Cloud size={20} /></div>
                                <span className="kpi-label">GHG Intensity (Avg)</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value co2">{(currentDisplayCo2Intensity ?? 0).toFixed(2)}</span>
                                <span className="kpi-unit">kg CO₂e / BOE</span>
                            </div>
                            <div className="kpi-footer">
                                <span className="gwp-subtag">{gwpHorizon === '20' ? 'GWP₂₀ Active' : 'GWP₁₀₀ Standard'}</span>
                                <span>Total: <strong>{formatNumber(currentDisplayTotalCo2e)} tCO₂e</strong></span>
                            </div>
                        </div>

                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon scope1"><Layers size={20} /></div>
                                <span className="kpi-label">Scope 1 Direct Intensity</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value scope1">{(stats.avgScope1Intensity ?? 0).toFixed(2)}</span>
                                <span className="kpi-unit">kg CO₂e / BOE</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Scope 2: <strong>{(stats.avgScope2Intensity ?? 0).toFixed(2)} kg/BOE</strong></span>
                                <span>Total S1: <strong>{formatNumber(stats.totalScope1)} t</strong></span>
                            </div>
                        </div>

                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon flare"><Flame size={20} /></div>
                                <span className="kpi-label">Flaring Carbon Intensity</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value flare">{(stats.avgFlaringIntensity ?? 0).toFixed(2)}</span>
                                <span className="kpi-unit">kg CO₂e / BOE</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Flared: <strong>{formatNumber(stats.totalFlaringEmissions)} tCO₂e</strong></span>
                            </div>
                        </div>

                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon scope3"><ShieldCheck size={20} /></div>
                                <span className="kpi-label">Scope 3 Value Chain</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value scope3">{(stats.avgScope3Intensity ?? 0).toFixed(2)}</span>
                                <span className="kpi-unit">kg CO₂e / BOE</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Total S3: <strong>{formatNumber(stats.totalScope3)} tCO₂e</strong></span>
                            </div>
                        </div>
                    </div>

                    {/* Production Context Bar */}
                    <div className="scope-breakdown">
                        <div className="scope-item">
                            <span className="label">Total Oil Production</span>
                            <span className="val">{formatNumber(stats.totalOilProduction, 0)} bbl</span>
                        </div>
                        <div className="scope-item bordered">
                            <span className="label">Total Gas Production</span>
                            <span className="val">{formatNumber(stats.totalGasProduction, 0)} mscf</span>
                        </div>
                        <div className="scope-item bordered">
                            <span className="label">Combined Production (BOE)</span>
                            <span className="val" style={{ color: 'var(--accent-color)', fontWeight: 700 }}>
                                {formatNumber(stats.totalBoe, 0)} BOE
                            </span>
                        </div>
                        <div className="scope-item bordered">
                            <span className="label">Total Gas Flared</span>
                            <span className="val flare-val">{formatNumber(stats.totalFlaringVolume, 0)} m³</span>
                        </div>
                    </div>
                </div>


                {/* Regional Bar Charts */}
                <div className="chart-grid">
                    <div className="card">
                        <div className="chart-header">
                            <div className="chart-title-wrapper">
                                <h3>GHG Intensity by Facility (kg CO₂e / BOE)</h3>
                                <div className="chart-indicator" style={{ background: '#0d9488' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: gwpHorizon === '20' ? (d.co2_intensity_gwp20 || d.co2_intensity) : d.co2_intensity
                                }))}
                                dataKey="value"
                                xKey="name"
                                color="#0d9488"
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="chart-header">
                            <div className="chart-title-wrapper">
                                <h3>Scope 1 Direct vs Scope 2 Intensity</h3>
                                <div className="chart-indicator" style={{ background: '#2563eb' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: d.scope1_intensity || 0
                                }))}
                                dataKey="value"
                                xKey="name"
                                color="#2563eb"
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="chart-header">
                            <div className="chart-title-wrapper">
                                <h3>Oil BOE Contribution by Facility</h3>
                                <div className="chart-indicator" style={{ background: '#ea580c' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: d.total_oil || 0
                                }))}
                                dataKey="value"
                                xKey="name"
                                color="#ea580c"
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="chart-header">
                            <div className="chart-title-wrapper">
                                <h3>Gas BOE Contribution by Facility</h3>
                                <div className="chart-indicator" style={{ background: '#8b5cf6' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: (d.total_gas || 0) * GAS_TO_BOE
                                }))}
                                dataKey="value"
                                xKey="name"
                                color="#8b5cf6"
                            />
                        </div>
                    </div>
                </div>

                {/* Historical Trends Section */}
                <div className="card trend-section">
                    <div className="chart-header">
                        <div>
                            <h3 style={{ marginBottom: '4px' }}>Historical Carbon Intensity Trends</h3>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>5-Year Performance Track (kg CO₂e / BOE)</p>
                        </div>
                        <div className="trend-view-controls">
                            <div className="view-toggle">
                                <button className={`view-btn ${trendView === 'chart' ? 'active' : ''}`} onClick={() => setTrendView('chart')}>
                                    <BarChart2 size={16} /> Chart
                                </button>
                                <button className={`view-btn ${trendView === 'heatmap' ? 'active' : ''}`} onClick={() => setTrendView('heatmap')}>
                                    <Grid size={16} /> Heatmap
                                </button>
                            </div>
                        </div>
                    </div>

                    {trendView === 'chart' ? (
                        <div style={{ height: '350px' }}>
                            <LineChart
                                data={trendChartData}
                                xKey="year"
                                series={[
                                    { key: 'co2_100', color: '#0d9488', name: 'GHG Intensity (AR5 100-Yr GWP)' },
                                    { key: 'co2_20', color: '#ea580c', name: 'GHG Intensity (AR5 20-Yr GWP)', dash: '5 5' }
                                ]}
                            />
                        </div>
                    ) : (
                        <div className="heatmap-container">
                            <div className="heatmap-header">
                                <div className="heatmap-header-cell" style={{ textAlign: 'left' }}>FACILITY / REGION</div>
                                {rawTrendData.map(d => <div key={d.year} className="heatmap-header-cell">{d.year}</div>)}
                            </div>
                            <div className="heatmap-body">
                                {regionalData.length > 0 ? (
                                    regionalData.map(facData => (
                                        <div key={facData.facility_id} className="heatmap-row">
                                            <div className="heatmap-label">
                                                {facData.facility_name}
                                            </div>
                                            {rawTrendData.map(yData => {
                                                const record = yData.data.find(r => r.facility_id === facData.facility_id);
                                                const val = record ? (gwpHorizon === '20' ? (record.co2_intensity_gwp20 || record.co2_intensity) : record.co2_intensity) : 0;
                                                return (
                                                    <div
                                                        key={yData.year}
                                                        className={`heatmap-cell ${getHeatmapClass(val)}`}
                                                        title={`${yData.year} Intensity: ${val.toFixed(3)} kg CO2e/BOE`}
                                                    >
                                                        {val > 0 ? val.toFixed(2) : '-'}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    ))
                                ) : (
                                    <p style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>No regional data available</p>
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
