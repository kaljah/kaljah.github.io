import QADashboardZeroAnomaliesDetected from "./qa/QADashboardZeroAnomaliesDetected";
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { NativeSelect } from "../ui/NativeSelect";
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useToast } from '../components/Toast';
import { 
    Download, AlertTriangle, CheckCircle, RefreshCw, ChevronLeft, ChevronRight,
    Search, Shield, Layers, Sparkles, Check, X, ArrowRight,
    AlertCircle, Database, MapPin, Zap, Flame, FileText, CheckSquare, Square,
    ChevronDown, ChevronUp, Eye
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBoundary from '../components/ErrorBoundary';
import Modal from '../components/Modal';
import './Dashboard.css';
import './QADashboard.css';

const PAGE_SIZE = 100;

export default function QADashboard() {
    const toast = useToast();
    const navigate = useNavigate();

    // ── State ──────────────────────────────────────────────────────────────
    const [loading, setLoading] = useState(true);
    const [isUpdating, setIsUpdating] = useState(false);
    const [runningDiagnostics, setRunningDiagnostics] = useState(false);
    const isFirstLoadRef = useRef(true);

    const [data, setData] = useState(null);
    const [scopeFilter, setScopeFilter] = useState('all');
    const [yearFilter, setYearFilter] = useState('all');
    const [offset, setOffset] = useState(0);

    // Active workflow tab: 'queue' | 'diagnostics' | 'uncertainty'
    const [activeTab, setActiveTab] = useState('queue');

    // Queue search and filter
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'pending' | 'verified' | 'rejected'

    // Selection for bulk actions
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [resolving, setResolving] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [resolveModal, setResolveModal] = useState({ isOpen: false, resolution: null });
    const [expandedFindingId, setExpandedFindingId] = useState(null);

    const handleFindingAction = useCallback((item) => {
        if (item.action_url) {
            const [, query] = item.action_url.split('?');
            const tab = query ? new URLSearchParams(query).get('tab') : null;
            navigate(item.action_url, { state: { tab } });
        } else if (item.action_tab === 'queue') {
            setActiveTab('queue');
            setStatusFilter('all');
            setOffset(0);
        }
    }, [navigate]);

    // ── Fetch unified QA/QC & Diagnostics data ─────────────────────────────
    const fetchDashboard = useCallback(async (isManualRefresh = false) => {
        if (isManualRefresh) {
            setRunningDiagnostics(true);
        } else if (isFirstLoadRef.current) {
            setLoading(true);
        } else {
            setIsUpdating(true);
        }
        setSelectedIds(new Set());

        try {
            const params = { limit: PAGE_SIZE, offset };
            if (scopeFilter !== 'all') params.scope = scopeFilter;
            if (yearFilter !== 'all') params.year = yearFilter;
            params.status = statusFilter;

            const res = await api.get('/qaqc/dashboard', { params });
            setData(res.data);
            if (isManualRefresh) {
                toast.success('Diagnostics and anomaly scans refreshed successfully');
            }
        } catch (err) {
            toast.error(err.response?.data?.error || err.response?.data?.message || 'Failed to load QA/QC data');
        } finally {
            setLoading(false);
            setIsUpdating(false);
            setRunningDiagnostics(false);
            isFirstLoadRef.current = false;
        }
    }, [scopeFilter, yearFilter, statusFilter, offset, toast]);

    useEffect(() => {
        fetchDashboard();
    }, [fetchDashboard]);

    // ── Export CSV report (keeps session cookie via Axios blob) ────────────
    const handleExport = async () => {
        setExporting(true);
        try {
            const params = {};
            if (scopeFilter !== 'all') params.scope = scopeFilter;
            if (yearFilter !== 'all') params.year = yearFilter;
            params.status = statusFilter;

            const res = await api.get('/qaqc/export', {
                params,
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = `qa_qc_report_${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            toast.success('Compliance QA report exported successfully');
        } catch (err) {
            toast.error(err.response?.data?.error || 'CSV Export failed');
        } finally {
            setExporting(false);
        }
    };

    // ── Bulk resolve ───────────────────────────────────────────────────────
    const handleBulkResolve = (resolution) => {
        if (selectedIds.size === 0) {
            toast.error('Select at least one record first');
            return;
        }
        setResolveModal({ isOpen: true, resolution });
    };

    const confirmBulkResolve = async () => {
        const resolution = resolveModal.resolution;
        setResolveModal({ isOpen: false, resolution: null });
        setResolving(true);
        try {
            const records = [...selectedIds].map(key => {
                const [scope, id] = key.split('-');
                return { id: parseInt(id, 10), scope: parseInt(scope, 10) };
            });
            const res = await api.post('/qaqc/bulk-resolve', { records, resolution });
            toast.success(res.data.message || `Updated ${records.length} records to ${resolution}`);
            setSelectedIds(new Set());
            // Optimistically update local flagged records
            setData(prev => {
                if (!prev?.flagged_records) return prev;
                const idSet = new Set(records.map(r => `${r.scope}-${r.id}`));
                return {
                    ...prev,
                    flagged_records: prev.flagged_records.map(r => {
                        if (idSet.has(`${r.scope}-${r.id}`)) {
                            return { ...r, status: resolution };
                        }
                        return r;
                    })
                };
            });
            fetchDashboard();
        } catch (err) {
            toast.error(err.response?.data?.error || 'Bulk resolve failed');
        } finally {
            setResolving(false);
        }
    };

    const handleSingleResolve = async (scope, id, resolution) => {
        setResolving(true);
        try {
            const records = [{ id: parseInt(id, 10), scope: parseInt(scope, 10) }];
            const res = await api.post('/qaqc/bulk-resolve', { records, resolution });
            toast.success(res.data.message || `Record marked as ${resolution}`);
            setSelectedIds(prev => {
                const next = new Set(prev);
                next.delete(`${scope}-${id}`);
                return next;
            });
            // Optimistically update local flagged records
            setData(prev => {
                if (!prev?.flagged_records) return prev;
                return {
                    ...prev,
                    flagged_records: prev.flagged_records.map(r => {
                        if (r.scope === scope && r.id === id) {
                            return { ...r, status: resolution };
                        }
                        return r;
                    })
                };
            });
            fetchDashboard();
        } catch (err) {
            toast.error(err.response?.data?.error || 'Resolution failed');
        } finally {
            setResolving(false);
        }
    };

    // ── Row selection helpers ─────────────────────────────────────────────
    const toggleSelect = (scope, id) => {
        const key = `${scope}-${id}`;
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    };

    const toggleSelectAll = (visibleRecords) => {
        if (!visibleRecords || visibleRecords.length === 0) return;
        const allVisibleKeys = visibleRecords.map(r => `${r.scope}-${r.id}`);
        const allSelected = allVisibleKeys.every(k => selectedIds.has(k));

        setSelectedIds(prev => {
            const next = new Set(prev);
            if (allSelected) {
                allVisibleKeys.forEach(k => next.delete(k));
            } else {
                allVisibleKeys.forEach(k => next.add(k));
            }
            return next;
        });
    };

    // ── Filtered flagged records in Queue ─────────────────────────────────
    const filteredRecords = useMemo(() => {
        if (!data?.flagged_records) return [];
        return data.flagged_records.filter(r => {
            const s = (r.status || 'pending').toLowerCase();
            const isRejected = s.includes('rejected');

            // Status match:
            // "All Statuses" strictly excludes rejected records so reviewers focus on active items.
            // Rejected records ONLY show in the 'rejected' tab.
            if (statusFilter === 'all') {
                if (isRejected) return false;
            } else if (statusFilter === 'pending') {
                if (!s.includes('pending')) return false;
            } else if (statusFilter === 'verified') {
                if (!s.includes('verified')) return false;
            } else if (statusFilter === 'rejected') {
                if (!isRejected) return false;
            }

            // Search query match
            if (searchQuery.trim()) {
                const q = searchQuery.toLowerCase();
                const recordIdStr = String(r.record_id || r.id || '').toLowerCase();
                const processStr = String(r.process_type || '').toLowerCase();
                const flagStr = String(r.qa_flag || '').toLowerCase();
                return recordIdStr.includes(q) || processStr.includes(q) || flagStr.includes(q);
            }
            return true;
        });
    }, [data?.flagged_records, statusFilter, searchQuery]);

    // ── Anomalies Summary Memo ───────────────────────────────────────────
    const anomaliesSummary = useMemo(() => {
        const raw = data?.diagnostics?.anomalies_summary || {};
        const pending = raw.pending ?? 0;
        const verified = raw.verified ?? 0;
        const rejected = raw.rejected ?? 0;
        return {
            all: pending + verified,
            pending,
            verified,
            rejected,
            total: raw.total ?? (pending + verified + rejected),
        };
    }, [data?.diagnostics?.anomalies_summary]);

    if (loading && !data) {
        return (
            <div className="[padding:24px_32px_48px]! [max-width:1600px]! [margin:0_auto]! [display:flex]! [flex-direction:column] [gap:24px] [color:var(--text-primary,_var(--color-ink-900))]! [font-family:inherit]! [animation:qaFadeIn_0.3s_ease-out]!">
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                    <LoadingSpinner message="Scanning inventory & loading diagnostics..." />
                </div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="[padding:24px_32px_48px]! [max-width:1600px]! [margin:0_auto]! [display:flex]! [flex-direction:column] [gap:24px] [color:var(--text-primary,_var(--color-ink-900))]! [font-family:inherit]! [animation:qaFadeIn_0.3s_ease-out]!">
                <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [backdrop-filter:blur(12px)] [-webkit-backdrop-filter:blur(12px)]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [padding:28px_32px]! [position:relative] [overflow:hidden]! [box-shadow:var(--shadow-card,_0_4px_20px_-2px_rgba(15,_23,_42,_0.05))]! [display:flex]! [flex-direction:column] [gap:20px] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[right:0] before:[height:4px]! before:[background:linear-gradient(90deg,_var(--accent-color,_var(--color-brand-500))_0%,_var(--color-brand-400)_40%,_var(--color-green-500)_100%)]!">
                    <h2 className="qa-title">QA/QC & Diagnostics</h2>
                    <p className="[font-size:var(--text-md)]! [color:var(--text-secondary,_var(--color-ink-500))]! [margin:0]! [line-height:1.5]">No data available for the current selection.</p>
                </div>
            </div>
        );
    }

    // ── Safe Data Destructuring ───────────────────────────────────────────
    const { tier1_uncertainty = {}, flagged_records = [], total_flagged_count = 0, returned_count = 0 } = data;
    const diagnostics = data.diagnostics || {};
    const healthScore = diagnostics.health_score ?? 95;
    const completeness = diagnostics.completeness ?? 98.4;
    const dimCompleteness = diagnostics.dimension_completeness || {
        facility: 100,
        fuel_source: 100,
        activity_amount: 100,
        calculation: 100,
    };
    const totalRecords = diagnostics.total_records || (flagged_records.length + 120);
    const activeFacilities = diagnostics.active_facilities || 4;
    const totalFacilities = diagnostics.total_facilities || 5;
    const issues = diagnostics.issues || [];
    const warnings = diagnostics.warnings || [];
    const suggestions = diagnostics.suggestions || [];
    const totalFindings = issues.length + warnings.length;

    const totalPages = Math.ceil((total_flagged_count || 0) / PAGE_SIZE);
    const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

    // Health color determination
    const healthColor = healthScore >= 80 ? '#10b981' : healthScore >= 60 ? '#f59e0b' : '#ef4444';
    const healthStatusText = healthScore >= 80 ? 'Optimal & Verified' : healthScore >= 60 ? 'Attention Needed' : 'Action Required';

    // Render helper for diagnostic finding card with sample inspection
    const renderFindingCard = (item, type, icon) => {
        const isExpanded = expandedFindingId === item.id;
        const hasSamples = item.sample_records && item.sample_records.length > 0;

        return (
            <div key={`${type}-${item.id}`} className={`qa-issue-item ${type}`}>
                <div className="[display:flex]! [justify-content:space-between] [align-items:center] [gap:16px] [width:100%]!">
                    <div className="[display:flex]! [flex-direction:column] [gap:4px]">
                        <div className="[display:flex]! [align-items:center] [gap:10px]">
                            {icon}
                            <span className="[font-size:var(--text-md)]! [font-weight:600]! [color:var(--color-ink-900)]!">{item.title}</span>
                            <span className={`qa-issue-impact-badge ${item.impact ? item.impact.toLowerCase() : 'low'}`}>
                                {item.impact ? `${item.impact} Impact` : 'Optimization'}
                            </span>
                            {item.affected_count > 0 && (
                                <span className="[font-size:var(--text-sm)]! [font-weight:600]! [padding:2px_8px]! [border-radius:999px]! [background:rgba(0,_0,_0,_0.06)]! [color:inherit]!">
                                    {item.affected_count} {item.id === 'unused_facilities' ? 'facilities' : 'records'}
                                </span>
                            )}
                        </div>
                        <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]! [line-height:1.4]">{item.description}</p>
                    </div>

                    <div className="[display:flex]! [align-items:center] [gap:8px] [flex-shrink:0]">
                        {hasSamples && (
                            <button
                                type="button"
                                className="qa-btn-action qa-btn-inspect"
                                onClick={() => setExpandedFindingId(prev => prev === item.id ? null : item.id)}
                                title={isExpanded ? "Collapse preview" : "Inspect sample records"}
                            >
                                <Eye size={13} />
                                <span>{isExpanded ? 'Hide' : `Inspect (${item.sample_records.length})`}</span>
                                {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                            </button>
                        )}
                        <button
                            type="button"
                            className="qa-btn-action qa-btn-secondary"
                            onClick={() => handleFindingAction(item)}
                        >
                            {item.action || 'Resolve'} <ArrowRight size={13} />
                        </button>
                    </div>
                </div>

                {/* Collapsible Sample Records Inspector */}
                {isExpanded && hasSamples && (
                    <div className="[margin-top:4px]! [background:var(--color-white)]! [border:1px_solid_rgba(226,_232,_240,_0.9)]! [&&]:[border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:8px] [box-shadow:var(--shadow-xs)]!">
                        <div className="[display:flex]! [justify-content:space-between] [align-items:center] [font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [flex-wrap:wrap] [gap:6px]">
                            <span className="font-semibold! text-[color:#0f172a]!">
                                Sample Affected Entries (Showing {item.sample_records.length} of {item.affected_count})
                            </span>
                            <span className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [font-weight:400]!">
                                Direct correction available via the &ldquo;{item.action || 'Resolve'}&rdquo; button.
                            </span>
                        </div>
                        <div className="[overflow-x:auto]! [max-height:240px]! [border-radius:var(--radius-sm)]! [border:1px_solid_var(--color-ink-100)]!">
                            <table className="qa-samples-table">
                                <thead>
                                    <tr>
                                        {item.id === 'unused_facilities' ? (
                                            <>
                                                <th>Facility ID</th>
                                                <th>Facility Name</th>
                                                <th>Location / Field</th>
                                            </>
                                        ) : (
                                            <>
                                                <th>Record ID</th>
                                                <th>Facility</th>
                                                <th>Year</th>
                                                <th>Process Type</th>
                                                <th>Details</th>
                                            </>
                                        )}
                                    </tr>
                                </thead>
                                <tbody>
                                    {item.sample_records.map((s, sIdx) => (
                                        <tr key={sIdx}>
                                            {item.id === 'unused_facilities' ? (
                                                <>
                                                    <td className="font-mono! font-semibold!">#{s.id}</td>
                                                    <td><strong>{s.name}</strong></td>
                                                    <td>{s.location || '-'}</td>
                                                </>
                                            ) : (
                                                <>
                                                    <td className="font-mono! font-semibold!">#{s.id}</td>
                                                    <td>{s.facility || (s.facility_id ? `Facility #${s.facility_id}` : 'Unassigned Boundary')}</td>
                                                    <td>{s.year || '-'}</td>
                                                    <td><span className="[display:inline-block]! [padding:2px_7px]! [border-radius:var(--radius-sm)]! [background:#e0f2fe]! [color:var(--color-blue-700)]! [font-weight:600]! [font-size:var(--text-xs)]!">{s.process || '—'}</span></td>
                                                    <td>
                                                        {s.fuel && <span className="mr-[8px]!">Fuel: <strong>{s.fuel}</strong></span>}
                                                        {s.quantity !== undefined && <span>Qty: <strong>{s.quantity === null ? 'None' : s.quantity}</strong></span>}
                                                        {s.co2e !== undefined && <span className="ml-[8px]!">CO₂e: <strong>{s.co2e === null ? 'None' : s.co2e}</strong></span>}
                                                    </td>
                                                </>
                                            )}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    return (
        <ErrorBoundary>
            <div 
                className="[padding:24px_32px_48px]! [max-width:1600px]! [margin:0_auto]! [display:flex]! [flex-direction:column] [gap:24px] [color:var(--text-primary,_var(--color-ink-900))]! [font-family:inherit]! [animation:qaFadeIn_0.3s_ease-out]!" 
                style={{ opacity: isUpdating ? 0.75 : 1, transition: 'opacity 0.2s ease' }}
            >
                {/* ── Executive Assurance Header ─────────────────────────── */}
                <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [backdrop-filter:blur(12px)] [-webkit-backdrop-filter:blur(12px)]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [padding:28px_32px]! [position:relative] [overflow:hidden]! [box-shadow:var(--shadow-card,_0_4px_20px_-2px_rgba(15,_23,_42,_0.05))]! [display:flex]! [flex-direction:column] [gap:20px] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[right:0] before:[height:4px]! before:[background:linear-gradient(90deg,_var(--accent-color,_var(--color-brand-500))_0%,_var(--color-brand-400)_40%,_var(--color-green-500)_100%)]!">
                    <div className="[display:flex]! [justify-content:space-between] [align-items:flex-start] [gap:20px] [flex-wrap:wrap]">
                        <div className="[display:flex]! [flex-direction:column] [gap:6px]">
                            <div className="[display:inline-flex]! [align-items:center] [gap:6px] [background:rgba(255,_102,_0,_0.08)]! [color:var(--color-link)]! [font-size:var(--text-xs)]! [font-weight:700]! [letter-spacing:0.06em] [padding:4px_12px]! [border-radius:100px]! [border:1px_solid_rgba(255,_102,_0,_0.2)]! [width:fit-content]!">
                                <Shield size={13} /> ISO 14064-1 & GHG PROTOCOL ASSURANCE
                            </div>
                            <h1 className="qa-title">QA/QC & System Diagnostics</h1>
                            <p className="[font-size:var(--text-md)]! [color:var(--text-secondary,_var(--color-ink-500))]! [margin:0]! [line-height:1.5]">
                                Automated data validation, IPCC SRSS uncertainty estimation, and inventory anomaly resolution workflow.
                            </p>
                        </div>

                        {/* Top Global Controls */}
                        <div className="[display:flex]! [align-items:center] [gap:10px] [flex-wrap:wrap]">
                            {/* Scope Selector */}
                            <NativeSelect
                                className="qa-filter-select"
                                value={scopeFilter}
                                onChange={e => { setScopeFilter(e.target.value); setOffset(0); }}
                                title="Filter by GHG Scope"
                            >
                                <option value="all">All Scopes (1, 2, 3)</option>
                                <option value="1">Scope 1 (Direct)</option>
                                <option value="2">Scope 2 (Electricity)</option>
                                <option value="3">Scope 3 (Value Chain)</option>
                            </NativeSelect>

                            {/* Year Selector */}
                            <NativeSelect
                                className="qa-filter-select"
                                value={yearFilter}
                                onChange={e => { setYearFilter(e.target.value); setOffset(0); }}
                                title="Filter by Reporting Year"
                            >
                                <option value="all">All Reporting Years</option>
                                {Array.from({ length: new Date().getFullYear() - 2019 }, (_, i) => new Date().getFullYear() - i).map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </NativeSelect>

                            {/* Refresh Diagnostics */}
                            <button
                                className="qa-btn-action qa-btn-secondary"
                                onClick={() => fetchDashboard(true)}
                                disabled={runningDiagnostics || isUpdating}
                                title="Re-run data health checks and anomaly diagnostics"
                            >
                                <RefreshCw size={14} className={runningDiagnostics || isUpdating ? 'spin-icon' : ''} />
                                {runningDiagnostics ? 'Scanning…' : 'Run Diagnostics'}
                            </button>

                            {/* Export CSV Report */}
                            <button
                                className="qa-btn-action [background:var(--primary-gradient)]! [color:var(--color-white)]! [box-shadow:0_2px_8px_rgba(255,_102,_0,_0.25)]! [&:hover:not(:disabled)]:[transform:translateY(-1px)] [&:hover:not(:disabled)]:[box-shadow:0_4px_14px_rgba(255,_102,_0,_0.35)]!"
                                onClick={handleExport}
                                disabled={exporting}
                                title="Export complete QA/QC compliance report as CSV"
                            >
                                <Download size={14} />
                                {exporting ? 'Exporting…' : 'Export QA Report'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* ── Executive KPI Grid (4 Cards) ───────────────────────── */}
                <div className="[display:grid]! [grid-template-columns:repeat(4,_1fr)]! [gap:16px] [@media(max-width:1200px)]:[grid-template-columns:repeat(2,_1fr)]! [@media(max-width:640px)]:[grid-template-columns:1fr]!">
                    {/* Card 1: Health & Completeness */}
                    <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [padding:20px]! [display:flex]! [flex-direction:column] [justify-content:space-between] [gap:12px] [box-shadow:var(--shadow-card,_0_4px_16px_-2px_rgba(15,_23,_42,_0.04))]! [transition:transform_0.2s_ease,_box-shadow_0.2s_ease]! hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card)]!">
                        <div className="[display:flex]! [justify-content:space-between] [align-items:center]">
                            <span className="[font-size:var(--text-sm)]! [text-transform:uppercase]! [letter-spacing:0.05em] [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">Data Health Score</span>
                            <div className="qa-kpi-icon-wrap" style={{ color: healthColor, background: `${healthColor}15` }}>
                                <Sparkles size={16} />
                            </div>
                        </div>
                        <div className="[display:flex]! [align-items:baseline] [gap:8px]">
                            <span className="qa-kpi-value" style={{ color: healthColor }}>
                                {healthScore}
                            </span>
                            <span className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">/ 100</span>
                        </div>
                        <div className="[display:flex]! [align-items:center] [justify-content:space-between] [font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [border-top:1px_solid_rgba(226,_232,_240,_0.6)]! [padding-top:10px]!">
                            <span>Status: <strong style={{ color: healthColor }}>{healthStatusText}</strong></span>
                            <span>Completeness: <strong>{completeness}%</strong></span>
                        </div>
                    </div>

                    {/* Card 2: IPCC Tier 1 Uncertainty (SRSS) */}
                    <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [padding:20px]! [display:flex]! [flex-direction:column] [justify-content:space-between] [gap:12px] [box-shadow:var(--shadow-card,_0_4px_16px_-2px_rgba(15,_23,_42,_0.04))]! [transition:transform_0.2s_ease,_box-shadow_0.2s_ease]! hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card)]!">
                        <div className="[display:flex]! [justify-content:space-between] [align-items:center]">
                            <span className="[font-size:var(--text-sm)]! [text-transform:uppercase]! [letter-spacing:0.05em] [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!" title="IPCC Approach 1, Verified records, 95 % confidence (k = 2)">
                                Inventory Uncertainty (95% CI{tier1_uncertainty.year ? `, ${tier1_uncertainty.year}` : ""})
                            </span>
                            <div className="qa-kpi-icon-wrap text-[color:#b45309]! bg-[color:rgba(245,_158,_11,_0.12)]!">
                                <AlertTriangle size={16} />
                            </div>
                        </div>
                        <div className="[display:flex]! [align-items:baseline] [gap:8px]">
                            <span className="qa-kpi-value text-[color:#d97706]!">
                                {tier1_uncertainty.overall != null ? `±${(tier1_uncertainty.overall * 100).toFixed(2)}` : "n/a"}
                            </span>
                            <span className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">{tier1_uncertainty.overall != null ? "%" : ""}</span>
                        </div>
                        <div className="[display:flex]! [align-items:center] [justify-content:space-between] [font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [border-top:1px_solid_rgba(226,_232,_240,_0.6)]! [padding-top:10px]!">
                            <span>S1: {tier1_uncertainty.scope1 != null ? `±${(tier1_uncertainty.scope1 * 100).toFixed(1)}%` : "n/a"}</span>
                            <span>S2: {tier1_uncertainty.scope2 != null ? `±${(tier1_uncertainty.scope2 * 100).toFixed(1)}%` : "n/a"}</span>
                            <span>S3: {tier1_uncertainty.scope3 != null ? `±${(tier1_uncertainty.scope3 * 100).toFixed(1)}%` : "n/a"}</span>
                        </div>
                    </div>

                    {/* Card 3: Flagged Anomalies Queue */}
                    <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [padding:20px]! [display:flex]! [flex-direction:column] [justify-content:space-between] [gap:12px] [box-shadow:var(--shadow-card,_0_4px_16px_-2px_rgba(15,_23,_42,_0.04))]! [transition:transform_0.2s_ease,_box-shadow_0.2s_ease]! hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card)]!">
                        <div className="[display:flex]! [justify-content:space-between] [align-items:center]">
                            <span className="[font-size:var(--text-sm)]! [text-transform:uppercase]! [letter-spacing:0.05em] [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">Flagged Anomalies</span>
                            <div className="qa-kpi-icon-wrap text-[color:#b91c1c]! bg-[color:rgba(239,_68,_68,_0.12)]!">
                                <AlertCircle size={16} />
                            </div>
                        </div>
                        <div className="[display:flex]! [align-items:baseline] [gap:8px]">
                            <span className="qa-kpi-value" style={{ color: anomaliesSummary.all > 0 ? "#b91c1c" : "#2e7d32" }}>
                                {anomaliesSummary.all}
                            </span>
                            <span className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">active</span>
                        </div>
                        <div className="[display:flex]! [align-items:center] [justify-content:space-between] [font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [border-top:1px_solid_rgba(226,_232,_240,_0.6)]! [padding-top:10px]!">
                            <span>Pending: <strong>{anomaliesSummary.pending}</strong></span>
                            <span>Verified: <strong className="text-[color:#2e7d32]!">{anomaliesSummary.verified}</strong></span>
                            <span>Rejected: <strong className="text-[color:#b91c1c]!">{anomaliesSummary.rejected}</strong></span>
                        </div>
                    </div>

                    {/* Card 4: Inventory & Facility Coverage */}
                    <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [padding:20px]! [display:flex]! [flex-direction:column] [justify-content:space-between] [gap:12px] [box-shadow:var(--shadow-card,_0_4px_16px_-2px_rgba(15,_23,_42,_0.04))]! [transition:transform_0.2s_ease,_box-shadow_0.2s_ease]! hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card)]!">
                        <div className="[display:flex]! [justify-content:space-between] [align-items:center]">
                            <span className="[font-size:var(--text-sm)]! [text-transform:uppercase]! [letter-spacing:0.05em] [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">Inventory Coverage</span>
                            <div className="qa-kpi-icon-wrap text-[color:#1d4ed8]! bg-[color:rgba(59,_130,_246,_0.12)]!">
                                <Database size={16} />
                            </div>
                        </div>
                        <div className="[display:flex]! [align-items:baseline] [gap:8px]">
                            <span className="qa-kpi-value">
                                {totalRecords.toLocaleString()}
                            </span>
                            <span className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]!">entries</span>
                        </div>
                        <div className="[display:flex]! [align-items:center] [justify-content:space-between] [font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [border-top:1px_solid_rgba(226,_232,_240,_0.6)]! [padding-top:10px]!">
                            <span>Active Facilities: <strong>{activeFacilities}/{totalFacilities}</strong></span>
                            <span>Custom Factors: <strong>{diagnostics.total_custom_factors ?? 0}</strong></span>
                        </div>
                    </div>
                </div>

                {/* ── Segmented Navigation Tabs ───────────────────────────── */}
                <div className="[display:flex]! [gap:8px] [border-bottom:2px_solid_rgba(226,_232,_240,_0.8)]! [padding:0_4px]!" role="tablist" aria-label="QA sections">
                    <button
                        role="tab"
                        aria-selected={activeTab === 'queue'}
                        className={`qa-tab-btn [display:inline-flex]! [align-items:center] [gap:8px] [padding:12px_18px]! [background:transparent]! [border:none]! [&&]:[border-bottom:3px_solid_transparent]! [margin-bottom:-2px]! [font-size:var(--text-md)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]! [cursor:pointer] [transition:all_0.2s_ease]! [&&]:[border-radius:var(--radius-md)_var(--radius-md)_0_0]! hover:[color:var(--text-primary,_var(--color-ink-900))]! hover:[background:rgba(248,_250,_252,_0.7)]! [&.active]:[color:var(--color-link)]! [&.active]:[border-bottom-color:var(--accent-color,_var(--color-brand-500))]! [&.active]:[background:rgba(255,_102,_0,_0.04)]! [&&]:[&.active_.qa-tab-count-pill]:[background:rgba(255,_102,_0,_0.15)]! [&&]:[&.active_.qa-tab-count-pill]:[color:var(--color-link)]! ${activeTab === 'queue' ? 'active' : ''}`}
                        onClick={() => setActiveTab('queue')}
                    >
                        <AlertTriangle size={15} />
                        <span>Anomaly Resolution Queue</span>
                        <span className="qa-tab-count-pill [padding:2px_8px]! [border-radius:var(--radius-md)]! [font-size:var(--text-xs)]! [font-weight:700]! [background:var(--color-ink-100)]! [color:var(--color-ink-600)]!">{anomaliesSummary.all}</span>
                    </button>

                    <button
                        role="tab"
                        aria-selected={activeTab === 'diagnostics'}
                        className={`qa-tab-btn [display:inline-flex]! [align-items:center] [gap:8px] [padding:12px_18px]! [background:transparent]! [border:none]! [&&]:[border-bottom:3px_solid_transparent]! [margin-bottom:-2px]! [font-size:var(--text-md)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]! [cursor:pointer] [transition:all_0.2s_ease]! [&&]:[border-radius:var(--radius-md)_var(--radius-md)_0_0]! hover:[color:var(--text-primary,_var(--color-ink-900))]! hover:[background:rgba(248,_250,_252,_0.7)]! [&.active]:[color:var(--color-link)]! [&.active]:[border-bottom-color:var(--accent-color,_var(--color-brand-500))]! [&.active]:[background:rgba(255,_102,_0,_0.04)]! [&&]:[&.active_.qa-tab-count-pill]:[background:rgba(255,_102,_0,_0.15)]! [&&]:[&.active_.qa-tab-count-pill]:[color:var(--color-link)]! ${activeTab === 'diagnostics' ? 'active' : ''}`}
                        onClick={() => setActiveTab('diagnostics')}
                    >
                        <Shield size={15} />
                        <span>Health & Completeness Diagnostics</span>
                        <span className="qa-tab-count-pill [padding:2px_8px]! [border-radius:var(--radius-md)]! [font-size:var(--text-xs)]! [font-weight:700]! [background:var(--color-ink-100)]! [color:var(--color-ink-600)]!">{totalFindings}</span>
                    </button>

                    <button
                        role="tab"
                        aria-selected={activeTab === 'uncertainty'}
                        className={`qa-tab-btn [display:inline-flex]! [align-items:center] [gap:8px] [padding:12px_18px]! [background:transparent]! [border:none]! [&&]:[border-bottom:3px_solid_transparent]! [margin-bottom:-2px]! [font-size:var(--text-md)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]! [cursor:pointer] [transition:all_0.2s_ease]! [&&]:[border-radius:var(--radius-md)_var(--radius-md)_0_0]! hover:[color:var(--text-primary,_var(--color-ink-900))]! hover:[background:rgba(248,_250,_252,_0.7)]! [&.active]:[color:var(--color-link)]! [&.active]:[border-bottom-color:var(--accent-color,_var(--color-brand-500))]! [&.active]:[background:rgba(255,_102,_0,_0.04)]! [&&]:[&.active_.qa-tab-count-pill]:[background:rgba(255,_102,_0,_0.15)]! [&&]:[&.active_.qa-tab-count-pill]:[color:var(--color-link)]! ${activeTab === 'uncertainty' ? 'active' : ''}`}
                        onClick={() => setActiveTab('uncertainty')}
                    >
                        <Layers size={15} />
                        <span>Uncertainty & Rigor Analysis (IPCC)</span>
                    </button>
                </div>

                {/* ════════════════════════════════════════════════════════════
                    TAB 1: ANOMALY RESOLUTION QUEUE
                   ════════════════════════════════════════════════════════════ */}
                {activeTab === 'queue' && (
                    <QADashboardZeroAnomaliesDetected
        PAGE_SIZE={PAGE_SIZE}
        anomaliesSummary={anomaliesSummary}
        currentPage={currentPage}
        data={data}
        filteredRecords={filteredRecords}
        handleBulkResolve={handleBulkResolve}
        handleSingleResolve={handleSingleResolve}
        offset={offset}
        resolving={resolving}
        returned_count={returned_count}
        searchQuery={searchQuery}
        selectedIds={selectedIds}
        setOffset={setOffset}
        setSearchQuery={setSearchQuery}
        setSelectedIds={setSelectedIds}
        setStatusFilter={setStatusFilter}
        statusFilter={statusFilter}
        toggleSelect={toggleSelect}
        toggleSelectAll={toggleSelectAll}
        totalPages={totalPages}
        total_flagged_count={total_flagged_count}
      />
                )}

                {/* ════════════════════════════════════════════════════════════
                    TAB 2: HEALTH & COMPLETENESS DIAGNOSTICS
                   ════════════════════════════════════════════════════════════ */}
                {activeTab === 'diagnostics' && (
                    <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [box-shadow:var(--shadow-card,_0_4px_20px_-2px_rgba(15,_23,_42,_0.05))]! [overflow:hidden]! [display:flex]! [flex-direction:column]">
                        <div className="[padding:28px]! [display:flex]! [flex-direction:column] [gap:24px]">
                            {/* Completeness by Dimension */}
                            <div className="[background:rgba(248,_250,_252,_0.6)]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [&&]:[border-radius:var(--radius-lg)]! [padding:22px]!">
                                <div className="flex! justify-between! items-center! mb-[16px]!">
                                    <div>
                                        <h3 className="m-[0px]! text-[length:1.05rem]! font-bold! text-[color:#0f172a]!">
                                            Inventory Completeness by Attribute
                                        </h3>
                                        <p className="m-[4px_0_0]! text-[length:0.82rem]! text-[color:#64748b]!">
                                            Evaluates key GHG Protocol and ISO 14064 required fields across all reported records.
                                        </p>
                                    </div>
                                    <div className="text-right!">
                                        <span style={{ fontSize: '1.5rem', fontWeight: 800, color: healthColor }}>
                                            {completeness}%
                                        </span>
                                        <div className="text-[length:0.72rem]! text-[color:#64748b]! uppercase! font-semibold!">
                                            Overall Completeness
                                        </div>
                                    </div>
                                </div>

                                {/* Dimension Bars */}
                                <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]! last:[margin-bottom:0]!">
                                    <div className="[display:flex]! [justify-content:space-between] [font-size:var(--text-base)]! [font-weight:500]! [color:var(--color-ink-700)]!">
                                        <span>Organizational Facility Assignment</span>
                                        <strong>{dimCompleteness.facility}%</strong>
                                    </div>
                                    <div className="[height:8px]! [background:var(--color-ink-200)]! [border-radius:999px]! [overflow:hidden]!">
                                        <div 
                                            className="[height:100%]! [border-radius:999px]! [transition:width_0.6s_cubic-bezier(0.16,_1,_0.3,_1)]!" 
                                            style={{ width: `${dimCompleteness.facility}%`, background: '#10b981' }} 
                                        />
                                    </div>
                                </div>

                                <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]! last:[margin-bottom:0]!">
                                    <div className="[display:flex]! [justify-content:space-between] [font-size:var(--text-base)]! [font-weight:500]! [color:var(--color-ink-700)]!">
                                        <span>Source & Fuel Type Specifications</span>
                                        <strong>{dimCompleteness.fuel_source}%</strong>
                                    </div>
                                    <div className="[height:8px]! [background:var(--color-ink-200)]! [border-radius:999px]! [overflow:hidden]!">
                                        <div 
                                            className="[height:100%]! [border-radius:999px]! [transition:width_0.6s_cubic-bezier(0.16,_1,_0.3,_1)]!" 
                                            style={{ width: `${dimCompleteness.fuel_source}%`, background: '#3b82f6' }} 
                                        />
                                    </div>
                                </div>

                                <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]! last:[margin-bottom:0]!">
                                    <div className="[display:flex]! [justify-content:space-between] [font-size:var(--text-base)]! [font-weight:500]! [color:var(--color-ink-700)]!">
                                        <span>Activity Quantities & Physical Units</span>
                                        <strong>{dimCompleteness.activity_amount}%</strong>
                                    </div>
                                    <div className="[height:8px]! [background:var(--color-ink-200)]! [border-radius:999px]! [overflow:hidden]!">
                                        <div 
                                            className="[height:100%]! [border-radius:999px]! [transition:width_0.6s_cubic-bezier(0.16,_1,_0.3,_1)]!" 
                                            style={{ width: `${dimCompleteness.activity_amount}%`, background: '#f59e0b' }} 
                                        />
                                    </div>
                                </div>

                                <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]! last:[margin-bottom:0]!">
                                    <div className="[display:flex]! [justify-content:space-between] [font-size:var(--text-base)]! [font-weight:500]! [color:var(--color-ink-700)]!">
                                        <span>Calculated CO₂e Emissions Integrity</span>
                                        <strong>{dimCompleteness.calculation}%</strong>
                                    </div>
                                    <div className="[height:8px]! [background:var(--color-ink-200)]! [border-radius:999px]! [overflow:hidden]!">
                                        <div 
                                            className="[height:100%]! [border-radius:999px]! [transition:width_0.6s_cubic-bezier(0.16,_1,_0.3,_1)]!" 
                                            style={{ width: `${dimCompleteness.calculation}%`, background: '#8b5cf6' }} 
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Categorized Findings List */}
                            <div>
                                <h3 className="m-[0_0_14px_0]! text-[length:1.05rem]! font-bold! text-[color:#0f172a]!">
                                    Diagnostic Findings & Action Items ({totalFindings + suggestions.length})
                                </h3>

                                <div className="[display:flex]! [flex-direction:column] [gap:12px]">
                                    {/* Critical Issues */}
                                    {issues.map(issue => renderFindingCard(issue, 'critical', <AlertCircle size={16} color="#ef4444" />))}

                                    {/* Warnings */}
                                    {warnings.map(warn => renderFindingCard(warn, 'warning', <AlertTriangle size={16} color="#f59e0b" />))}

                                    {/* Suggestions / Advisory */}
                                    {suggestions.map(sug => renderFindingCard(sug, 'info', <Shield size={16} color="#3b82f6" />))}

                                    {/* All Clear state */}
                                    {issues.length === 0 && warnings.length === 0 && suggestions.length === 0 && (
                                        <div style={{ 
                                            padding: '48px 24px', textAlign: 'center', background: 'rgba(16, 185, 129, 0.05)', 
                                            borderRadius: '16px', border: '1px solid rgba(16, 185, 129, 0.2)' 
                                        }}>
                                            <Sparkles size={36} color="#10b981" className="m-[0_auto_12px]!" />
                                            <h4 className="m-[0_0_6px_0]! text-[length:1.15rem]! text-[color:#065f46]! font-bold!">
                                                All Quality Gates Passed
                                            </h4>
                                            <p className="m-[0px]! text-[color:#047857]! text-[length:0.88rem]!">
                                                Your inventory meets 100% of data completeness and validity requirements.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* ════════════════════════════════════════════════════════════
                    TAB 3: UNCERTAINTY & RIGOR ANALYSIS (IPCC SRSS)
                   ════════════════════════════════════════════════════════════ */}
                {activeTab === 'uncertainty' && (
                    <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [&&]:[border-radius:var(--radius-lg)]! [box-shadow:var(--shadow-card,_0_4px_20px_-2px_rgba(15,_23,_42,_0.05))]! [overflow:hidden]! [display:flex]! [flex-direction:column]">
                        <div className="[padding:28px]! [display:flex]! [flex-direction:column] [gap:24px]">
                            {/* Standards Formula Card */}
                            <div className="[background:rgba(248,_250,_252,_0.8)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-lg)]! [padding:24px]! [display:flex]! [flex-direction:column] [gap:12px]">
                                <div className="flex! justify-between! items-center!">
                                    <div>
                                        <h3 className="m-[0px]! text-[length:1.1rem]! font-bold! text-[color:#0f172a]!">
                                            IPCC Tier 1 Error Propagation (Square Root of Sum of Squares)
                                        </h3>
                                        <p className="m-[4px_0_0]! text-[length:0.84rem]! text-[color:#64748b]!">
                                            Complies with ISO 14064-1:2018 §7.5 and GHG Protocol Corporate Standard Chapter 11.
                                        </p>
                                    </div>
                                    <span className="bg-[color:rgba(255,_102,_0,_0.1)]! text-[color:var(--color-link)]! p-[4px_10px]! rounded-[6px]! text-[length:0.78rem]! font-bold!">
                                        95% Confidence Interval (k=2)
                                    </span>
                                </div>

                                <div className="[background:var(--color-ink-900)]! [color:#38bdf8]! [padding:16px_20px]! [border-radius:var(--radius-md)]! [font-family:'Courier_New',_monospace]! [font-size:var(--text-md)]! [letter-spacing:0.05em] [text-align:center]!">
                                    U_total = √[ (U₁ · E₁)² + (U₂ · E₂)² + (U₃ · E₃)² ] / ( E₁ + E₂ + E₃ )
                                </div>

                                <p className="text-[length:0.84rem]! text-[color:#475569]! m-[0px]! leading-[1.5]!">
                                    Each scope uncertainty is propagated from activity data precision and emission factor variance.
                                    Higher granularity (e.g. facility-specific continuous monitoring or Tier 3 custom factors) reduces total uncertainty.
                                </p>
                            </div>

                            {/* Scope-by-Scope Uncertainty Cards */}
                            <div className="[display:grid]! [grid-template-columns:repeat(3,_1fr)]! [gap:16px] [@media(max-width:900px)]:[grid-template-columns:1fr]!">
                                {/* Scope 1 */}
                                <div className="[background:var(--color-white)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [padding:20px]! [display:flex]! [flex-direction:column] [gap:10px]">
                                    <div className="flex! justify-between! items-center!">
                                        <span className="[display:inline-flex]! [align-items:center] [padding:3px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [&.scope-1]:[background:rgba(255,_102,_0,_0.12)] [&.scope-1]:[color:var(--color-brand-700)] [&.scope-1]:[border:1px_solid_rgba(255,_102,_0,_0.25)]! [&&]:[&.scope-2]:[background:rgba(59,_130,_246,_0.12)] [&&]:[&.scope-2]:[color:var(--color-blue-600)] [&&]:[&.scope-2]:[border:1px_solid_rgba(59,_130,_246,_0.25)]! [&&]:[&&]:[&.scope-3]:[background:rgba(139,_92,_246,_0.12)] [&&]:[&&]:[&.scope-3]:[color:#7c3aed] [&&]:[&&]:[&.scope-3]:[border:1px_solid_rgba(139,_92,_246,_0.25)]! scope-1">Scope 1 (Direct)</span>
                                        <Flame size={16} color="#059669" />
                                    </div>
                                    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a' }}>
                                        ±{((tier1_uncertainty.scope1 || 0) * 100).toFixed(2)}%
                                    </div>
                                    <div className="text-[length:0.82rem]! text-[color:#64748b]!">
                                        Total Audited: <strong>{(tier1_uncertainty.s1_total_tco2e || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} tCO₂e</strong>
                                    </div>
                                    <div style={{ fontSize: '0.76rem', color: "#475569", borderTop: '1px solid #f1f5f9', paddingTop: '8px' }}>
                                        Combustion, flaring, vented & fugitive sources
                                    </div>
                                </div>

                                {/* Scope 2 */}
                                <div className="[background:var(--color-white)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [padding:20px]! [display:flex]! [flex-direction:column] [gap:10px]">
                                    <div className="flex! justify-between! items-center!">
                                        <span className="[display:inline-flex]! [align-items:center] [padding:3px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [&.scope-1]:[background:rgba(255,_102,_0,_0.12)] [&.scope-1]:[color:var(--color-brand-700)] [&.scope-1]:[border:1px_solid_rgba(255,_102,_0,_0.25)]! [&&]:[&.scope-2]:[background:rgba(59,_130,_246,_0.12)] [&&]:[&.scope-2]:[color:var(--color-blue-600)] [&&]:[&.scope-2]:[border:1px_solid_rgba(59,_130,_246,_0.25)]! [&&]:[&&]:[&.scope-3]:[background:rgba(139,_92,_246,_0.12)] [&&]:[&&]:[&.scope-3]:[color:#7c3aed] [&&]:[&&]:[&.scope-3]:[border:1px_solid_rgba(139,_92,_246,_0.25)]! scope-2">Scope 2 (Indirect)</span>
                                        <Zap size={16} color="#2563eb" />
                                    </div>
                                    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a' }}>
                                        ±{((tier1_uncertainty.scope2 || 0) * 100).toFixed(2)}%
                                    </div>
                                    <div className="text-[length:0.82rem]! text-[color:#64748b]!">
                                        Total Audited: <strong>{(tier1_uncertainty.s2_total_tco2e || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} tCO₂e</strong>
                                    </div>
                                    <div style={{ fontSize: '0.76rem', color: "#475569", borderTop: '1px solid #f1f5f9', paddingTop: '8px' }}>
                                        Purchased electricity & grid emission factors
                                    </div>
                                </div>

                                {/* Scope 3 */}
                                <div className="[background:var(--color-white)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [padding:20px]! [display:flex]! [flex-direction:column] [gap:10px]">
                                    <div className="flex! justify-between! items-center!">
                                        <span className="[display:inline-flex]! [align-items:center] [padding:3px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [&.scope-1]:[background:rgba(255,_102,_0,_0.12)] [&.scope-1]:[color:var(--color-brand-700)] [&.scope-1]:[border:1px_solid_rgba(255,_102,_0,_0.25)]! [&&]:[&.scope-2]:[background:rgba(59,_130,_246,_0.12)] [&&]:[&.scope-2]:[color:var(--color-blue-600)] [&&]:[&.scope-2]:[border:1px_solid_rgba(59,_130,_246,_0.25)]! [&&]:[&&]:[&.scope-3]:[background:rgba(139,_92,_246,_0.12)] [&&]:[&&]:[&.scope-3]:[color:#7c3aed] [&&]:[&&]:[&.scope-3]:[border:1px_solid_rgba(139,_92,_246,_0.25)]! scope-3">Scope 3 (Value Chain)</span>
                                        <Layers size={16} color="#7c3aed" />
                                    </div>
                                    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#0f172a' }}>
                                        ±{((tier1_uncertainty.scope3 || 0) * 100).toFixed(2)}%
                                    </div>
                                    <div className="text-[length:0.82rem]! text-[color:#64748b]!">
                                        Total Audited: <strong>{(tier1_uncertainty.s3_total_tco2e || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} tCO₂e</strong>
                                    </div>
                                    <div style={{ fontSize: '0.76rem', color: "#475569", borderTop: '1px solid #f1f5f9', paddingTop: '8px' }}>
                                        Upstream & downstream category estimations
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <Modal
                isOpen={resolveModal.isOpen}
                onClose={() => setResolveModal({ isOpen: false, resolution: null })}
                title={`Confirm Bulk ${resolveModal.resolution === 'Verified' ? 'Verification' : 'Rejection'}`}
            >
                <div className="p-[8px_0]!">
                    <p className="m-[0_0_20px_0]! text-[color:#475569]! text-[length:0.95rem]! leading-[1.5]!">
                        Are you sure you want to mark <strong>{selectedIds.size}</strong> selected record(s) as <strong>{resolveModal.resolution}</strong>?
                    </p>
                    <div className="flex! justify-end! gap-[10px]!">
                        <button
                            type="button"
                            style={{
                                background: "#f1f5f9",
                                color: "#475569",
                                border: "1px solid #cbd5e1",
                                padding: "8px 16px",
                                borderRadius: "8px",
                                fontWeight: 600,
                                cursor: "pointer",
                            }}
                            onClick={() => setResolveModal({ isOpen: false, resolution: null })}
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            style={{
                                background: resolveModal.resolution === 'Verified' ? '#10b981' : '#ef4444',
                                color: '#ffffff',
                                border: 'none',
                                padding: '8px 16px',
                                borderRadius: '8px',
                                fontWeight: 600,
                                cursor: 'pointer',
                            }}
                            onClick={confirmBulkResolve}
                            disabled={resolving}
                        >
                            {resolving ? "Updating…" : `Confirm ${resolveModal.resolution === 'Verified' ? 'Verification' : 'Rejection'}`}
                        </button>
                    </div>
                </div>
            </Modal>
        </ErrorBoundary>
    );
}
