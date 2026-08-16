import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from '../components/Toast';
import { Download, AlertTriangle, CheckCircle } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBoundary from '../components/ErrorBoundary';
import './Dashboard.css';

export default function QADashboard() {
    const toast = useToast();
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);

    useEffect(() => {
        const fetchDashboard = async () => {
            try {
                const res = await api.get('/qaqc/dashboard');
                setData(res.data);
            } catch (err) {
                toast.error("Failed to load QA/QC data");
            } finally {
                setLoading(false);
            }
        };
        fetchDashboard();
    }, []);

    if (loading) return <LoadingSpinner />;
    if (!data) return <div className="dashboard-content">No Data Available</div>;

    const { tier1_uncertainty, flagged_records } = data;

    return (
        <ErrorBoundary>
            <div className="dashboard-content">
                <div className="dashboard-grid">
                    <div className="dashboard-header-row">
                        <h1 className="grid-title">QA/QC Dashboard</h1>
                        <button 
                            className="action-button secondary" 
                            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '0.8rem' }}
                            onClick={() => {
                                window.open(api.defaults.baseURL + '/qaqc/export', '_blank');
                                toast.success("Report export started");
                            }}
                        >
                            <Download size={14} /> Export QA Report (CSV)
                        </button>
                    </div>

                    {/* Uncertainty Overview Card */}
                    <div className="card hero-card glass-panel">
                        <div className="hero-header">
                            <h2 className="hero-title">Uncertainty Assessment</h2>
                            <div className="location-badge">
                                IPCC Tier 1
                            </div>
                        </div>

                        <div className="hero-stats-grid">
                            <div className="stat-item">
                                <div className="stat-label">Overall Uncertainty</div>
                                <div className="stat-value-row">
                                    <div className="stat-value warning">
                                        {((tier1_uncertainty.overall || 0) * 100).toFixed(2)}
                                    </div>
                                    <span className="stat-unit">%</span>
                                </div>
                            </div>
                            
                            <div className="stat-item border-left">
                                <div className="stat-label">Scope 1 Uncertainty</div>
                                <div className="stat-value-row">
                                    <div className="stat-value">
                                        {((tier1_uncertainty.scope1 || 0) * 100).toFixed(2)}
                                    </div>
                                    <span className="stat-unit">%</span>
                                </div>
                            </div>

                            <div className="stat-item border-left">
                                <div className="stat-label">Scope 2 Uncertainty</div>
                                <div className="stat-value-row">
                                    <div className="stat-value energy">
                                        {((tier1_uncertainty.scope2 || 0) * 100).toFixed(2)}
                                    </div>
                                    <span className="stat-unit">%</span>
                                </div>
                            </div>

                            <div className="stat-item border-left">
                                <div className="stat-label">Scope 3 Uncertainty</div>
                                <div className="stat-value-row">
                                    <div className="stat-value">
                                        {((tier1_uncertainty.scope3 || 0) * 100).toFixed(2)}
                                    </div>
                                    <span className="stat-unit">%</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Anomalies Table Card */}
                    <div className="card glass-panel">
                        <div style={{ padding: '24px', borderBottom: '1px solid rgba(226, 232, 240, 0.6)' }}>
                            <h2 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                Anomalies Flagged for Review
                                <span style={{ background: '#fef2f2', color: '#ef4444', padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem' }}>
                                    {flagged_records.length}
                                </span>
                            </h2>
                        </div>
                        
                        {flagged_records.length === 0 ? (
                            <div style={{ padding: '64px 24px', textAlign: 'center' }}>
                                <div style={{ background: '#ecfdf5', color: '#10b981', width: '64px', height: '64px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto' }}>
                                    <CheckCircle size={32} />
                                </div>
                                <h3 style={{ fontSize: '1.25rem', color: '#0f172a', fontWeight: '700', marginBottom: '8px' }}>No anomalies detected</h3>
                                <p style={{ color: '#64748b', maxWidth: '400px', margin: '0 auto' }}>Your database is fully compliant with QA thresholds. No outlier or malformed records were found.</p>
                            </div>
                        ) : (
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr>
                                            <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', fontWeight: '600', borderBottom: '1px solid rgba(226, 232, 240, 0.6)', background: 'rgba(248, 250, 252, 0.5)' }}>Record ID</th>
                                            <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', fontWeight: '600', borderBottom: '1px solid rgba(226, 232, 240, 0.6)', background: 'rgba(248, 250, 252, 0.5)' }}>Scope</th>
                                            <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', fontWeight: '600', borderBottom: '1px solid rgba(226, 232, 240, 0.6)', background: 'rgba(248, 250, 252, 0.5)' }}>Issue (QA Flag)</th>
                                            <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', fontWeight: '600', borderBottom: '1px solid rgba(226, 232, 240, 0.6)', background: 'rgba(248, 250, 252, 0.5)' }}>Emissions (tCO₂e)</th>
                                            <th style={{ padding: '16px 24px', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', fontWeight: '600', borderBottom: '1px solid rgba(226, 232, 240, 0.6)', background: 'rgba(248, 250, 252, 0.5)' }}>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {flagged_records.map(record => (
                                            <tr key={record.id} style={{ borderBottom: '1px solid rgba(226, 232, 240, 0.6)', transition: 'background 0.2s' }}>
                                                <td style={{ padding: '16px 24px', fontFamily: 'monospace', color: '#64748b' }}>{record.id}</td>
                                                <td style={{ padding: '16px 24px', fontWeight: '500', color: '#334155' }}>Scope {record.scope}</td>
                                                <td style={{ padding: '16px 24px' }}>
                                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: '#d97706', fontWeight: '500', background: '#fffbeb', padding: '6px 12px', borderRadius: '6px' }}>
                                                        <AlertTriangle size={14} />
                                                        {record.qa_flag}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '16px 24px', fontFamily: 'monospace', fontWeight: '600', color: '#334155' }}>{record.co2e?.toFixed(2) || '0.00'}</td>
                                                <td style={{ padding: '16px 24px' }}>
                                                    <span style={{ 
                                                        padding: '6px 12px', 
                                                        borderRadius: '9999px', 
                                                        fontSize: '0.75rem', 
                                                        fontWeight: '600', 
                                                        display: 'inline-flex', 
                                                        alignItems: 'center',
                                                        background: record.status.toLowerCase().includes('pending') ? '#fef3c7' : '#dcfce7',
                                                        color: record.status.toLowerCase().includes('pending') ? '#b45309' : '#15803d',
                                                        border: `1px solid ${record.status.toLowerCase().includes('pending') ? '#fde68a' : '#bbf7d0'}`
                                                    }}>
                                                        {record.status}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </ErrorBoundary>
    );
}
