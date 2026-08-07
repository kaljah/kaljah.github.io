import React, { useState, useEffect } from 'react';
import { 
    Globe, 
    Target, 
    Building2, 
    SlidersHorizontal, 
    Save, 
    CheckCircle2, 
    Scale, 
    ShieldCheck, 
    Activity, 
    Layers
} from 'lucide-react';
import api from '../api';
import { useToast } from '../components/Toast';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/LoadingSpinner';
import './Settings.css';

const GWP_DATA = {
    AR5: {
        name: 'IPCC 5th Assessment Report (AR5)',
        year: '2014',
        status: 'UNFCCC / EU Standard (Default)',
        ch4_100: 28.0,
        ch4_20: 82.5,
        n2o_100: 265.0,
        co2: 1.0,
        description: 'Standard baseline used by OGMP 2.0, UNFCCC National Inventories, and corporate GHG reporting frameworks.'
    },
    AR6: {
        name: 'IPCC 6th Assessment Report (AR6)',
        year: '2021',
        status: 'Latest IPCC Physical Science Basis',
        ch4_100: 27.9,
        ch4_20: 82.5,
        n2o_100: 273.0,
        co2: 1.0,
        description: 'Most recent scientific consensus incorporating updated radiative efficiency and tropospheric adjustments.'
    },
    AR4: {
        name: 'IPCC 4th Assessment Report (AR4)',
        year: '2007',
        status: 'Legacy Regulatory Frameworks',
        ch4_100: 25.0,
        ch4_20: 72.0,
        n2o_100: 298.0,
        co2: 1.0,
        description: 'Historical standard preserved for legacy compliance agreements and multi-decade baseline tracking.'
    }
};

const Settings = () => {
    const toast = useToast();
    const { user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [facilities, setFacilities] = useState([]);
    const [activeTab, setActiveTab] = useState('gwp');

    // Settings state
    const [gwpStandard, setGwpStandard] = useState('AR5');
    const [defaultBaseYear, setDefaultBaseYear] = useState(2023);
    const [globalThreshold, setGlobalThreshold] = useState(20.0);
    const [upstreamTarget, setUpstreamTarget] = useState(0.20);
    const [midstreamTarget, setMidstreamTarget] = useState(0.05);
    const [theme, setTheme] = useState(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
    const [unitSystem, setUnitSystem] = useState('metric');
    const [autoFlagDiscrepancy, setAutoFlagDiscrepancy] = useState(true);

    // Facility specific overrides
    const [facilityEdits, setFacilityEdits] = useState({});

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const [settingsRes, facRes] = await Promise.all([
                api.get('/auth/settings').catch(() => ({ data: {} })),
                api.get('/facilities').catch(() => ({ data: [] }))
            ]);

            const settings = settingsRes.data;
            if (settings) {
                if (settings.gwp_standard) setGwpStandard(settings.gwp_standard);
                if (settings.ogmp_default_base_year) setDefaultBaseYear(settings.ogmp_default_base_year);
                if (settings.reconciliation_threshold) setGlobalThreshold(settings.reconciliation_threshold);
                if (settings.ogmp_upstream_target_pct !== undefined) setUpstreamTarget(Number(settings.ogmp_upstream_target_pct));
                if (settings.ogmp_midstream_target_pct !== undefined) setMidstreamTarget(Number(settings.ogmp_midstream_target_pct));
                if (settings.theme) {
                    setTheme(settings.theme);
                    applyThemeLive(settings.theme);
                }
                if (settings.unit_system) setUnitSystem(settings.unit_system);
                if (settings.auto_flag_discrepancy !== undefined) setAutoFlagDiscrepancy(settings.auto_flag_discrepancy);
            }

            const facList = facRes.data;
            if (facList && Array.isArray(facList)) {
                setFacilities(facList);
                const initialMap = {};
                facList.forEach(f => {
                    initialMap[f.id] = {
                        operator_status: f.operator_status || 'operated',
                        country: f.country || 'Algeria',
                        ogmp_membership_year: f.ogmp_membership_year || 2023,
                        reconciliation_threshold: f.reconciliation_threshold || 20.0
                    };
                });
                setFacilityEdits(initialMap);
            }
        } catch (err) {
            console.error('Failed to load settings:', err);
            toast.error('Failed to load settings');
        } finally {
            setLoading(false);
        }
    };

    const applyThemeLive = (newTheme) => {
        if (newTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    };

    const handleThemeChange = (newTheme) => {
        setTheme(newTheme);
        applyThemeLive(newTheme);
    };

    const handleSaveGlobal = async () => {
        try {
            setSaving(true);
            await api.post('/auth/settings', {
                gwp_standard: gwpStandard,
                ogmp_default_base_year: Number(defaultBaseYear),
                reconciliation_threshold: Number(globalThreshold),
                ogmp_upstream_target_pct: Number(upstreamTarget),
                ogmp_midstream_target_pct: Number(midstreamTarget),
                theme,
                unit_system: unitSystem,
                auto_flag_discrepancy: autoFlagDiscrepancy
            });
            applyThemeLive(theme);
            toast.success('System settings and GWP standards updated successfully!');
        } catch (err) {
            console.error('Save failed:', err);
            toast.error('Error saving settings');
        } finally {
            setSaving(false);
        }
    };

    const handleFacilityChange = (facId, field, value) => {
        setFacilityEdits(prev => ({
            ...prev,
            [facId]: {
                ...prev[facId],
                [field]: value
            }
        }));
    };

    const handleSaveFacility = async (facId) => {
        try {
            const data = facilityEdits[facId];
            await api.put(`/facilities/${facId}`, {
                operator_status: data.operator_status,
                country: data.country,
                ogmp_membership_year: Number(data.ogmp_membership_year),
                reconciliation_threshold: Number(data.reconciliation_threshold)
            });
            toast.success('Facility OGMP settings updated!');
        } catch (err) {
            console.error('Facility save failed:', err);
            toast.error('Failed to update facility');
        }
    };

    if (loading) {
        return (
            <div className="settings-loading-container">
                <LoadingSpinner message="Loading Standards & System Preferences..." />
            </div>
        );
    }

    const currentGwp = GWP_DATA[gwpStandard] || GWP_DATA.AR5;

    return (
        <div className="settings-page-wrapper">
            {/* Header */}
            <div className="settings-hero-card">
                <div className="settings-header-content">
                    <div className="settings-header-left">
                        <div className="settings-badge">
                            <SlidersHorizontal size={14} />
                            <span>STANDARDS & METHODOLOGIES</span>
                        </div>
                        <h1 className="settings-title">System Settings & Protocols</h1>
                        <p className="settings-subtitle">
                            Configure IPCC Global Warming Potential (GWP) conversion factors, OGMP 2.0 Gold Standard compliance parameters, and facility-specific reconciliation tolerances.
                        </p>
                    </div>
                    <div className="settings-header-right">
                        <button 
                            className="btn-save-primary" 
                            onClick={handleSaveGlobal} 
                            disabled={saving}
                            id="save-settings-btn"
                        >
                            {saving ? (
                                <>
                                    <span className="spinner-small"></span>
                                    <span>Saving...</span>
                                </>
                            ) : (
                                <>
                                    <Save size={16} />
                                    <span>Save All Changes</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Navigation Tabs Bar */}
                <div className="settings-tabs-bar">
                    <button 
                        className={`settings-tab-btn ${activeTab === 'gwp' ? 'active' : ''}`}
                        onClick={() => setActiveTab('gwp')}
                        id="tab-gwp"
                    >
                        <Globe size={17} className="tab-icon-svg" />
                        <span>IPCC GWP Standards</span>
                    </button>
                    <button 
                        className={`settings-tab-btn ${activeTab === 'ogmp' ? 'active' : ''}`}
                        onClick={() => setActiveTab('ogmp')}
                        id="tab-ogmp"
                    >
                        <Target size={17} className="tab-icon-svg" />
                        <span>OGMP 2.0 Baseline & Thresholds</span>
                    </button>
                    <button 
                        className={`settings-tab-btn ${activeTab === 'facilities' ? 'active' : ''}`}
                        onClick={() => setActiveTab('facilities')}
                        id="tab-facilities"
                    >
                        <Building2 size={17} className="tab-icon-svg" />
                        <span>Facility Overrides ({facilities.length})</span>
                    </button>
                </div>
            </div>

            {/* TAB CONTENT: GWP Standards */}
            {activeTab === 'gwp' && (
                <div className="settings-section-card">
                    <div className="section-intro">
                        <div className="section-intro-header">
                            <Scale size={20} className="section-icon" />
                            <h2>IPCC Global Warming Potential (GWP) Standard</h2>
                        </div>
                        <p>Select which Intergovernmental Panel on Climate Change (IPCC) assessment report conversion factors are applied to Methane (CH₄) and Nitrous Oxide (N₂O) emissions calculations.</p>
                    </div>

                    <div className="gwp-cards-grid">
                        {Object.entries(GWP_DATA).map(([key, data]) => {
                            const isSelected = gwpStandard === key;
                            return (
                                <div 
                                    key={key} 
                                    className={`gwp-card ${isSelected ? 'selected' : ''}`}
                                    onClick={() => setGwpStandard(key)}
                                    id={`gwp-card-${key.toLowerCase()}`}
                                >
                                    <div className="gwp-card-header">
                                        <div className="gwp-version-badge">{key}</div>
                                        {isSelected && (
                                            <div className="gwp-active-indicator">
                                                <CheckCircle2 size={13} />
                                                <span>ACTIVE STANDARD</span>
                                            </div>
                                        )}
                                    </div>
                                    <h3 className="gwp-title">{data.name}</h3>
                                    <div className="gwp-status-pill">{data.status}</div>
                                    <p className="gwp-desc">{data.description}</p>

                                    <div className="gwp-factors-box">
                                        <div className="factor-item">
                                            <span className="factor-label">CH₄ (100-yr)</span>
                                            <span className="factor-val">{data.ch4_100}×</span>
                                        </div>
                                        <div className="factor-item highlight">
                                            <span className="factor-label">CH₄ (20-yr)</span>
                                            <span className="factor-val">{data.ch4_20}×</span>
                                        </div>
                                        <div className="factor-item">
                                            <span className="factor-label">N₂O (100-yr)</span>
                                            <span className="factor-val">{data.n2o_100}×</span>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Live Comparison Table */}
                    <div className="comparison-container">
                        <div className="comparison-header">
                            <Layers size={18} className="comparison-icon" />
                            <h3>Conversion Factor Matrix Comparison</h3>
                        </div>
                        <div className="comparison-table-wrapper">
                            <table className="comparison-table">
                                <thead>
                                    <tr>
                                        <th>Metric / Gas</th>
                                        <th>AR4 (2007)</th>
                                        <th>AR5 (2014 - Default)</th>
                                        <th>AR6 (2021)</th>
                                        <th>Application Context</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>Carbon Dioxide (CO₂)</strong></td>
                                        <td>1.0</td>
                                        <td>1.0</td>
                                        <td>1.0</td>
                                        <td>Universal baseline anchor</td>
                                    </tr>
                                    <tr className={gwpStandard === 'AR5' ? 'active-row' : ''}>
                                        <td><strong>Methane (CH₄) - 100 Year</strong></td>
                                        <td>25.0×</td>
                                        <td><strong>28.0×</strong></td>
                                        <td>27.9×</td>
                                        <td>Corporate GHG Inventory / Scope 1</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Methane (CH₄) - 20 Year</strong></td>
                                        <td>72.0×</td>
                                        <td><strong>82.5×</strong></td>
                                        <td>82.5×</td>
                                        <td>Near-Term Climate Impact / ESG Analytics</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Nitrous Oxide (N₂O) - 100 Year</strong></td>
                                        <td>298.0×</td>
                                        <td><strong>265.0×</strong></td>
                                        <td>273.0×</td>
                                        <td>Flaring / Combustion byproducts</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {/* TAB CONTENT: OGMP 2.0 Baseline & Thresholds */}
            {activeTab === 'ogmp' && (
                <div className="settings-section-card">
                    <div className="section-intro">
                        <div className="section-intro-header">
                            <Target size={20} className="section-icon" />
                            <h2>OGMP 2.0 Framework & Threshold Configuration</h2>
                        </div>
                        <p>Establish global compliance benchmarks, default asset membership years, and acceptable reconciliation tolerances.</p>
                    </div>

                    <div className="ogmp-config-grid">
                        <div className="config-card">
                            <label className="config-label">
                                Default OGMP 2.0 Membership Baseline Year
                            </label>
                            <span className="config-subtext">The year from which the Gold Standard milestone clock begins (Year 0).</span>
                            <div className="year-selector-buttons">
                                {[2021, 2022, 2023, 2024, 2025, 2026].map(yr => (
                                    <button
                                        key={yr}
                                        type="button"
                                        className={`btn-year-pill ${defaultBaseYear === yr ? 'active' : ''}`}
                                        onClick={() => setDefaultBaseYear(yr)}
                                    >
                                        {yr}
                                    </button>
                                ))}
                            </div>
                            <div className="deadline-preview-note">
                                <div className="deadline-title">
                                    <ShieldCheck size={15} />
                                    <span>Gold Standard Deadlines:</span>
                                </div>
                                <ul className="deadline-list">
                                    <li>Operated Assets (3 Years): <strong>{defaultBaseYear + 3}</strong></li>
                                    <li>Non-Operated Assets (5 Years): <strong>{defaultBaseYear + 5}</strong></li>
                                </ul>
                            </div>
                        </div>

                        <div className="config-card">
                            <label className="config-label">
                                Global Reconciliation Variance Threshold (±%)
                            </label>
                            <span className="config-subtext">Maximum tolerable difference between Bottom-Up (L1-L4) inventory and Top-Down (L4/L5) site measurements.</span>
                            
                            <div className="threshold-slider-box">
                                <input 
                                    type="range" 
                                    min="5" 
                                    max="50" 
                                    step="1"
                                    value={globalThreshold} 
                                    onChange={(e) => setGlobalThreshold(Number(e.target.value))}
                                    className="range-slider"
                                    id="global-threshold-slider"
                                />
                                <div className="threshold-val-display">
                                    ±{globalThreshold}%
                                </div>
                            </div>
                            <p className="slider-hint">OGMP 2.0 recommended default is <strong>±20.0%</strong>. Facilities exceeding this threshold will be flagged for investigation.</p>
                        </div>
                    </div>

                    <div className="target-standards-box">
                        <div className="target-header">
                            <Activity size={18} className="target-icon" />
                            <h3>OGMP 2.0 Methane Intensity Targets</h3>
                        </div>
                        <div className="targets-grid">
                            <div className="target-card upstream">
                                <div className="target-segment">Upstream Exploration & Production</div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '8px 0' }}>
                                    <input 
                                        type="number" 
                                        step="0.01" 
                                        min="0.01" 
                                        max="5.0"
                                        value={upstreamTarget}
                                        onChange={(e) => setUpstreamTarget(Number(e.target.value))}
                                        className="form-input"
                                        style={{ width: '100px', fontWeight: 700, fontSize: '1.1rem', color: '#2563eb' }}
                                        id="upstream-target-input"
                                    />
                                    <span style={{ fontWeight: 700, fontSize: '1.1rem', color: '#2563eb' }}>%</span>
                                </div>
                                <div className="target-desc">Methane loss volume as % of total marketable natural gas volume. (Default: 0.20%)</div>
                            </div>
                            <div className="target-card midstream">
                                <div className="target-segment">Midstream Processing & LNG</div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '8px 0' }}>
                                    <input 
                                        type="number" 
                                        step="0.01" 
                                        min="0.01" 
                                        max="5.0"
                                        value={midstreamTarget}
                                        onChange={(e) => setMidstreamTarget(Number(e.target.value))}
                                        className="form-input"
                                        style={{ width: '100px', fontWeight: 700, fontSize: '1.1rem', color: '#10b981' }}
                                        id="midstream-target-input"
                                    />
                                    <span style={{ fontWeight: 700, fontSize: '1.1rem', color: '#10b981' }}>%</span>
                                </div>
                                <div className="target-desc">Methane loss volume as % of total throughput volume. (Default: 0.05%)</div>
                            </div>
                        </div>
                    </div>

                    <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
                        <button 
                            className="btn-primary"
                            onClick={handleSaveGlobal}
                            disabled={saving}
                            id="save-ogmp-settings-btn"
                            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 24px' }}
                        >
                            <Save size={18} />
                            {saving ? 'Saving Changes...' : 'Save OGMP & Target Settings'}
                        </button>
                    </div>
                </div>
            )}

            {/* TAB CONTENT: Facility-Level Overrides */}
            {activeTab === 'facilities' && (
                <div className="settings-section-card">
                    <div className="section-intro">
                        <div className="section-intro-header">
                            <Building2 size={20} className="section-icon" />
                            <h2>Facility-Level OGMP Overrides</h2>
                        </div>
                        <p>Customize operator status (Operated vs Non-Operated), country, base year, and specific reconciliation variance thresholds for each facility.</p>
                    </div>

                    <div className="facility-table-wrapper">
                        <table className="facility-config-table">
                            <thead>
                                <tr>
                                    <th>Facility Name</th>
                                    <th>Segment</th>
                                    <th>Operator Status</th>
                                    <th>Country</th>
                                    <th>Base Year</th>
                                    <th>Target Year</th>
                                    <th>Threshold (±%)</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {facilities.map(fac => {
                                    const edit = facilityEdits[fac.id] || {};
                                    const opStatus = edit.operator_status || 'operated';
                                    const baseYear = Number(edit.ogmp_membership_year || 2023);
                                    const targetYear = baseYear + (opStatus === 'operated' ? 3 : 5);

                                    return (
                                        <tr key={fac.id}>
                                            <td className="fac-name-cell">
                                                <strong>{fac.name}</strong>
                                                <span className="fac-code">{fac.code || 'FAC-' + fac.id}</span>
                                            </td>
                                            <td>{fac.segment || 'Upstream'}</td>
                                            <td>
                                                <select 
                                                    className="table-select"
                                                    value={opStatus}
                                                    onChange={(e) => handleFacilityChange(fac.id, 'operator_status', e.target.value)}
                                                >
                                                    <option value="operated">Operated (3-yr target)</option>
                                                    <option value="non_operated">Non-Operated (5-yr target)</option>
                                                </select>
                                            </td>
                                            <td>
                                                <input 
                                                    type="text" 
                                                    className="table-input"
                                                    value={edit.country || 'Algeria'}
                                                    onChange={(e) => handleFacilityChange(fac.id, 'country', e.target.value)}
                                                />
                                            </td>
                                            <td>
                                                <select 
                                                    className="table-select-small"
                                                    value={baseYear}
                                                    onChange={(e) => handleFacilityChange(fac.id, 'ogmp_membership_year', e.target.value)}
                                                >
                                                    {[2021, 2022, 2023, 2024, 2025, 2026].map(y => (
                                                        <option key={y} value={y}>{y}</option>
                                                    ))}
                                                </select>
                                            </td>
                                            <td className="target-yr-cell">
                                                <span className="badge-target-year">{targetYear}</span>
                                            </td>
                                            <td>
                                                <div className="threshold-input-box">
                                                    <span>±</span>
                                                    <input 
                                                        type="number" 
                                                        min="1" 
                                                        max="100"
                                                        className="table-input-num"
                                                        value={edit.reconciliation_threshold || 20.0}
                                                        onChange={(e) => handleFacilityChange(fac.id, 'reconciliation_threshold', e.target.value)}
                                                    />
                                                    <span>%</span>
                                                </div>
                                            </td>
                                            <td>
                                                <button 
                                                    className="btn-table-save"
                                                    onClick={() => handleSaveFacility(fac.id)}
                                                    title="Save Facility Settings"
                                                >
                                                    <Save size={13} />
                                                    <span>Save</span>
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Settings;
