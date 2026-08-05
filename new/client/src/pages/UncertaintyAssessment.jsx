import React, { useState, useEffect } from 'react';
import { Info, ShieldCheck, Database, Layers, BarChart, TrendingUp, AlertTriangle } from 'lucide-react';
import api from '../api';
import './UncertaintyAssessment.css';

const UncertaintyAssessment = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedYear, setSelectedYear] = useState('all');
    const [availableYears, setAvailableYears] = useState([]);

    const fetchData = async () => {
        setLoading(true);
        try {
            // First load filters if not loaded
            if (availableYears.length === 0) {
                const filterRes = await api.get('/filters/available');
                if (filterRes.data && filterRes.data.years && filterRes.data.years.length > 0) {
                    setAvailableYears(filterRes.data.years);
                    // If current selection is default, set to latest year
                    if (selectedYear === 'all') {
                        setSelectedYear(filterRes.data.years[0].toString());
                        return; // Effect will trigger again
                    }
                }
            }

            const res = await api.get(`/dashboard/uncertainty?year=${selectedYear === 'all' ? '' : selectedYear}`);
            setData(res.data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to load uncertainty data:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedYear]);

    if (loading) return <div className="loading-container" style={{ color: '#fff', padding: '50px', textAlign: 'center' }}>Quantifying Inventory Uncertainty...</div>;
    if (!data) return <div className="error-container">No uncertainty data available.</div>;

    return (
        <div className="uncertainty-assessment">
            <header className="top-bar" style={{ padding: '0 0 30px 0', border: 'none', background: 'transparent' }}>
                <div className="breadcrumbs">
                    <ShieldCheck size={14} style={{ marginRight: '8px', color: 'var(--text-secondary)' }} />
                    <span>Compliance</span>
                    <span style={{ margin: '0 8px', color: 'var(--text-secondary)' }}>/</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Uncertainty Assessment</span>
                </div>
            </header>

            <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                    <h1 style={{ fontSize: '2.5rem', fontWeight: 800, color: '#1e293b', margin: '0 0 10px 0' }}>Data Reliability Analysis</h1>
                    <p style={{ fontSize: '1.1rem', color: '#64748b', maxWidth: '800px' }}>
                        Dynamic uncertainty quantification across the complete GHG inventory.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-end' }}>
                    <div className="filter-group-alt">
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', marginBottom: '8px', textTransform: 'uppercase' }}>Select Reporting Year</label>
                        <select
                            value={selectedYear}
                            onChange={(e) => setSelectedYear(e.target.value)}
                            style={{ padding: '10px 16px', borderRadius: '10px', border: '1px solid #e2e8f0', background: '#fff', fontSize: '0.9rem', fontWeight: 600, color: '#334155', minWidth: '120px' }}
                        >
                            <option value="all">Select Year</option>
                            {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                    </div>
                    <div style={{ background: 'rgba(30, 41, 59, 0.05)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(0,0,0,0.05)', textAlign: 'right' }}>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '4px' }}>Inventory Uncertainty</div>
                        <div style={{ fontSize: '2rem', fontWeight: 800, color: data.inventory_uncertainty_decimal < 0.1 ? '#10b981' : (data.inventory_uncertainty_decimal < 0.2 ? '#f59e0b' : '#ef4444') }}>
                            {data.inventory_uncertainty_pct}
                        </div>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '40px' }}>
                {Object.entries(data.tier_breakdown || {}).map(([tier, pct]) => (
                    <div key={tier} style={{ background: '#fff', padding: '20px', borderRadius: '12px', border: '1px solid #f1f5f9', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>{tier} (Data Quality)</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 700, margin: '8px 0', color: tier === 'Tier 3' ? '#10b981' : (tier === 'Tier 2' ? '#3b82f6' : '#f59e0b') }}>{pct}%</div>
                        <div style={{ width: '100%', height: '4px', background: '#f1f5f9', borderRadius: '2px' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: tier === 'Tier 3' ? '#10b981' : (tier === 'Tier 2' ? '#3b82f6' : '#f59e0b'), borderRadius: '2px' }}></div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="legend-bar">
                <div className="legend-item">
                    <div className="legend-dot" style={{ background: '#10b981' }}></div>
                    Low Uncertainty (≤ ±5%)
                </div>
                <div className="legend-item">
                    <div className="legend-dot" style={{ background: '#f59e0b' }}></div>
                    Medium Uncertainty (±5% to ±15%)
                </div>
                <div className="legend-item">
                    <div className="legend-dot" style={{ background: '#ef4444' }}></div>
                    High Uncertainty (&gt; ±15%)
                </div>
            </div>

            <div className="category-grid">
                {data.categories.map((section, idx) => (
                    <div key={idx} className="category-section" style={{ marginBottom: '40px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h3 className="category-title" style={{ margin: 0 }}>{section.category}</h3>
                            <div className={`uncertainty-badge uncertainty-${section.level}`}>
                                {section.uncertainty_pct}
                            </div>
                        </div>

                        <div className="uncertainty-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
                            {section.top_contributors.map((factor, fIdx) => (
                                <div key={fIdx} className="factor-card" style={{ background: '#fff', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                                    <div className="factor-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
                                        <div>
                                            <div className="factor-name" style={{ fontWeight: 700, fontSize: '1.1rem', color: '#1e293b' }}>{factor.name}</div>
                                            <div className="factor-source" style={{ fontSize: '0.8rem', color: '#64748b' }}>Primary Contributor</div>
                                        </div>
                                        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#64748b', padding: '4px 8px', background: '#f1f5f9', borderRadius: '6px' }}>
                                            {factor.uncertainty}
                                        </div>
                                    </div>
                                    <div className="factor-stats" style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px', color: '#64748b' }}>
                                                <span>Impact on Category</span>
                                                <span style={{ fontWeight: 600 }}>{factor.contribution}%</span>
                                            </div>
                                            <div style={{ width: '100%', height: '6px', background: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
                                                <div style={{ width: `${factor.contribution}%`, height: '100%', background: '#3b82f6' }}></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ marginTop: '60px', padding: '30px', background: 'rgba(30, 41, 59, 0.03)', borderRadius: '20px', border: '1px dashed #cbd5e1' }}>
                <div style={{ display: 'flex', gap: '20px' }}>
                    <Info size={24} style={{ color: '#64748b' }} />
                    <div>
                        <h4 style={{ margin: '0 0 8px 0', color: '#1e293b' }}>Calculation Methodology</h4>
                        <p style={{ margin: 0, color: '#64748b', fontSize: '0.95rem', lineHeight: '1.6' }}>
                            Uncertainty is quantified using the Square Root of Sum of Squares (SRSS) propagation method.
                            Individual emission factor uncertainties are derived from the calculation tiers (IPCC/API):
                            Tier 3 (±3%), Tier 2 (±8%), and Tier 1 (±20-40%). The final results represent the 95% confidence interval
                            for the reported inventory.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UncertaintyAssessment;
