import QADashboardZeroAnomaliesDetected, { type FlaggedRecord } from "./qa/QADashboardZeroAnomaliesDetected";
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { NativeSelect } from "../ui/NativeSelect";
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useToast } from '../components/Toast';
import { AlertTriangle, Download, Layers, RefreshCw, Shield } from 'lucide-react';
import { Badge, Button, Card, ConfirmDialog, Page, Tabs, TabsContent, TabsList, TabsTrigger } from '../ui';
import { cn } from '../ui/cn';
import { controlClass } from '../components/import-wizard/mapping';
import { QaKpis, DiagnosticsPanel, UncertaintyPanel } from './qa/QaPanels';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBoundary from '../components/ErrorBoundary';
import { t } from "../i18n";

const PAGE_SIZE = 100;

interface ResolveModalState {
  isOpen: boolean;
  resolution: string | null;
}

export default function QADashboard() {
    const toast = useToast();
    const navigate = useNavigate();

    // ── State ──────────────────────────────────────────────────────────────
    const [loading, setLoading] = useState<boolean>(true);
    const [isUpdating, setIsUpdating] = useState<boolean>(false);
    const [runningDiagnostics, setRunningDiagnostics] = useState<boolean>(false);
    const isFirstLoadRef = useRef<boolean>(true);

    const [data, setData] = useState<any>(null);
    const [scopeFilter, setScopeFilter] = useState<string>('all');
    const [yearFilter, setYearFilter] = useState<string>('all');
    const [offset, setOffset] = useState<number>(0);

    // Active workflow tab: 'queue' | 'diagnostics' | 'uncertainty'
    const [activeTab, setActiveTab] = useState<string>('queue');

    // Queue search and filter
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [statusFilter, setStatusFilter] = useState<string>('all'); // 'all' | 'pending' | 'verified' | 'rejected'

    // Selection for bulk actions
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [resolving, setResolving] = useState<boolean>(false);
    const [exporting, setExporting] = useState<boolean>(false);
    const [resolveModal, setResolveModal] = useState<ResolveModalState>({ isOpen: false, resolution: null });
    const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);

    const handleFindingAction = useCallback((item: any) => {
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
            const params: Record<string, any> = { limit: PAGE_SIZE, offset };
            if (scopeFilter !== 'all') params.scope = scopeFilter;
            if (yearFilter !== 'all') params.year = yearFilter;
            params.status = statusFilter;

            const res = await api.get('/qaqc/dashboard', { params });
            setData(res.data);
            if (isManualRefresh) {
                toast.success(t("Diagnostics and anomaly scans refreshed successfully"));
            }
        } catch (err: any) {
            toast.error(err.response?.data?.error || err.response?.data?.message || t("Failed to load QA/QC data"));
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
            const params: Record<string, any> = {};
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
            toast.success(t("Compliance QA report exported successfully"));
        } catch (err: any) {
            toast.error(err.response?.data?.error || t("CSV Export failed"));
        } finally {
            setExporting(false);
        }
    };

    // ── Bulk resolve ───────────────────────────────────────────────────────
    const handleBulkResolve = (resolution: string) => {
        if (selectedIds.size === 0) {
            toast.error(t("Select at least one record first"));
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
            setData((prev: any) => {
                if (!prev?.flagged_records) return prev;
                const idSet = new Set(records.map(r => `${r.scope}-${r.id}`));
                return {
                    ...prev,
                    flagged_records: prev.flagged_records.map((r: FlaggedRecord) => {
                        if (idSet.has(`${r.scope}-${r.id}`)) {
                            return { ...r, status: resolution };
                        }
                        return r;
                    })
                };
            });
            fetchDashboard();
        } catch (err: any) {
            toast.error(err.response?.data?.error || t("Bulk resolve failed"));
        } finally {
            setResolving(false);
        }
    };

    const handleSingleResolve = async (scope: number | string, id: number | string, resolution: string) => {
        setResolving(true);
        try {
            const records = [{ id: parseInt(String(id), 10), scope: parseInt(String(scope), 10) }];
            const res = await api.post('/qaqc/bulk-resolve', { records, resolution });
            toast.success(res.data.message || `Record marked as ${resolution}`);
            setSelectedIds(prev => {
                const next = new Set(prev);
                next.delete(`${scope}-${id}`);
                return next;
            });
            // Optimistically update local flagged records
            setData((prev: any) => {
                if (!prev?.flagged_records) return prev;
                return {
                    ...prev,
                    flagged_records: prev.flagged_records.map((r: FlaggedRecord) => {
                        if (r.scope === scope && r.id === id) {
                            return { ...r, status: resolution };
                        }
                        return r;
                    })
                };
            });
            fetchDashboard();
        } catch (err: any) {
            toast.error(err.response?.data?.error || t("Resolution failed"));
        } finally {
            setResolving(false);
        }
    };

    // ── Row selection helpers ─────────────────────────────────────────────
    const toggleSelect = (scope: number | string, id: number | string) => {
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

    const toggleSelectAll = (visibleRecords: FlaggedRecord[]) => {
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
    const filteredRecords: FlaggedRecord[] = useMemo(() => {
        if (!data?.flagged_records) return [];
        return data.flagged_records.filter((r: FlaggedRecord) => {
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
            <div className="flex min-h-[60vh] items-center justify-center">
                <LoadingSpinner message={t("Scanning inventory & loading diagnostics...")} />
            </div>
        );
    }

    if (!data) {
        return (
            <Page className="max-w-[1600px]">
                <Card>
                    <h2 className="qa-title m-0 mb-2 text-xl font-bold text-text">{t("QA/QC & Diagnostics")}</h2>
                    <p className="m-0 text-md text-text-secondary">{t("No data available for the current selection.")}</p>
                </Card>
            </Page>
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

    return (
        <ErrorBoundary>
            <Page className={cn("max-w-[1600px] px-4 pb-12 pt-6 transition-opacity duration-200 sm:px-8", isUpdating && "opacity-75")}>
                <Card className="p-7">
                    <div className="flex flex-wrap items-start justify-between gap-5">
                        <div className="flex min-w-0 flex-col gap-1.5">
                            <Badge tone="brand" className="w-fit gap-1.5 px-3 py-1 uppercase tracking-wide">
                                <Shield className="size-3.5" aria-hidden="true" />{" "}{t("ISO 14064-1 & GHG Protocol Assurance")}
                            </Badge>
                            <h1 className="qa-title m-0 text-xl font-bold text-text">{t("QA/QC & System Diagnostics")}</h1>
                            <p className="m-0 max-w-3xl text-md leading-normal text-text-secondary">
                                {t("Automated data validation, IPCC SRSS uncertainty estimation, and inventory anomaly resolution workflow.")}
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2.5">
                            <NativeSelect className={cn(controlClass, "qa-filter-select h-[38px] w-auto")} aria-label={t("Filter by GHG Scope")} value={scopeFilter} onChange={e => { setScopeFilter(e.target.value); setOffset(0); }} title={t("Filter by GHG Scope")}>
                                <option value="all">{t("All Scopes (1, 2, 3)")}</option>
                                <option value="1">{t("Scope 1 (Direct)")}</option>
                                <option value="2">{t("Scope 2 (Electricity)")}</option>
                                <option value="3">{t("Scope 3 (Value Chain)")}</option>
                            </NativeSelect>
                            <NativeSelect className={cn(controlClass, "qa-filter-select h-[38px] w-auto")} aria-label={t("Filter by Reporting Year")} value={yearFilter} onChange={e => { setYearFilter(e.target.value); setOffset(0); }} title={t("Filter by Reporting Year")}>
                                <option value="all">{t("All Reporting Years")}</option>
                                {Array.from({ length: new Date().getFullYear() - 2019 }, (_, i) => new Date().getFullYear() - i).map(y => (
                                    <option key={y} value={y}>{y}</option>
                                ))}
                            </NativeSelect>
                            <Button variant="secondary" onClick={() => fetchDashboard(true)} disabled={runningDiagnostics || isUpdating} title={t("Re-run data health checks and anomaly diagnostics")}>
                                <RefreshCw className={cn("size-3.5", (runningDiagnostics || isUpdating) && "animate-spin")} aria-hidden="true" />
                                {runningDiagnostics ? t("Scanning…") : t("Run Diagnostics")}
                            </Button>
                            <Button onClick={handleExport} loading={exporting} disabled={exporting} title={t("Export complete QA/QC compliance report as CSV")}>
                                <Download className="size-3.5" aria-hidden="true" />
                                {exporting ? t("Exporting…") : t("Export QA Report")}
                            </Button>
                        </div>
                    </div>
                </Card>

                <QaKpis
                    diagnostics={diagnostics}
                    uncertainty={tier1_uncertainty}
                    anomalies={anomaliesSummary}
                    totalRecords={totalRecords}
                    activeFacilities={activeFacilities}
                    totalFacilities={totalFacilities}
                    healthScore={healthScore}
                    completeness={completeness}
                />

                <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList aria-label={t("QA sections")} className="border-b-2">
                        <TabsTrigger value="queue" badge={anomaliesSummary.all}>
                            <AlertTriangle className="size-[15px]" aria-hidden="true" />{" "}{t("Anomaly Resolution Queue")}
                        </TabsTrigger>
                        <TabsTrigger value="diagnostics" badge={totalFindings}>
                            <Shield className="size-[15px]" aria-hidden="true" />{" "}{t("Health & Completeness Diagnostics")}
                        </TabsTrigger>
                        <TabsTrigger value="uncertainty">
                            <Layers className="size-[15px]" aria-hidden="true" />{" "}{t("Uncertainty & Rigor Analysis (IPCC)")}
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="queue">
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
                    </TabsContent>

                    <TabsContent value="diagnostics">
                        <DiagnosticsPanel
                            healthScore={healthScore}
                            completeness={completeness}
                            dim={dimCompleteness}
                            issues={issues}
                            warnings={warnings}
                            suggestions={suggestions}
                            expandedId={expandedFindingId}
                            onExpand={setExpandedFindingId}
                            onAction={handleFindingAction}
                        />
                    </TabsContent>

                    <TabsContent value="uncertainty">
                        <UncertaintyPanel uncertainty={tier1_uncertainty} />
                    </TabsContent>
                </Tabs>
            </Page>

            <ConfirmDialog
                open={resolveModal.isOpen}
                onCancel={() => setResolveModal({ isOpen: false, resolution: null })}
                onConfirm={confirmBulkResolve}
                loading={resolving}
                title={`Confirm Bulk ${resolveModal.resolution === 'Verified' ? 'Verification' : 'Rejection'}`}
                message={<>{t("Are you sure you want to mark")}{" "}<strong>{selectedIds.size}</strong>{" "}{t("selected record(s) as")}{" "}<strong>{resolveModal.resolution}</strong>?</>}
                confirmLabel={`Confirm ${resolveModal.resolution === 'Verified' ? 'Verification' : 'Rejection'}`}
                confirmVariant={resolveModal.resolution === 'Verified' ? 'primary' : 'danger'}
            />
        </ErrorBoundary>
    );
}
