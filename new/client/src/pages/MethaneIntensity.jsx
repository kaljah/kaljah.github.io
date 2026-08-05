import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import { BarChart, LineChart } from '../components/charts';
import { useLayout } from '../context/LayoutContext';
import CustomDropdown from '../components/CustomDropdown';
import { formatNumber } from '../utils/formatters';
import { Wind, Flame, Activity, BarChart2, Grid, Layers, ShieldCheck, AlertTriangle, CheckCircle, Compass, Radio } from 'lucide-react';
import './CarbonIntensity.css';

const MethaneIntensity = () => {
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

    // View states
    const [trendView, setTrendView] = useState('chart'); // 'chart' or 'heatmap'

    // Data states
    const [stats, setStats] = useState({
        avgCh4Intensity: 0,
        avgMethaneLossRatePct: 0,
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
        ogmpGoldStatus: 'Compliant'
    });

    const [regionalData, setRegionalData] = useState([]);
    const [ogmpSurveys, setOgmpSurveys] = useState([]);
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
                const [facRes, filterRes] = await Promise.all([
                    api.get('/facilities'),
                    api.get('/filters/available')
                ]);
                setFacilities(facRes.data);

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
        loadMethaneData();
        loadOgmpData();
    }, [currentActivity, currentDivision, currentRegion, selectedYear]);

    // Load trend data
    useEffect(() => {
        if (selectedYear) {
            loadTrendData(selectedYear);
        }
    }, [selectedYear, currentActivity, currentDivision]);

    const loadMethaneData = async () => {
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

            let tOil = 0, tGasMscf = 0, tGasM3 = 0, tBoe = 0, tFlaringVol = 0, tFlaringEm = 0;
            let wCh4Sum = 0, tCh4Tonnes = 0, tWecFee = 0;

            data.forEach(d => {
                const boe = d.total_boe || 0;
                tOil += d.total_oil || 0;
                tGasMscf += d.total_gas || 0;
                tGasM3 += d.total_gas_m3 || ((d.total_gas || 0) * 28.3168);
                tFlaringVol += d.flaring_volume || 0;
                tFlaringEm += d.flaring_emissions || 0;
                tCh4Tonnes += d.total_ch4 || 0;
                tWecFee += d.wec_fee_usd || 0;

                if (boe > 0) {
                    wCh4Sum += ((d.ch4_intensity || 0) * boe);
                    tBoe += boe;
                }
            });

            // Methane density at standard conditions = 0.6785 kg/m3
            const totalCh4VolM3 = (tCh4Tonnes * 1000.0) / 0.6785;
            const avgLossRatePct = tGasM3 > 0 ? (totalCh4VolM3 / tGasM3 * 100.0) : 0.0;
            const avgFlaringRatePct = tGasM3 > 0 ? (tFlaringVol / tGasM3 * 100.0) : 0.0;

            let goldStatus = 'Compliant';
            if (avgLossRatePct > 0.25) goldStatus = 'Non-Compliant';
            else if (avgLossRatePct > 0.20) goldStatus = 'Warning';

            setStats({
                avgCh4Intensity:        tBoe > 0 ? (wCh4Sum / tBoe) : 0,
                avgMethaneLossRatePct:  avgLossRatePct,
                avgFlaringRatePct:      avgFlaringRatePct,
                totalCh4Emissions:      tCh4Tonnes,
                totalCh4VolumeM3:       totalCh4VolM3,
                totalGasProductionM3:   tGasM3,
                totalGasProductionMscf: tGasMscf,
                totalOilProduction:     tOil,
                totalBoe:               tBoe,
                totalFlaringVolume:     tFlaringVol,
                totalFlaringEmissions:  tFlaringEm,
                totalWecFeeUsd:         tWecFee,
                ogmpGoldStatus:         goldStatus
            });
        } catch (error) {
            console.error('Failed to load methane stats:', error);
            toast.error('Failed to load methane intensity metrics');
        } finally {
            setLoading(false);
        }
    };

    const loadOgmpData = async () => {
        try {
            const params = new URLSearchParams();
            if (selectedYear && selectedYear !== 'all') params.append('year', selectedYear);
            if (currentRegion && currentRegion !== 'all') params.append('facilityId', currentRegion);
            const res = await api.get(`/data/ogmp-surveys?${params}`).catch(() => ({ data: [] }));
            setOgmpSurveys(res.data || []);
        } catch (error) {
            console.error('OGMP load error:', error);
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

    // Trend chart data
    const trendChartData = useMemo(() => {
        return rawTrendData.map(item => {
            let yearData = item.data;
            if (currentRegion !== 'all') {
                yearData = yearData.filter(d => d.facility_id.toString() === currentRegion);
            }

            let wCh4 = 0, tBoe = 0, tGasM3 = 0, tCh4VolM3 = 0;
            yearData.forEach(d => {
                const boe = d.total_boe || 0;
                const gasM3 = d.total_gas_m3 || ((d.total_gas || 0) * 28.3168);
                const ch4Tonnes = d.total_ch4 || 0;
                tGasM3 += gasM3;
                tCh4VolM3 += (ch4Tonnes * 1000.0) / 0.6785;

                if (boe > 0) {
                    wCh4 += ((d.ch4_intensity || 0) * boe);
                    tBoe += boe;
                }
            });

            const lossRate = tGasM3 > 0 ? (tCh4VolM3 / tGasM3 * 100.0) : 0.0;

            return {
                year: item.year,
                ch4_intensity: tBoe > 0 ? (wCh4 / tBoe) : 0,
                loss_rate_pct: lossRate,
                target_020: 0.20
            };
        });
    }, [rawTrendData, currentRegion]);

    const getHeatmapClass = (val) => {
        if (val === null || val === 0) return 'heat-null';
        if (val < 0.05) return 'heat-lux';
        if (val < 0.15) return 'heat-low';
        if (val < 0.25) return 'heat-mid';
        if (val < 0.50) return 'heat-high';
        return 'heat-crit';
    };

    if (loading && regionalData.length === 0) return <LoadingSpinner message="Calculating Methane Intensity & Loss Rates..." fullScreen />;

    return (
        <div className="intensity-content">
            <div className="intensity-grid">

                {/* KPI HERO CARD */}
                <div className="hero-card">
                    <div className="hero-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <h2 className="grid-title">
                                <Wind size={24} color="var(--accent-secondary)" />
                                Methane Intensity & Loss Rate Analytics
                            </h2>
                            <div className="year-badge" style={{ background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb', borderColor: 'rgba(37, 99, 235, 0.2)' }}>
                                {selectedYear} Performance
                            </div>
                        </div>

                        {/* OGMP 2.0 Gold Standard Badge */}
                        <div className="ogmp-gold-badge" style={{
                            display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '8px',
                            background: stats.ogmpGoldStatus === 'Compliant' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            border: `1px solid ${stats.ogmpGoldStatus === 'Compliant' ? '#10b981' : '#ef4444'}`,
                            color: stats.ogmpGoldStatus === 'Compliant' ? '#10b981' : '#ef4444',
                            fontWeight: 600, fontSize: '0.85rem'
                        }}>
                            {stats.ogmpGoldStatus === 'Compliant' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                            <span>OGMP 2.0 Gold Standard: {stats.ogmpGoldStatus} (&le;0.20%)</span>
                        </div>
                    </div>

                    {/* Horizontal 4-KPI Grid */}
                    <div className="kpi-grid-4">
                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon ch4"><Wind size={20} /></div>
                                <span className="kpi-label">Methane Intensity (Avg)</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value ch4">{(stats.avgCh4Intensity ?? 0).toFixed(4)}</span>
                                <span className="kpi-unit">kg CH₄ / BOE</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Total CH₄: <strong>{formatNumber(stats.totalCh4Emissions)} tCH₄</strong></span>
                            </div>
                        </div>

                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon loss" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}><Compass size={20} /></div>
                                <span className="kpi-label">Methane Loss Rate</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value" style={{ color: stats.avgMethaneLossRatePct <= 0.20 ? '#10b981' : (stats.avgMethaneLossRatePct <= 0.25 ? '#f59e0b' : '#ef4444') }}>
                                    {(stats.avgMethaneLossRatePct ?? 0).toFixed(3)}%
                                </span>
                                <span className="kpi-unit">of Gas Volume</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Target: <strong>&le; 0.200% (OGMP)</strong></span>
                                <span>Vol: <strong>{formatNumber(stats.totalCh4VolumeM3, 0)} m³</strong></span>
                            </div>
                        </div>

                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon flare"><Flame size={20} /></div>
                                <span className="kpi-label">Gas Flaring Rate</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value flare">{(stats.avgFlaringRatePct ?? 0).toFixed(3)}%</span>
                                <span className="kpi-unit">of Gas Volume</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Flared: <strong>{formatNumber(stats.totalFlaringVolume, 0)} m³</strong></span>
                            </div>
                        </div>

                        <div className="kpi-card">
                            <div className="kpi-header">
                                <div className="kpi-icon wec" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}><AlertTriangle size={20} /></div>
                                <span className="kpi-label">EPA WEC Liability</span>
                            </div>
                            <div className="kpi-value-container">
                                <span className="total-value" style={{ color: stats.totalWecFeeUsd > 0 ? '#ef4444' : '#10b981' }}>
                                    ${formatNumber(stats.totalWecFeeUsd, 0)}
                                </span>
                                <span className="kpi-unit">USD Est.</span>
                            </div>
                            <div className="kpi-footer">
                                <span>Waste Emissions Charge ($900/t)</span>
                            </div>
                        </div>
                    </div>

                    {/* Methane Mass Balance Bar */}
                    <div className="scope-breakdown">
                        <div className="scope-item">
                            <span className="label">Total Gas Produced</span>
                            <span className="val">{formatNumber(stats.totalGasProductionM3, 0)} m³ <sub style={{ fontSize: '0.7em', color: 'var(--text-secondary)' }}>({formatNumber(stats.totalGasProductionMscf, 0)} mscf)</sub></span>
                        </div>
                        <div className="scope-item bordered">
                            <span className="label">Methane Loss Volume</span>
                            <span className="val" style={{ color: '#2563eb', fontWeight: 700 }}>
                                {formatNumber(stats.totalCh4VolumeM3, 0)} m³
                            </span>
                        </div>
                        <div className="scope-item bordered">
                            <span className="label">Total Gas Flared</span>
                            <span className="val flare-val">{formatNumber(stats.totalFlaringVolume, 0)} m³</span>
                        </div>
                        <div className="scope-item bordered">
                            <span className="label">Total Combined BOE</span>
                            <span className="val">{formatNumber(stats.totalBoe, 0)} BOE</span>
                        </div>
                    </div>
                </div>

                {/* OGMP 2.0 LEVEL 4/5 TOP-DOWN SURVEY RECONCILIATION SECTION */}
                <div className="card ogmp-section">
                    <div className="chart-header">
                        <div>
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Radio size={20} color="var(--accent-secondary)" />
                                OGMP 2.0 Level 4/5 Top-Down Survey & Bottom-Up Reconciliation
                            </h3>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: '4px 0 0 0' }}>
                                Site-level measurement (Satellite, OGI, Drone, Aircraft) reconciled with source-level inventory
                            </p>
                        </div>
                        <div className="ogmp-level-badge" style={{ background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb', padding: '6px 14px', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 600 }}>
                            Gold Standard Pathway: Level 5 Reconciled
                        </div>
                    </div>

                    {ogmpSurveys.length > 0 ? (
                        <div className="table-responsive" style={{ marginTop: '16px' }}>
                            <table className="custom-table">
                                <thead>
                                    <tr>
                                        <th>Facility</th>
                                        <th>Survey Date</th>
                                        <th>Technology / Method</th>
                                        <th>Measured Rate (kg CH₄/hr)</th>
                                        <th>Annualized Rate (tCH₄/yr)</th>
                                        <th>Bottom-Up Annual (tCH₄)</th>
                                        <th>Reconciliation Status</th>
                                        <th>Operator Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {ogmpSurveys.map((s, idx) => {
                                        const fid = s.facilityId ?? s.facility_id;
                                        const matchingFac = regionalData.find(f => f.facility_id === fid);
                                        const bottomUpCh4 = matchingFac ? matchingFac.total_ch4 : null;
                                        const facName = s.facilityName || s.facility_name || (matchingFac ? matchingFac.facility_name : '—');
                                        const sDate = s.surveyDate || s.survey_date || '—';
                                        const sType = s.surveyType || s.survey_type || 'Top-Down';
                                        const rateKgHr = s.measuredRateKgHr ?? s.measured_rate_kg_hr;
                                        const annTch4 = s.estimatedAnnualTch4 ?? s.estimated_annual_tch4 ?? 0;
                                        const recStatus = s.reconciliationStatus || s.reconciliation_status || 'Reconciled';
                                        const notes = s.operatorNotes || s.operator_notes || '—';
                                        return (
                                            <tr key={s.id || idx}>
                                                <td style={{ fontWeight: 600 }}>{facName}</td>
                                                <td>{sDate}</td>
                                                <td><span className="code-pill">{sType}</span></td>
                                                <td><strong style={{ color: '#2563eb' }}>{typeof rateKgHr === 'number' ? rateKgHr.toFixed(2) : '—'}</strong></td>
                                                <td><strong>{formatNumber(annTch4, 2)}</strong></td>
                                                <td>{bottomUpCh4 !== null ? `${bottomUpCh4.toFixed(2)} t` : '—'}</td>
                                                <td>
                                                    <span className={`status-badge ${recStatus === 'Reconciled' ? 'badge-success' : 'badge-warning'}`} style={{
                                                        padding: '4px 10px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 600,
                                                        background: recStatus === 'Reconciled' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                                                        color: recStatus === 'Reconciled' ? '#10b981' : '#f59e0b'
                                                    }}>
                                                        {recStatus}
                                                    </span>
                                                </td>
                                                <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{notes}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="cbam-empty-state">
                            <p>No OGMP 2.0 top-down surveys registered for the selected filters. Record survey campaigns via <strong>Manage Data &gt; OGMP Surveys</strong>.</p>
                        </div>
                    )}
                </div>

                {/* Regional Bar Charts */}
                <div className="chart-grid">
                    <div className="card">
                        <div className="chart-header">
                            <div className="chart-title-wrapper">
                                <h3>Methane Loss Rate by Facility (% of Gas Produced)</h3>
                                <div className="chart-indicator" style={{ background: '#2563eb' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: d.methane_loss_rate_pct || 0
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
                                <h3>Methane Intensity by Facility (kg CH₄ / BOE)</h3>
                                <div className="chart-indicator" style={{ background: '#0d9488' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: d.ch4_intensity || 0
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
                                <h3>Total Methane Emissions (tCH₄)</h3>
                                <div className="chart-indicator" style={{ background: '#3b82f6' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: d.total_ch4 || 0
                                }))}
                                dataKey="value"
                                xKey="name"
                                color="#3b82f6"
                            />
                        </div>
                    </div>

                    <div className="card">
                        <div className="chart-header">
                            <div className="chart-title-wrapper">
                                <h3>Gas Flaring Volume by Facility (m³)</h3>
                                <div className="chart-indicator" style={{ background: '#ea580c' }}></div>
                            </div>
                        </div>
                        <div style={{ height: '300px' }}>
                            <BarChart
                                data={regionalData.map(d => ({
                                    name: d.facility_name,
                                    value: d.flaring_volume || 0
                                }))}
                                dataKey="value"
                                xKey="name"
                                color="#ea580c"
                            />
                        </div>
                    </div>
                </div>

                {/* Historical Trends Section */}
                <div className="card trend-section">
                    <div className="chart-header">
                        <div>
                            <h3 style={{ marginBottom: '4px' }}>Historical Methane Trends & Targets</h3>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>5-Year Methane Loss Rate (%) vs OGMP 2.0 Target (0.20%)</p>
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
                                    { key: 'loss_rate_pct', color: '#2563eb', name: 'Methane Loss Rate (%)' },
                                    { key: 'target_020', color: '#10b981', name: 'OGMP Gold Target (0.20%)', dash: '4 4' }
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
                                                const val = record ? (record.methane_loss_rate_pct || 0) : 0;
                                                return (
                                                    <div
                                                        key={yData.year}
                                                        className={`heatmap-cell ${getHeatmapClass(val)}`}
                                                        title={`${yData.year} Loss Rate: ${val.toFixed(3)}%`}
                                                    >
                                                        {val > 0 ? `${val.toFixed(3)}%` : '-'}
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

export default MethaneIntensity;
