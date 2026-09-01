import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { useToast } from '../components/Toast';
import { Download, AlertTriangle, CheckCircle, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBoundary from '../components/ErrorBoundary';
import './Dashboard.css';

const PAGE_SIZE = 100;

export default function QADashboard() {
    const toast = useToast();
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [scopeFilter, setScopeFilter] = useState('all');
    const [yearFilter, setYearFilter] = useState('all');
    const [offset, setOffset] = useState(0);
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [resolving, setResolving] = useState(false);
    const [exporting, setExporting] = useState(false);

    const fetchDashboard = useCallback(async () => {
        setLoading(true);
        setSelectedIds(new Set());
        try {
            const params = { limit: PAGE_SIZE, offset };
            if (scopeFilter !== 'all') params.scope = scopeFilter;
            if (yearFilter !== 'all') params.year = yearFilter;
            const res = await api.get('/qaqc/dashboard', { params });
            setData(res.data);
        } catch (err) {
            toast.error(err.response?.data?.error || 'Failed to load QA/QC data');
        } finally {
            setLoading(false);
        }
    }, [scopeFilter, yearFilter, offset]);

    useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

    // ── Export via Axios blob (keeps session cookie) ──────────────────────
    const handleExport = async () => {
        setExporting(true);
        try {
            const params = {};
            if (scopeFilter !== 'all') params.scope = scopeFilter;
            if (yearFilter !== 'all') params.year = yearFilter;
            const res = await api.get('/qaqc/export', {
                params,
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = 'qa_qc_report.csv';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            toast.success('QA report exported successfully');
        } catch (err) {
            toast.error(err.response?.data?.error || 'Export failed');
        } finally {
            setExporting(false);
        }
    };

    // ── Bulk resolve ──────────────────────────────────────────────────────
    const handleBulkResolve = async (resolution) => {
        if (selectedIds.size === 0) {
            toast.error('Select at least one record first');
            return;
        }
        if (!window.confirm(`Mark ${selectedIds.size} record(s) as "${resolution}"?`)) return;

        setResolving(true);
        try {
            const records = [...selectedIds].map(key => {
                const [scope, id] = key.split('-');
                return { id: parseInt(id, 10), scope: parseInt(scope, 10) };
            });
            const res = await api.post('/qaqc/bulk-resolve', { records, resolution });
            toast.success(res.data.message);
            fetchDashboard();
        } catch (err) {
            toast.error(err.response?.data?.error || 'Bulk resolve failed');
        } finally {
            setResolving(false);
        }
    };

    const toggleSelect = (scope, id) => {
        const key = `${scope}-${id}`;
        setSelectedIds(prev => {
            const next = new Set(prev);
            next.has(key) ? next.delete(key) : next.add(key);
            return next;
        });
    };

    const toggleSelectAll = () => {
        if (!data) return;
        if (selectedIds.size === data.flagged_records.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(data.flagged_records.map(r => `${r.scope}-${r.id}`)));
        }
    };

    if (loading) return <LoadingSpinner />;
    if (!data) return <div className="dashboard-content">No Data Available</div>;

    const { tier1_uncertainty, flagged_records, total_flagged_count, returned_count } = data;
    const totalPages = Math.ceil((total_flagged_count || 0) / PAGE_SIZE);
    const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

    return (
        <ErrorBoundary>
            <div className="dashboard-content">
                <div className="dashboard-grid">

                    {/* Header row */}
                    <div className="dashboard-header-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                        <h1 className="grid-title">QA/QC Dashboard</h1>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>

                            {/* Scope filter */}
                            <select
                                value={scopeFilter}
                                onChange={e => { setScopeFilter(e.target.value); setOffset(0); }}
                                style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}
                            >
                                <option value="all">All Scopes</option>
                                <option value="1">Scope 1</option>
                                <option value="2">Scope 2</option>
                                <option value="3">Scope 3</option>
                            </select>

                            {/* Year filter */}
                            <select
                                value={yearFilter}
                                onChange={e => { setYearFilter(e.target.value); setOffset(0); }}
                                style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}
                            >
                                <option value="all">All Years</option>
                                {[2020, 2021, 2022, 2023, 2024, 2025, 2026].map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </select>

                            <button
                                className="action-button secondary"
                                onClick={fetchDashboard}
                                title="Refresh"
                                style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '6px 12px', fontSize: '0.8rem' }}
                            >
                                <RefreshCw size={13} /> Refresh
                            </button>
                            <button
                                className="action-button secondary"
                                onClick={handleExport}
                                disabled={exporting}
                                style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '6px 12px', fontSize: '0.8rem' }}
                            >
                                <Download size={13} /> {exporting ? 'Exporting…' : 'Export CSV'}
                            </button>
                        </div>
                    </div>

                    {/* Uncertainty Overview Card */}
                    <div className="card hero-card glass-panel">
                        <div className="hero-header">
                            <h2 className="hero-title">Uncertainty Assessment (IPCC SRSS)</h2>
                            <div className="location-badge">ISO 14064-1:2018 §7.5</div>
                        </div>
                        <div className="hero-stats-grid">
                            <div className="stat-item">
                                <div className="stat-label">Overall</div>
                                <div className="stat-value-row">
                                    <div className="stat-value warning">
                                        {((tier1_uncertainty.overall || 0) * 100).toFixed(2)}
                                    </div>
                                    <span className="stat-unit">%</span>
                                </div>
                            </div>
                            <div className="stat-item border-left">
                                <div className="stat-label">Scope 1</div>
                                <div className="stat-value-row">
                                    <div className="stat-value">{((tier1_uncertainty.scope1 || 0) * 100).toFixed(2)}</div>
                                    <span className="stat-unit">%</span>
                                </div>
                                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                                    {(tier1_uncertainty.s1_total_tco2e || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} tCO₂e
                                </div>
                            </div>
                            <div className="stat-item border-left">
                                <div className="stat-label">Scope 2</div>
                                <div className="stat-value-row">
                                    <div className="stat-value energy">{((tier1_uncertainty.scope2 || 0) * 100).toFixed(2)}</div>
                                    <span className="stat-unit">%</span>
                                </div>
                                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                                    {(tier1_uncertainty.s2_total_tco2e || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} tCO₂e
                                </div>
                            </div>
                            <div className="stat-item border-left">
                                <div className="stat-label">Scope 3</div>
                                <div className="stat-value-row">
                                    <div className="stat-value">{((tier1_uncertainty.scope3 || 0) * 100).toFixed(2)}</div>
                                    <span className="stat-unit">%</span>
                                </div>
                                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                                    {(tier1_uncertainty.s3_total_tco2e || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} tCO₂e
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Anomalies Table Card */}
                    <div className="card glass-panel">
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid rgba(226,232,240,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                            <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#1e293b', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                Anomalies Flagged for Review
                                <span style={{ background: '#fef2f2', color: '#ef4444', padding: '2px 8px', borderRadius: '12px', fontSize: '0.78rem' }}>
                                    {total_flagged_count}
                                </span>
                            </h2>

                            {/* Bulk actions */}
                            {selectedIds.size > 0 && (
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.82rem', color: '#64748b' }}>{selectedIds.size} selected</span>
                                    <button
                                        className="action-button"
                                        onClick={() => handleBulkResolve('Verified')}
                                        disabled={resolving}
                                        style={{ padding: '5px 12px', fontSize: '0.8rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
                                    >
                                        {resolving ? '…' : '✓ Approve'}
                                    </button>
                                    <button
                                        className="action-button"
                                        onClick={() => handleBulkResolve('Rejected')}
                                        disabled={resolving}
                                        style={{ padding: '5px 12px', fontSize: '0.8rem', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
                                    >
                                        {resolving ? '…' : '✕ Reject'}
                                    </button>
                                </div>
                            )}
                        </div>

                        {flagged_records.length === 0 ? (
                            <div style={{ padding: '64px 24px', textAlign: 'center' }}>
                                <div style={{ background: '#ecfdf5', color: '#10b981', width: '64px', height: '64px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto' }}>
                                    <CheckCircle size={32} />
                                </div>
                                <h3 style={{ fontSize: '1.25rem', color: '#0f172a', fontWeight: '700', marginBottom: '8px' }}>No anomalies detected</h3>
                                <p style={{ color: '#64748b', maxWidth: '400px', margin: '0 auto' }}>
                                    Your inventory is fully QA-compliant. No outlier or malformed records found for the selected filters.
                                </p>
                            </div>
                        ) : (
                            <>
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                        <thead>
                                            <tr>
                                                <th style={thStyle}>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIds.size === flagged_records.length && flagged_records.length > 0}
                                                        onChange={toggleSelectAll}
                                                    />
                                                </th>
                                                <th style={thStyle}>Record ID</th>
                                                <th style={thStyle}>Scope</th>
                                                <th style={thStyle}>Year</th>
                                                <th style={thStyle}>Process / Source</th>
                                                <th style={thStyle}>Issue (QA Flag)</th>
                                                <th style={thStyle}>Emissions (tCO₂e)</th>
                                                <th style={thStyle}>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {flagged_records.map(record => {
                                                const key = `${record.scope}-${record.id}`;
                                                return (
                                                    <tr
                                                        key={key}
                                                        style={{ borderBottom: '1px solid rgba(226,232,240,0.6)', background: selectedIds.has(key) ? 'rgba(16,185,129,0.04)' : undefined }}
                                                    >
                                                        <td style={tdStyle}>
                                                            <input
                                                                type="checkbox"
                                                                checked={selectedIds.has(key)}
                                                                onChange={() => toggleSelect(record.scope, record.id)}
                                                            />
                                                        </td>
                                                        <td style={{ ...tdStyle, fontFamily: 'monospace', color: '#64748b', fontSize: '0.8rem' }}>
                                                            {record.record_id || record.id}
                                                        </td>
                                                        <td style={{ ...tdStyle, fontWeight: '500', color: '#334155' }}>Scope {record.scope}</td>
                                                        <td style={{ ...tdStyle, color: '#475569' }}>{record.year || '—'}</td>
                                                        <td style={{ ...tdStyle, color: '#475569', fontSize: '0.85rem' }}>{record.process_type || '—'}</td>
                                                        <td style={tdStyle}>
                                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#d97706', fontWeight: '500', background: '#fffbeb', padding: '5px 10px', borderRadius: '6px', fontSize: '0.82rem' }}>
                                                                <AlertTriangle size={13} />
                                                                {record.qa_flag}
                                                            </span>
                                                        </td>
                                                        <td style={{ ...tdStyle, fontFamily: 'monospace', fontWeight: '600', color: '#334155' }}>
                                                            {record.co2e != null ? record.co2e.toFixed(2) : '0.00'}
                                                        </td>
                                                        <td style={tdStyle}>
                                                            <span style={{
                                                                padding: '4px 10px',
                                                                borderRadius: '9999px',
                                                                fontSize: '0.75rem',
                                                                fontWeight: '600',
                                                                background: record.status?.toLowerCase().includes('pending') ? '#fef3c7' : '#dcfce7',
                                                                color: record.status?.toLowerCase().includes('pending') ? '#b45309' : '#15803d',
                                                                border: `1px solid ${record.status?.toLowerCase().includes('pending') ? '#fde68a' : '#bbf7d0'}`,
                                                            }}>
                                                                {record.status}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Pagination */}
                                {total_flagged_count > PAGE_SIZE && (
                                    <div style={{ padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(226,232,240,0.6)' }}>
                                        <span style={{ fontSize: '0.82rem', color: '#64748b' }}>
                                            Showing {offset + 1}–{Math.min(offset + returned_count, total_flagged_count)} of {total_flagged_count}
                                        </span>
                                        <div style={{ display: 'flex', gap: '6px' }}>
                                            <button
                                                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                                                disabled={offset === 0}
                                                style={paginationBtnStyle(offset === 0)}
                                            >
                                                <ChevronLeft size={14} />
                                            </button>
                                            <span style={{ fontSize: '0.82rem', color: '#475569', padding: '0 8px', lineHeight: '28px' }}>
                                                Page {currentPage} / {totalPages}
                                            </span>
                                            <button
                                                onClick={() => setOffset(offset + PAGE_SIZE)}
                                                disabled={offset + PAGE_SIZE >= total_flagged_count}
                                                style={paginationBtnStyle(offset + PAGE_SIZE >= total_flagged_count)}
                                            >
                                                <ChevronRight size={14} />
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </ErrorBoundary>
    );
}

// ── Style helpers ──────────────────────────────────────────────────────────
const thStyle = {
    padding: '12px 16px',
    textAlign: 'left',
    fontSize: '0.72rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: '#64748b',
    fontWeight: '600',
    borderBottom: '1px solid rgba(226,232,240,0.6)',
    background: 'rgba(248,250,252,0.5)',
    whiteSpace: 'nowrap',
};

const tdStyle = {
    padding: '12px 16px',
    verticalAlign: 'middle',
};

const paginationBtnStyle = (disabled) => ({
    padding: '0 8px',
    height: '28px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    background: disabled ? '#f8fafc' : '#fff',
    color: disabled ? '#cbd5e1' : '#475569',
    cursor: disabled ? 'default' : 'pointer',
    display: 'flex',
    alignItems: 'center',
});
