import React, { useState, useEffect, useMemo } from 'react';
import { Badge, Button, Card, Input } from "../ui";
import { cn } from "../ui/cn";
import { controlClass } from "../components/import-wizard/mapping";
import { NativeSelect } from "../ui/NativeSelect";
import { showReviewResult } from '../utils/reviewResult';
import { useLocation } from 'react-router-dom';
import api from '../api';
import { apiError } from '../utils/apiError';

import ColumnMappingWizard from '../components/ColumnMappingWizard';
import { useToast } from '../components/Toast';
import ErrorBoundary from '../components/ErrorBoundary'; // FE-03 FIX
import Modal from '../components/Modal';
import ConfirmModal from '../components/ConfirmModal';
import { useAuth } from '../context/AuthContext';
import { getUserOperationalDefaults, matchesActivity, matchesFacilityRegion, isUnrestrictedLocation } from '../utils/userDefaults';
import { Clock, Search } from 'lucide-react';
import PendingReviewTab, { type PendingEmissionRecord, type PendingMetrics, type RejectionModalState } from './manage-data/PendingReviewTab';
import PendingAccessNotice from './manage-data/PendingAccessNotice';
import FactorsTab, { type CustomFactorRecord, type FactorWorkbenchState } from './manage-data/FactorsTab';
import FacilitiesTab, { type FacilityRecord } from './manage-data/FacilitiesTab';
import ProductionTab, { type ProductionRecord } from './manage-data/ProductionTab';
import SourcesTab, { type SourceRecord } from './manage-data/SourcesTab';
import GoalsTab, { type GoalRecord, type BaseYearRecord, type BaseYearsData, type SbtiConfig } from './manage-data/GoalsTab';
import MitigationTab, { type MitigationRecord } from './manage-data/MitigationTab';
import CbamTab, { type CbamRecord } from './manage-data/CbamTab';
import OgmpTab, { type OgmpSurveyRecord } from './manage-data/OgmpTab';
import './ManageData.css';
import '../pages/Dashboard.css';

interface ConfirmDialogState {
    isOpen: boolean;
    title: string;
    message: string;
    confirmLabel: string;
    confirmVariant: "primary" | "danger";
    onConfirm: (() => Promise<void> | void) | null;
}

const ManageDataInner: React.FC = () => {
    const { user } = useAuth();
    const isPrivileged = Boolean(user?.role && ['admin', 'superuser'].includes(user.role));

    const HIERARCHY: Record<string, string[]> = {
        'EP': ['Production', 'Association'],
        'LQS': ['LNG', 'LPG', 'LSH'],
        'RPC': ['Refining', 'Petrochemicals', 'Raffinage', 'Petrochimie'],
        'TRC': ['TRC', 'Make']
    };

    // Activities that are NOT oil & gas — excluded from OGMP 2.0 scope
    const NON_OG_ACTIVITIES = [
        'Steel & Iron (Acier DRI)',
        'Chemicals & Fertilizers',
        'Cement & Clinker',
    ];

    const ACTIVITY_LABELS: Record<string, string> = {
        'EP': 'Exploration & Production',
        'LQS': 'Liquifaction and Separation',
        'RPC': 'Refining and Petrochemicals',
        'TRC': 'Transport (TRC)'
    };

    const toast = useToast();
    const location = useLocation();
    const [activeTab, setActiveTab] = useState<string>('factors');

    // Core Data State
    const [facilities, setFacilities] = useState<FacilityRecord[]>([]);
    const [customFactors, setCustomFactors] = useState<CustomFactorRecord[]>([]);
    const [productionData, setProductionData] = useState<ProductionRecord[]>([]);
    const [availableFilters, setAvailableFilters] = useState<{ years: (number | string)[]; regions: string[] }>({ years: [], regions: [] });
    const [importModal, setImportModal] = useState<{ isOpen: boolean; type: string }>({ isOpen: false, type: 'sources' });
    const [sources, setSources] = useState<SourceRecord[]>([]);
    const [mitigations, setMitigations] = useState<MitigationRecord[]>([]);
    const [cbamExports, setCbamExports] = useState<CbamRecord[]>([]);
    const [ogmpSurveys, setOgmpSurveys] = useState<OgmpSurveyRecord[]>([]);
    const [goals, setGoals] = useState<GoalRecord[]>([]);
    const [baseYearsData, setBaseYearsData] = useState<BaseYearsData>({ active_year: undefined, active_record: null, history: [] });
    const [sbtiConfig, setSbtiConfig] = useState<SbtiConfig>({
        base_year: 2024,
        base_year_emissions: 0,
        target_year: 2050,
        reduction_rate_pct: 4.2,
        pathway_type: "1.5C"
    });
    const [hasSbti, setHasSbti] = useState<boolean>(false);

    // Derive available activities from the already-permission-filtered facilities list
    const getAvailableActivities = (facilitiesList = facilities): string[] => {
        const acts = [...new Set(facilitiesList.map(f => f.activity).filter(Boolean) as string[])];
        // Sort by the defined hierarchy order, then alphabetically for unknowns
        const order = Object.keys(HIERARCHY);
        return acts.sort((a, b) => {
            const ia = order.indexOf(a);
            const ib = order.indexOf(b);
            if (ia !== -1 && ib !== -1) return ia - ib;
            if (ia !== -1) return -1;
            if (ib !== -1) return 1;
            return a.localeCompare(b);
        });
    };

    // Derive available divisions for a given activity from the filtered facilities list
    const getAvailableDivisions = (activity?: string, facilitiesList = facilities): string[] => {
        if (!activity) return [];
        return [...new Set(
            facilitiesList.filter(f => f.activity === activity).map(f => f.division).filter(Boolean) as string[]
        )].sort();
    };

    const fetchSbti = async () => {
        try {
            const res = await api.get('/manage/sbti');
            if (res.data.has_target) {
                setHasSbti(true);
                setSbtiConfig({
                    base_year: res.data.base_year,
                    base_year_emissions: res.data.base_year_emissions,
                    target_year: res.data.target_year,
                    reduction_rate_pct: res.data.reduction_rate_pct,
                    pathway_type: res.data.pathway_type
                });
            }
        } catch (err: any) {
            toast.error(apiError(err, 'Failed to load the SBTi target'));
        }
    };

    const handleSaveSbti = async () => {
        try {
            await api.post('/manage/sbti', sbtiConfig);
            toast.success('SBTi Target saved successfully');
            setHasSbti(true);
        } catch (e: any) {
            toast.error(apiError(e, 'Failed to save SBTi Target'));
        }
    };

    const [searchTerm, setSearchTerm] = useState<string>('');
    const [pendingEmissions, setPendingEmissions] = useState<{
        scope1: any[];
        scope2: any[];
        scope3: any[];
        total_pending: number;
        pending_counts?: Record<string, number> | null;
        pending_co2e?: number;
    }>({ scope1: [], scope2: [], scope3: [], total_pending: 0 });
    const [isProcessingBatch, setIsProcessingBatch] = useState<boolean>(false);
    const [isRefreshingPending, setIsRefreshingPending] = useState<boolean>(false);
    const [pendingScopeFilter, setPendingScopeFilter] = useState<string>('all');
    const [pendingSearch, setPendingSearch] = useState<string>('');
    const [pendingQaFilter, setPendingQaFilter] = useState<string>('all');
    const [selectedPendingKeys, setSelectedPendingKeys] = useState<Set<string>>(new Set());
    const [isBatchWizardOpen, setIsBatchWizardOpen] = useState<boolean>(false);
    const [rejectionModal, setRejectionModal] = useState<RejectionModalState>({
        isOpen: false,
        isBatch: false,
        scope: '1',
        recordId: null,
        recordIds: [],
        reason: ''
    });

    const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
        isOpen: false,
        title: "",
        message: "",
        confirmLabel: "Delete",
        confirmVariant: "danger",
        onConfirm: null,
    });

    const requestConfirm = ({
        title = "Confirm Deletion",
        message = "Are you sure you want to delete this item?",
        confirmLabel = "Delete",
        confirmVariant = "danger" as "primary" | "danger",
        onConfirm,
    }: {
        title?: string;
        message?: string;
        confirmLabel?: string;
        confirmVariant?: "primary" | "danger";
        onConfirm?: () => Promise<void> | void;
    }) => {
        setConfirmDialog({
            isOpen: true,
            title,
            message,
            confirmLabel,
            confirmVariant,
            onConfirm: async () => {
                setConfirmDialog(prev => ({ ...prev, isOpen: false }));
                if (onConfirm) await onConfirm();
            },
        });
    };

    const QUICK_REJECTION_REASONS = [
        "Incorrect Emission Factor Applied",
        "Facility Allocation Mismatch",
        "Missing Activity Documentation",
        "Value Exceeds Operational Threshold",
        "Duplicate Batch Entry Detected",
        "Incomplete Activity Metric"
    ];

    const fetchPendingEmissions = async (force = false) => {
        // Only admin / superuser roles can see and action pending records
        if (!isPrivileged) return;
        // Don't repopulate the list while the reviewer is mid-review inside the wizard
        if (!force && isBatchWizardOpen) return;
        setIsRefreshingPending(true);
        try {
            const res = await api.get('/emissions/pending');
            setPendingEmissions({
                scope1: res.data.scope1 || [],
                scope2: res.data.scope2 || [],
                scope3: res.data.scope3 || [],
                total_pending: res.data.total_pending || 0,
                // whole-queue counts; the lists hold at most `limit` rows per scope
                pending_counts: res.data.pending_counts || null,
                pending_co2e: res.data.pending_co2e,
            });
        } catch (e) {
            console.error("Failed to fetch pending emissions", e);
        } finally {
            setIsRefreshingPending(false);
        }
    };

    const pendingMetrics: PendingMetrics = useMemo(() => {
        const s1 = pendingEmissions?.scope1 || [];
        const s2 = pendingEmissions?.scope2 || [];
        const s3 = pendingEmissions?.scope3 || [];

        const pc = pendingEmissions?.pending_counts;
        const count1 = pc ? pc['1'] : s1.length;
        const count2 = pc ? pc['2'] : s2.length;
        const count3 = pc ? pc['3'] : s3.length;
        const totalCount = count1 + count2 + count3;
        const loadedCount = s1.length + s2.length + s3.length;

        const tco2e1 = s1.reduce((acc, r) => acc + (Number(r.co2e_total || r.co2e) || 0), 0);
        const tco2e2 = s2.reduce((acc, r) => acc + (Number(r.co2e_total || r.co2e) || 0), 0);
        const tco2e3 = s3.reduce((acc, r) => acc + (Number(r.co2e_total || r.co2e) || 0), 0);
        const totalTco2e = typeof pendingEmissions?.pending_co2e === 'number' ? pendingEmissions.pending_co2e : tco2e1 + tco2e2 + tco2e3;

        let flaggedCount = 0;
        let cleanCount = 0;
        [...s1, ...s2, ...s3].forEach(r => {
            if (r.qa_flag) flaggedCount++;
            else cleanCount++;
        });

        return {
            count1, count2, count3, totalCount, loadedCount,
            tco2e1, tco2e2, tco2e3, totalTco2e,
            flaggedCount, cleanCount
        };
    }, [pendingEmissions]);

    const allPendingRecords: PendingEmissionRecord[] = useMemo(() => {
        const list: PendingEmissionRecord[] = [];
        (pendingEmissions?.scope1 || []).forEach(r => {
            list.push({
                key: `1-${r.id}`,
                id: r.id,
                scope: '1',
                scopeKey: 'scope1',
                year: r.year,
                month: r.month,
                date: `${r.year}-${String(r.month || 1).padStart(2, '0')}`,
                facility_id: r.facility_id,
                created_by: r.created_by,
                raw: r,
                desc: `${r.process_type || 'General'} · ${r.fuel_type || ''} (${Number(r.quantity || 0).toLocaleString()} ${r.unit || ''})`,
                tco2e: Number(r.co2e_total || r.co2e || 0),
                qa_flag: r.qa_flag
            });
        });
        (pendingEmissions?.scope2 || []).forEach(r => {
            list.push({
                key: `2-${r.id}`,
                id: r.id,
                scope: '2',
                scopeKey: 'scope2',
                year: r.year,
                month: r.month,
                date: `${r.year}-${String(r.month || 1).padStart(2, '0')}`,
                facility_id: r.facility_id,
                created_by: r.created_by,
                raw: r,
                desc: `${r.source_type || 'Electricity'} (${Number(r.electricity_kwh || 0).toLocaleString()} kWh)`,
                tco2e: Number(r.co2e_total || r.co2e || 0),
                qa_flag: r.qa_flag
            });
        });
        (pendingEmissions?.scope3 || []).forEach(r => {
            list.push({
                key: `3-${r.id}`,
                id: r.id,
                scope: '3',
                scopeKey: 'scope3',
                year: r.year,
                month: r.month,
                date: `${r.year}-${String(r.month || 1).padStart(2, '0')}`,
                facility_id: r.facility_id,
                created_by: r.created_by,
                raw: r,
                desc: `${r.category || 'Scope 3 Category'}`,
                tco2e: Number(r.co2e_total || r.co2e || 0),
                qa_flag: r.qa_flag
            });
        });
        return list;
    }, [pendingEmissions]);

    const filteredPendingRecords = useMemo(() => {
        return allPendingRecords.filter(item => {
            if (pendingScopeFilter !== 'all' && String(item.scope) !== pendingScopeFilter) return false;
            if (pendingQaFilter === 'flagged' && !item.qa_flag) return false;
            if (pendingQaFilter === 'clean' && item.qa_flag) return false;
            if (pendingSearch && pendingSearch.trim()) {
                const q = pendingSearch.toLowerCase().trim();
                const facilityName = (facilities.find(f => f && f.id === item.facility_id)?.name || '').toLowerCase();
                const matchId = String(item.id || '').toLowerCase().includes(q);
                const matchDate = String(item.date || '').toLowerCase().includes(q);
                const matchDesc = String(item.desc || '').toLowerCase().includes(q);
                const matchFacility = facilityName.includes(q) || String(item.facility_id || '').toLowerCase().includes(q);
                const matchQa = String(item.qa_flag || '').toLowerCase().includes(q);
                if (!matchId && !matchDate && !matchDesc && !matchFacility && !matchQa) return false;
            }
            return true;
        });
    }, [allPendingRecords, pendingScopeFilter, pendingQaFilter, pendingSearch, facilities]);

    const selectedPendingImpactTco2e = useMemo(() => {
        let total = 0;
        allPendingRecords.forEach(item => {
            if (selectedPendingKeys.has(item.key)) {
                total += item.tco2e;
            }
        });
        return total;
    }, [allPendingRecords, selectedPendingKeys]);

    const handleToggleSelectPending = (key: string) => {
        setSelectedPendingKeys(prev => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
        });
    };

    const handleSelectAllPendingToggle = () => {
        const allVisibleKeys = filteredPendingRecords.map(r => r.key);
        const isAllSelected = allVisibleKeys.length > 0 && allVisibleKeys.every(k => selectedPendingKeys.has(k));
        if (isAllSelected) {
            setSelectedPendingKeys(prev => {
                const next = new Set(prev);
                allVisibleKeys.forEach(k => next.delete(k));
                return next;
            });
        } else {
            setSelectedPendingKeys(prev => {
                const next = new Set(prev);
                allVisibleKeys.forEach(k => next.add(k));
                return next;
            });
        }
    };

    const handleApproveSingle = async (scope: number | string, id: number | string) => {
        try {
            await api.post(`/emissions/approve/${id}`, { scope: String(scope) });
            toast.success('Record approved successfully');
            setSelectedPendingKeys(prev => {
                const next = new Set(prev);
                next.delete(`${scope}-${id}`);
                return next;
            });
            fetchPendingEmissions();
        } catch (e: any) {
            toast.error(e.response?.data?.error || 'Failed to approve record');
        }
    };

    const handleOpenRejectModal = (scope: number | string, id: number | string) => {
        setRejectionModal({
            isOpen: true,
            isBatch: false,
            scope: String(scope),
            recordId: id,
            recordIds: [`${scope}-${id}`],
            reason: ''
        });
    };

    const handleOpenBatchRejectModal = () => {
        if (selectedPendingKeys.size === 0) return;
        setRejectionModal({
            isOpen: true,
            isBatch: true,
            scope: pendingScopeFilter !== 'all' ? pendingScopeFilter : 'all',
            recordId: null,
            recordIds: Array.from(selectedPendingKeys),
            reason: ''
        });
    };

    const handleBatchApproveSelected = async () => {
        if (selectedPendingKeys.size === 0) return;
        setIsProcessingBatch(true);
        try {
            const byScope: Record<string, number[]> = { '1': [], '2': [], '3': [] };
            const ids: number[] = [];
            selectedPendingKeys.forEach(key => {
                const [scope, id] = key.split('-');
                if (byScope[scope]) byScope[scope].push(Number(id));
                ids.push(Number(id));
            });

            const res = await api.post('/emissions/approve/batch', {
                scope: 'all',
                ids,
                by_scope: byScope,
                approve_all: false
            });

            showReviewResult(toast, 'approved', res.data?.approved_count, selectedPendingKeys.size);
            setSelectedPendingKeys(new Set());
            fetchPendingEmissions();
        } catch (err: any) {
            toast.error(err.response?.data?.error || 'Failed to approve selected records');
        } finally {
            setIsProcessingBatch(false);
        }
    };

    const handleConfirmReject = async () => {
        if (!rejectionModal.reason.trim()) {
            toast.warning('Please specify or select a rejection reason');
            return;
        }
        setIsProcessingBatch(true);
        try {
            if (!rejectionModal.isBatch && rejectionModal.recordId) {
                await api.post(`/emissions/reject/${rejectionModal.recordId}`, {
                    scope: rejectionModal.scope,
                    reason: rejectionModal.reason.trim()
                });
                toast.success('Record rejected');
            } else {
                const byScope: Record<string, number[]> = { '1': [], '2': [], '3': [] };
                const ids: number[] = [];
                rejectionModal.recordIds.forEach(key => {
                    const [scope, id] = key.split('-');
                    if (byScope[scope]) byScope[scope].push(Number(id));
                    ids.push(Number(id));
                });

                const res = await api.post('/emissions/reject/batch', {
                    scope: 'all',
                    ids,
                    by_scope: byScope,
                    reason: rejectionModal.reason.trim(),
                    reject_all: false
                });
                showReviewResult(toast, 'rejected', res.data?.rejected_count ?? res.data?.deleted_count, rejectionModal.recordIds.length);
            }
            setRejectionModal({ isOpen: false, isBatch: false, scope: '1', recordId: null, recordIds: [], reason: '' });
            setSelectedPendingKeys(new Set());
            fetchPendingEmissions();
        } catch (err: any) {
            toast.error(err.response?.data?.error || 'Failed to reject record(s)');
        } finally {
            setIsProcessingBatch(false);
        }
    };

    const handleApproveAllInScope = (scopeNum: string | number) => {
        const count = (pendingMetrics as any)[`count${scopeNum}`];
        if (!count) return;
        requestConfirm({
            title: `Approve Scope ${scopeNum} Records`,
            message: `Are you sure you want to approve all ${count} pending Scope ${scopeNum} records?`,
            confirmLabel: "Approve All",
            confirmVariant: "primary",
            onConfirm: async () => {
                setIsProcessingBatch(true);
                try {
                    const res = await api.post('/emissions/approve/batch', { approve_all: true, scope: String(scopeNum) });
                    // the server skips the reviewer's own records: report its count, not the request
                    showReviewResult(toast, 'approved', res.data?.approved_count, count);
                    setSelectedPendingKeys(prev => {
                        const next = new Set(prev);
                        Array.from(next).forEach(k => {
                            if (k.startsWith(`${scopeNum}-`)) next.delete(k);
                        });
                        return next;
                    });
                    fetchPendingEmissions();
                } catch (err: any) {
                    toast.error(err.response?.data?.error || 'Failed to approve batch');
                } finally {
                    setIsProcessingBatch(false);
                }
            }
        });
    };

    // Auto-switch tab when navigated from Dashboard with state or query param
    useEffect(() => {
        const queryTab = new URLSearchParams(location.search).get('tab');
        const targetTab = location.state?.tab || queryTab;
        if (targetTab) {
            setActiveTab(targetTab);
            // Scroll into view smoothly
            setTimeout(() => {
                document.querySelector('.manage-nav-item.active')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }
    }, [location.state, location.search]);

    const handleTabChange = (tab: string) => {
        setActiveTab(tab);
        setCurrentPage(1);
        setSearchTerm('');
    };

    // Filter & Pagination State
    const [currentPage, setCurrentPage] = useState<number>(1);
    const ITEMS_PER_PAGE = 15;
    
    const [filterActivity, setFilterActivity] = useState<string>('');
    const [filterDivision, setFilterDivision] = useState<string>('');
    const [filterRegion, setFilterRegion] = useState<string>('');
    const [filterYear, setFilterYear] = useState<string>('');

    useEffect(() => {
        setCurrentPage(1);
    }, [activeTab, searchTerm, filterActivity, filterDivision, filterRegion, filterYear]);

    // Forms State
    const [facilityForm, setFacilityForm] = useState<Record<string, any>>({
        name: '', activity: '', division: '', field: '', location: '',
        boundary_type: '', boundary_detail: '', equity_share_pct: '',
        segment: '', latitude: '', longitude: ''
    });

    const [factorForm, setFactorForm] = useState<Record<string, any>>({
        factor_name: '', parent_fuel: '', unit: 'scf',
        co2_factor: '', ch4_factor: '', n2o_factor: '',
        co_factor: '', co2_uncertainty: '', ch4_uncertainty: '', n2o_uncertainty: '',
        source: '', description: ''
    });
    const [editingFactorId, setEditingFactorId] = useState<string | number | null>(null);

    const [prodForm, setProdForm] = useState<Record<string, any>>({
        activity: '', division: '', facility_id: '',
        month: 1, year: new Date().getFullYear(),
        oil_amount: '', oil_unit: 'bbl',
        gas_amount: '', gas_unit: 'mscf',
        gross_gas_mmsm3: '', gas_without_injected_mmsm3: '', injected_gas_mmsm3: '',
        crude_oil_mmboe: '', condensate_mmboe: '', lpg_mmboe: '',
        total_production_mmboe: '', saleable_production_mmboe: ''
    });

    const [sourceForm, setSourceForm] = useState<Record<string, any>>({
        activity: '', division: '', facility_id: '',
        name: '', type: '', equipment_id: '', fuel_type: '',
        design_capacity: '', description: '', status: 'Active'
    });

    const [mitigationForm, setMitigationForm] = useState<Record<string, any>>({
        activity: '', division: '', facility_id: '',
        name: '', year: new Date().getFullYear(), type: 'CCUS',
        quantity_tco2e: '', status: 'Active', reference_id: '', notes: ''
    });

    const [cbamForm, setCbamForm] = useState<Record<string, any>>({
        id: null,
        activity: "",
        division: "",
        facility_id: "",
        year: new Date().getFullYear(),
        month: 1,
        product_name: "Crude Petroleum Oil",
        cn_code: "2709 00",
        quantity_tonnes: "",
        export_destination: "EU",
        specific_embedded_direct: "",
        specific_embedded_indirect: "",
        notes: "",
    });
    const [editingCbamId, setEditingCbamId] = useState<string | number | null>(null);

    const [ogmpForm, setOgmpForm] = useState<Record<string, any>>({
        id: null, activity: '', division: '', facility_id: '',
        year: new Date().getFullYear(),
        survey_date: new Date().toISOString().split('T')[0],
        survey_type: 'Satellite (Sentinel-5P/MethaneSAT)',
        measured_rate_kg_hr: '', reconciliation_status: 'Reconciled', operator_notes: ''
    });
    const [editingOgmpId, setEditingOgmpId] = useState<string | number | null>(null);

    const [goalForm, setGoalForm] = useState<{ year: number | string; target_amount: number | string }>({
        year: new Date().getFullYear(),
        target_amount: ''
    });
    const [editingGoalYear, setEditingGoalYear] = useState<number | string | null>(null);

    const [baseYearForm, setBaseYearForm] = useState<Record<string, any>>({
        year: new Date().getFullYear(),
        reason: '',
        previous_emissions: '',
        adjusted_emissions: ''
    });

    const [workbench, setWorkbench] = useState<FactorWorkbenchState>({
        meter_precision: 5.0, lab_precision: 2.0, gwp_uncertainty: 15.0
    });

    // Fetch Data on Load
    useEffect(() => {
        fetchFacilities();
        fetchCustomFactors();
        fetchProduction();
        fetchSources();
        fetchMitigations();
        fetchCbamExports();
        fetchOgmpSurveys();
        fetchGoals();
        fetchBaseYears();
        fetchPendingEmissions();
        fetchSbti();
    }, []);

    // Auto-populate filters and forms based on connected user's and superuser's region, division, and activity
    useEffect(() => {
        if (!user) return;
        const userLoc = (user.location || '').trim();
        const isGlobalAdmin = user.role === 'admin' && isUnrestrictedLocation(userLoc);
        if (isGlobalAdmin && facilities.length > 1) return;

        const opDefaults = getUserOperationalDefaults(user, facilities);

        // 1. Set Toolbar Filter Dropdowns (region, activity, division)
        if (opDefaults.defaultRegion) {
            setFilterRegion(prev => prev || opDefaults.defaultRegion);
        }
        if (opDefaults.defaultActivity) {
            let actToSet = opDefaults.defaultActivity;
            if (['Upstream', 'Exploration & Production', 'EP'].includes(actToSet)) actToSet = 'EP';
            else if (['Downstream', 'Refining and Petrochemicals', 'RPC'].includes(actToSet)) actToSet = 'RPC';
            else if (['Midstream', 'Transport', 'TRC'].includes(actToSet)) actToSet = 'TRC';
            else if (['LQS', 'Liquifaction and Separation'].includes(actToSet)) actToSet = 'LQS';
            setFilterActivity(prev => prev || actToSet);
        }
        if (opDefaults.defaultDivision) {
            setFilterDivision(prev => prev || opDefaults.defaultDivision);
        }

        // 2. Set Entry Form Defaults
        const autoFill = {
            activity: opDefaults.defaultActivity || '',
            division: opDefaults.defaultDivision || '',
            facility_id: opDefaults.defaultFacilityId || ''
        };

        if (autoFill.activity || autoFill.division || autoFill.facility_id || opDefaults.defaultRegion) {
            setProdForm(prev => ({
                ...prev,
                activity: prev.activity || autoFill.activity,
                division: prev.division || autoFill.division,
                facility_id: prev.facility_id || autoFill.facility_id,
            }));
            setSourceForm(prev => ({
                ...prev,
                activity: prev.activity || autoFill.activity,
                division: prev.division || autoFill.division,
                facility_id: prev.facility_id || autoFill.facility_id,
            }));
            setMitigationForm(prev => ({
                ...prev,
                activity: prev.activity || autoFill.activity,
                division: prev.division || autoFill.division,
                facility_id: prev.facility_id || autoFill.facility_id,
            }));
            setCbamForm(prev => ({
                ...prev,
                activity: prev.activity || autoFill.activity,
                division: prev.division || autoFill.division,
                facility_id: prev.facility_id || autoFill.facility_id,
            }));
            setOgmpForm(prev => ({
                ...prev,
                activity: prev.activity || autoFill.activity,
                division: prev.division || autoFill.division,
                facility_id: prev.facility_id || autoFill.facility_id,
            }));
            setFacilityForm(prev => ({
                ...prev,
                location: prev.location || opDefaults.defaultRegion,
                activity: prev.activity || autoFill.activity,
                division: prev.division || autoFill.division,
            }));
        }
    }, [facilities, user]);

    // API Calls
    const fetchFacilities = async () => {
        try {
            const res = await api.get('/facilities');
            const data: FacilityRecord[] = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setFacilities(data);
            const regions = [...new Set(data.flatMap(f => [f.region_identifier, f.location]).filter(Boolean) as string[])].sort();
            const userLoc = (user?.location || '').trim();
            if (userLoc && !isUnrestrictedLocation(userLoc) && !regions.includes(userLoc)) {
                regions.unshift(userLoc);
            }
            setAvailableFilters(prev => ({ ...prev, regions }));
        } catch (err: any) { console.error(err); toast.error(apiError(err, 'Failed to load facilities')); }
    };

    const fetchCustomFactors = async () => {
        try {
            const res = await api.get('/custom-factors');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setCustomFactors(data);
        } catch (err: any) { console.error(err); toast.error(apiError(err, 'Failed to load custom factors')); }
    };

    const fetchProduction = async () => {
        try {
            const res = await api.get('/data/production');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setProductionData(data);
            const years = [...new Set(data.map((d: any) => d.year))].sort((a: any, b: any) => b - a) as (number | string)[];
            setAvailableFilters(prev => ({ ...prev, years }));
        } catch (err: any) { console.error(err); toast.error(apiError(err, 'Failed to load production')); }
    };

    const fetchSources = async () => {
        try {
            const res = await api.get('/sources');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setSources(data);
        } catch (err: any) { console.error(err); toast.error(apiError(err, 'Failed to load sources')); }
    };

    const fetchMitigations = async () => {
        try {
            const res = await api.get('/mitigation');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setMitigations(data);
        } catch (err: any) { console.error(err); toast.error(apiError(err, 'Failed to load mitigations')); }
    };

    const fetchCbamExports = async () => {
        try {
            const res = await api.get('/data/cbam-exports');
            setCbamExports(res.data || []);
        } catch (err: any) {
            console.error(err); toast.error(apiError(err, 'Failed to load cbam exports'));
        }
    };

    const fetchOgmpSurveys = async () => {
        try {
            const res = await api.get('/data/ogmp-surveys');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setOgmpSurveys(data);
        } catch (err: any) { console.error(err); toast.error(apiError(err, 'Failed to load ogmp surveys')); }
    };

    const fetchGoals = async () => {
        try {
            const res = await api.get('/goals');
            const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
            setGoals(data);
        } catch (err: any) { console.error('Failed to fetch goals:', err); toast.error(apiError(err, 'Failed to load emission goals')); }
    };

    const fetchBaseYears = async () => {
        try {
            const res = await api.get('/base-years');
            setBaseYearsData(res.data || { active_year: undefined, active_record: null, history: [] });
        } catch (err: any) { console.error('Failed to fetch base years:', err); toast.error(apiError(err, 'Failed to load base years')); }
    };

    const handleSaveGoal = async () => {
        if (!goalForm.year || goalForm.target_amount === '') {
            return toast.error('Year and target emission amount (tCO₂e) are required');
        }
        try {
            await api.post('/goals', {
                year: parseInt(String(goalForm.year), 10),
                target_amount: parseFloat(String(goalForm.target_amount))
            });
            toast.success(editingGoalYear ? 'Emission goal updated!' : 'Emission goal saved!');
            setEditingGoalYear(null);
            setGoalForm({ year: new Date().getFullYear(), target_amount: '' });
            fetchGoals();
        } catch (err: any) {
            toast.error(err.response?.data?.error || 'Failed to save emission goal');
        }
    };

    const handleEditGoal = (goal: GoalRecord) => {
        setGoalForm({
            year: goal.year,
            target_amount: goal.target_amount
        });
        setEditingGoalYear(goal.year);
    };

    const handleDeleteGoal = (year: number | string) => {
        requestConfirm({
            title: "Delete Emission Goal",
            message: `Delete emission goal for year ${year}?`,
            confirmLabel: "Delete Goal",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/goals/${year}`);
                    toast.success('Emission goal deleted');
                    if (editingGoalYear === year) {
                        setEditingGoalYear(null);
                        setGoalForm({ year: new Date().getFullYear(), target_amount: '' });
                    }
                    fetchGoals();
                } catch (err: any) {
                    toast.error(err.response?.data?.error || 'Failed to delete goal');
                }
            }
        });
    };

    const handleSaveBaseYear = async () => {
        if (!baseYearForm.year || !baseYearForm.reason.trim()) {
            return toast.error('Base Year and Reason for change/recalculation are required');
        }
        try {
            await api.post('/base-years', {
                year: parseInt(String(baseYearForm.year), 10),
                reason: baseYearForm.reason.trim(),
                previous_emissions: baseYearForm.previous_emissions !== '' ? parseFloat(baseYearForm.previous_emissions) : null,
                adjusted_emissions: baseYearForm.adjusted_emissions !== '' ? parseFloat(baseYearForm.adjusted_emissions) : null
            });
            toast.success('Base year recalculation recorded successfully!');
            setBaseYearForm({
                year: new Date().getFullYear(),
                reason: '',
                previous_emissions: '',
                adjusted_emissions: ''
            });
            fetchBaseYears();
        } catch (err: any) {
            toast.error(err.response?.data?.error || 'Failed to record base year');
        }
    };

    const handleDeleteBaseYearRecalc = (id: string | number) => {
        requestConfirm({
            title: "Delete Base Year Recalculation",
            message: 'Delete this base year recalculation entry?',
            confirmLabel: "Delete Record",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/base-years/${id}`);
                    toast.success('Base year record deleted');
                    fetchBaseYears();
                } catch (err: any) {
                    toast.error(err.response?.data?.error || 'Failed to delete base year record');
                }
            }
        });
    };

    // Handlers
    const handleFacilityChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFacilityForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleFactorChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFactorForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleAddFacility = async () => {
        if (!facilityForm.name || !facilityForm.activity || !facilityForm.division) {
            return toast.error('Name, Activity, and Division are required');
        }
        try {
            // Construct combined boundary_notes
            const fullBoundary = facilityForm.boundary_detail
                ? `${facilityForm.boundary_type} - ${facilityForm.boundary_detail}`
                : facilityForm.boundary_type;

            // BUG-045: optional numeric fields are omitted when empty (the server used to 500 on "")
            const body: Record<string, any> = { ...facilityForm, boundary_notes: fullBoundary };
            ['latitude', 'longitude', 'equity_share_pct'].forEach((k) => {
                if (body[k] === '' || body[k] === null || body[k] === undefined) delete body[k];
            });
            await api.post('/facilities', body);
            toast.success('Region added!');
            setFacilityForm({
                name: '', activity: '', division: '', field: '', location: '',
                boundary_type: '', boundary_detail: '', equity_share_pct: '',
                segment: '', latitude: '', longitude: ''
            });
            fetchFacilities();
        } catch (err: any) { toast.error(apiError(err, 'Failed to add region')); }
    };

    const handleSaveFactor = async () => {
        if (!factorForm.factor_name) return toast.error('Name required');
        try {
            if (editingFactorId) {
                await api.put(`/custom-factors/${editingFactorId}`, factorForm);
                toast.success('Factor updated!');
            } else {
                await api.post('/custom-factors', factorForm);
                toast.success('Factor added!');
            }
            setFactorForm({ factor_name: '', parent_fuel: '', unit: 'scf', co2_factor: '', ch4_factor: '', n2o_factor: '', co_factor: '', co2_uncertainty: '', ch4_uncertainty: '', n2o_uncertainty: '', source: '', description: '' });
            setEditingFactorId(null);
            fetchCustomFactors();
        } catch (err: any) { toast.error(apiError(err, 'Failed to save factor')); }
    };

    const handleDeleteFactor = (id: string | number) => {
        requestConfirm({
            title: "Delete Custom Factor",
            message: 'Delete this factor?',
            confirmLabel: "Delete Factor",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/custom-factors/${id}`);
                    toast.success('Factor deleted!');
                    fetchCustomFactors();
                } catch (err: any) { toast.error(apiError(err, 'Failed to delete factor')); }
            }
        });
    };

    // BUG-056: a factor used by records cannot be deleted; archiving hides it from new entries
    const handleArchiveFactor = async (id: string | number) => {
        try {
            await api.post(`/custom-factors/${id}/archive`, {});
            toast.success('Factor archived');
            fetchCustomFactors();
        } catch (err: any) { toast.error(apiError(err, 'Failed to archive factor')); }
    };

    const handleApproveFactor = async (id: string | number) => {
        try {
            await api.post(`/custom-factors/${id}/approve`, {});
            toast.success('Factor approved successfully');
            fetchCustomFactors();
        } catch (err: any) {
            console.error(err);
            toast.error(apiError(err, 'Failed to approve factor'));
        }
    };

    const handleEditFactor = (factor: CustomFactorRecord) => {
        setFactorForm({
            factor_name: factor.factor_name || factor.name || '',
            parent_fuel: factor.parent_fuel || '',
            unit: factor.unit || 'scf',
            co2_factor: factor.co2_factor || '',
            ch4_factor: factor.ch4_factor || '',
            n2o_factor: factor.n2o_factor || '',
            co_factor: factor.co_factor || '',
            co2_uncertainty: factor.co2_uncertainty || '',
            ch4_uncertainty: factor.ch4_uncertainty || '',
            n2o_uncertainty: factor.n2o_uncertainty || '',
            source: factor.source || '',
            description: factor.description || ''
        });
        setEditingFactorId(factor.id);
    };

    const handleSaveProduction = async () => {
        if (!prodForm.facility_id || !prodForm.year || !prodForm.month) {
            return toast.error('Region, Year and Month are required');
        }
        try {
            await api.post('/data/production', {
                ...prodForm,
                oil_amount: parseFloat(prodForm.oil_amount) || 0,
                gas_amount: parseFloat(prodForm.gas_amount) || 0,
                gross_gas_mmsm3: parseFloat(prodForm.gross_gas_mmsm3) || 0,
                gas_without_injected_mmsm3: parseFloat(prodForm.gas_without_injected_mmsm3) || 0,
                injected_gas_mmsm3: parseFloat(prodForm.injected_gas_mmsm3) || 0,
                crude_oil_mmboe: parseFloat(prodForm.crude_oil_mmboe) || 0,
                condensate_mmboe: parseFloat(prodForm.condensate_mmboe) || 0,
                lpg_mmboe: parseFloat(prodForm.lpg_mmboe) || 0,
                total_production_mmboe: parseFloat(prodForm.total_production_mmboe) || 0,
                saleable_production_mmboe: parseFloat(prodForm.saleable_production_mmboe) || 0,
            });
            toast.success('Production record saved!');
            fetchProduction();
            setProdForm(prev => ({
                ...prev,
                oil_amount: '', gas_amount: '',
                gross_gas_mmsm3: '', gas_without_injected_mmsm3: '', injected_gas_mmsm3: '',
                crude_oil_mmboe: '', condensate_mmboe: '', lpg_mmboe: '',
                total_production_mmboe: '', saleable_production_mmboe: ''
            }));
        } catch (err: any) { toast.error(apiError(err, 'Failed to save production')); }
    };

    const handleSaveSource = async () => {
        if (!sourceForm.facility_id || !sourceForm.name) return toast.error('Name and Region required');
        try {
            await api.post('/sources', sourceForm);
            toast.success('Source added!');
            fetchSources();
            setSourceForm({ ...sourceForm, name: '', equipment_id: '', fuel_type: '', design_capacity: '', description: '' });
        } catch (err: any) { toast.error(apiError(err, 'Failed to add source')); }
    };

    const handleSaveMitigation = async () => {
        if (!mitigationForm.quantity_tco2e) return toast.error('Quantity required');
        try {
            await api.post('/mitigation', mitigationForm);
            toast.success('Mitigation record saved!');
            fetchMitigations();
            setMitigationForm({ ...mitigationForm, quantity_tco2e: '', notes: '', reference_id: '', name: '' });
        } catch (err: any) { toast.error(apiError(err, 'Failed to save mitigation')); }
    };

    const handleSaveCbamExport = async () => {
        if (!cbamForm.facility_id || !cbamForm.product_name || !cbamForm.quantity_tonnes) {
            return toast.error('Facility, Product Name, and Export Quantity are required');
        }
        try {
            await api.post('/data/cbam-exports', {
                id: editingCbamId || undefined,
                facility_id: parseInt(cbamForm.facility_id, 10),
                year: parseInt(cbamForm.year, 10),
                month: parseInt(cbamForm.month, 10),
                product_name: cbamForm.product_name,
                cn_code: cbamForm.cn_code,
                quantity_tonnes: parseFloat(cbamForm.quantity_tonnes),
                export_destination: cbamForm.export_destination,
                specific_embedded_direct: cbamForm.specific_embedded_direct ? parseFloat(cbamForm.specific_embedded_direct) : 0.0,
                specific_embedded_indirect: cbamForm.specific_embedded_indirect ? parseFloat(cbamForm.specific_embedded_indirect) : 0.0,
                notes: cbamForm.notes
            });
            toast.success(editingCbamId ? 'CBAM export record updated!' : 'CBAM export record saved!');
            setEditingCbamId(null);
            setCbamForm({
                id: null, activity: cbamForm.activity, division: cbamForm.division, facility_id: cbamForm.facility_id,
                year: new Date().getFullYear(), month: 1,
                product_name: 'Crude Petroleum Oil', cn_code: '2709 00',
                quantity_tonnes: '', export_destination: 'EU',
                specific_embedded_direct: '', specific_embedded_indirect: '', notes: ''
            });
            fetchCbamExports();
        } catch (err: any) {
            toast.error(err?.response?.data?.error || 'Failed to save CBAM record');
        }
    };

    const handleDeleteCbamExport = (id: string | number) => {
        requestConfirm({
            title: "Delete CBAM Export",
            message: 'Delete this CBAM export record?',
            confirmLabel: "Delete Record",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete('/data/cbam-exports/' + id);
                    toast.success('CBAM export record deleted');
                    fetchCbamExports();
                } catch (err: any) {
                    toast.error(apiError(err, 'Failed to delete CBAM record'));
                }
            }
        });
    };

    const handleSaveOgmpSurvey = async () => {
        if (!ogmpForm.facility_id || !ogmpForm.survey_date || ogmpForm.measured_rate_kg_hr === '') {
            return toast.error('Facility, Survey Date, and Measured Rate are required');
        }
        try {
            await api.post('/data/ogmp-surveys', {
                id: editingOgmpId || undefined,
                facility_id: parseInt(ogmpForm.facility_id, 10),
                year: parseInt(ogmpForm.year, 10),
                survey_date: ogmpForm.survey_date,
                survey_type: ogmpForm.survey_type,
                measured_rate_kg_hr: parseFloat(ogmpForm.measured_rate_kg_hr),
                reconciliation_status: ogmpForm.reconciliation_status,
                reconciliation_override_reason: ogmpForm.operator_notes || 'Operational field survey observation',
                operator_notes: ogmpForm.operator_notes
            });
            toast.success(editingOgmpId ? 'OGMP survey record updated!' : 'OGMP survey record saved!');
            setEditingOgmpId(null);
            setOgmpForm({
                id: null, activity: ogmpForm.activity, division: ogmpForm.division, facility_id: ogmpForm.facility_id,
                year: new Date().getFullYear(),
                survey_date: new Date().toISOString().split('T')[0],
                survey_type: 'Satellite (Sentinel-5P/MethaneSAT)',
                measured_rate_kg_hr: '', reconciliation_status: 'Reconciled', operator_notes: ''
            });
            fetchOgmpSurveys();
        } catch (err: any) {
            toast.error(err.response?.data?.error || 'Failed to save OGMP survey');
        }
    };

    const handleDeleteOgmpSurvey = (id: string | number) => {
        requestConfirm({
            title: "Delete OGMP Survey",
            message: 'Delete this OGMP survey record?',
            confirmLabel: "Delete Survey",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/data/ogmp-surveys/${id}`);
                    toast.success('OGMP survey record deleted');
                    fetchOgmpSurveys();
                } catch (err: any) {
                    toast.error(apiError(err, 'Failed to delete OGMP survey'));
                }
            }
        });
    };

    const handleDeleteFacility = (id: string | number) => {
        requestConfirm({
            title: "Delete Region",
            message: 'Are you sure you want to delete this region/facility? Associated records may be affected.',
            confirmLabel: "Delete Region",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/facilities/${id}`);
                    toast.success('Region deleted');
                    fetchFacilities();
                } catch (err: any) {
                    toast.error(err?.response?.data?.error || 'Failed to delete region');
                }
            }
        });
    };

    const handleDeleteProduction = (id: string | number) => {
        requestConfirm({
            title: "Delete Production Record",
            message: 'Delete this production record?',
            confirmLabel: "Delete Record",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/data/production/${id}`);
                    toast.success('Production record deleted');
                    fetchProduction();
                } catch (err: any) {
                    toast.error(err?.response?.data?.error || 'Failed to delete production record');
                }
            }
        });
    };

    const handleDeleteSource = (id: string | number) => {
        requestConfirm({
            title: "Delete Emission Source",
            message: 'Delete this emission source?',
            confirmLabel: "Delete Source",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/sources/${id}`);
                    toast.success('Emission source deleted');
                    fetchSources();
                } catch (err: any) {
                    toast.error(err?.response?.data?.error || 'Failed to delete emission source');
                }
            }
        });
    };

    const handleDeleteMitigation = (id: string | number) => {
        requestConfirm({
            title: "Delete Mitigation Project",
            message: 'Delete this mitigation project?',
            confirmLabel: "Delete Project",
            confirmVariant: "danger",
            onConfirm: async () => {
                try {
                    await api.delete(`/mitigation/${id}`);
                    toast.success('Mitigation project deleted');
                    fetchMitigations();
                } catch (err: any) {
                    toast.error(err?.response?.data?.error || 'Failed to delete mitigation project');
                }
            }
        });
    };

    // Conversion Helpers (in-app modal dialog replacing blocking browser prompt)
    const [convertModal, setConvertModal] = useState<{ isOpen: boolean; type: 'gas' | 'oil'; value: string }>({ isOpen: false, type: 'gas', value: '' });

    const openGasConverter = () => {
        setConvertModal({ isOpen: true, type: 'gas', value: '' });
    };

    const openOilConverter = () => {
        setConvertModal({ isOpen: true, type: 'oil', value: '' });
    };

    const handleApplyConversion = (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        const val = parseFloat(convertModal.value);
        if (isNaN(val) || val <= 0) {
            toast.error("Please enter a valid positive number");
            return;
        }
        if (convertModal.type === 'gas') {
            const mcf = (val * 0.0353147).toFixed(2);
            setProdForm(prev => ({ ...prev, gas_amount: mcf, gas_unit: 'mscf' }));
            toast.success(`Converted ${val} m³ to ${mcf} mcf`);
        } else {
            const bbl = (val * 6.28981).toFixed(2);
            setProdForm(prev => ({ ...prev, oil_amount: bbl, oil_unit: 'bbl' }));
            toast.success(`Converted ${val} m³ to ${bbl} bbl`);
        }
        setConvertModal({ isOpen: false, type: 'gas', value: '' });
    };

    // CSV Logic with RFC 4180 Escaping and Blob Download
    const exportToCSV = (data: any[], filename: string) => {
        if (!data || data.length === 0) return toast.info('No data to export');
        const keys = Object.keys(data[0]);
        const escapeCell = (val: any) => {
            if (val === null || val === undefined) return '';
            const str = String(val);
            if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
                return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
        };
        const headers = keys.map(escapeCell).join(',');
        const rows = data.map(obj => keys.map(k => escapeCell(obj[k])).join(',')).join('\r\n');
        const csvContent = "\uFEFF" + headers + "\r\n" + rows;
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    // --- Dynamic Options and Matching for Filters ---
    const activityFilterOptions = useMemo(() => {
        const options = Object.keys(HIERARCHY).map(a => ({ value: a, label: ACTIVITY_LABELS[a] || a }));
        facilities.forEach(f => {
            if (f.activity && !options.some(opt => opt.value === f.activity || matchesActivity(opt.value, f.activity))) {
                options.push({ value: f.activity, label: f.activity });
            }
        });
        return options;
    }, [facilities]);

    const divisionFilterOptions = useMemo(() => {
        if (!filterActivity) return [];
        const fromHierarchy = HIERARCHY[filterActivity] || [];
        const fromFacilities = facilities
            .filter(f => matchesActivity(f.activity, filterActivity))
            .map(f => f.division)
            .filter(Boolean) as string[];
        return [...new Set([...fromHierarchy, ...fromFacilities])].sort();
    }, [filterActivity, facilities]);

    const matchesRegionCheck = (fac: any, region: string) => {
        if (!region || region === 'all') return true;
        if (!fac) return false;
        return matchesFacilityRegion(fac, region);
    };

    // --- Pre-calculate Filtered Data for Pagination ---
    const getFilteredFactors = () => customFactors.filter(f => {
        if (!f) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        return (f.factor_name || '').toLowerCase().includes(sTerm);
    });
    
    const getFilteredFacilities = () => facilities.filter(f => {
        if (!f) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const matchesSearch = (f.name || '').toLowerCase().includes(sTerm) || 
                              (f.location || '').toLowerCase().includes(sTerm) || 
                              (f.field || '').toLowerCase().includes(sTerm) ||
                              (f.code || '').toLowerCase().includes(sTerm);
        const matchesAct = filterActivity ? matchesActivity(f.activity, filterActivity) : true;
        const matchesDiv = filterDivision ? f.division === filterDivision : true;
        const matchesReg = matchesRegionCheck(f, filterRegion);
        return matchesSearch && matchesAct && matchesDiv && matchesReg;
    });

    const getFilteredProduction = () => productionData.filter(d => {
        if (!d) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const fac = facilities.find(f => f && f.id === d.facilityId);
        const facName = (fac ? fac.name : String(d.facilityId || '')) || '';
        const matchesSearch = facName.toLowerCase().includes(sTerm) || 
                              (d.year ? d.year.toString().includes(searchTerm || '') : false) || 
                              (d.activity || '').toLowerCase().includes(sTerm);
        const matchesAct = filterActivity ? (matchesActivity(d.activity, filterActivity) || (fac && matchesActivity(fac.activity, filterActivity))) : true;
        const matchesDiv = filterDivision ? (d.division === filterDivision || (fac && fac.division === filterDivision)) : true;
        const matchesReg = matchesRegionCheck(fac, filterRegion);
        const matchesYear = filterYear ? d.year?.toString() === filterYear.toString() : true;
        return matchesSearch && matchesAct && matchesDiv && matchesReg && matchesYear;
    });

    const getFilteredSources = () => sources.filter(s => {
        if (!s) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const fac = facilities.find(f => f && f.id === s.facility_id);
        const matchesSearch = (s.name || '').toLowerCase().includes(sTerm) || 
                              (s.equipment_id || '').toLowerCase().includes(sTerm) || 
                              (s.type || '').toLowerCase().includes(sTerm);
        const matchesAct = filterActivity ? (fac && matchesActivity(fac.activity, filterActivity)) : true;
        const matchesDiv = filterDivision ? (fac && fac.division === filterDivision) : true;
        const matchesReg = matchesRegionCheck(fac, filterRegion);
        return matchesSearch && matchesAct && matchesDiv && matchesReg;
    });

    const getFilteredMitigations = () => mitigations.filter(m => {
        if (!m) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const fac = facilities.find(f => f && f.id === m.facility_id);
        const matchesSearch = (m.name || '').toLowerCase().includes(sTerm) || 
                              (m.mitigation_type || m.type || '').toLowerCase().includes(sTerm) || 
                              (m.notes || '').toLowerCase().includes(sTerm) || 
                              (m.year ? m.year.toString().includes(searchTerm || '') : false);
        const matchesAct = filterActivity ? (matchesActivity(m.activity, filterActivity) || (fac && matchesActivity(fac.activity, filterActivity))) : true;
        const matchesDiv = filterDivision ? (m.division === filterDivision || fac?.division === filterDivision) : true;
        const matchesReg = matchesRegionCheck(fac || { region: m.region, location: m.region }, filterRegion);
        const matchesYear = filterYear ? m.year?.toString() === filterYear.toString() : true;
        return matchesSearch && matchesAct && matchesDiv && matchesReg && matchesYear;
    });

    const getFilteredOgmp = () => ogmpSurveys.filter(o => {
        if (!o) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const fid = o.facility_id || o.facilityId;
        const fac = facilities.find(f => f && f.id === fid);
        const sType = String(o.survey_type || o.surveyType || '');
        const fName = String(o.facility_name || o.facilityName || fac?.name || '');
        const rStatus = String(o.reconciliation_status || o.reconciliationStatus || '');
        const dateVal = o.survey_date || o.surveyDate;
        const yr = (o.year || (dateVal ? new Date(dateVal).getFullYear() : '') || '').toString();

        // Only show O&G facilities in the OGMP tab
        const isOilAndGas = !fac || !NON_OG_ACTIVITIES.includes(fac.activity || '');

        const matchesSearch = sType.toLowerCase().includes(sTerm) ||
            fName.toLowerCase().includes(sTerm) ||
            rStatus.toLowerCase().includes(sTerm) ||
            yr.includes(searchTerm || '');
        const matchesAct = filterActivity ? (fac && matchesActivity(fac.activity, filterActivity)) : true;
        const matchesDiv = filterDivision ? (fac && fac.division === filterDivision) : true;
        const matchesReg = matchesRegionCheck(fac, filterRegion);
        const matchesYear = filterYear ? yr === filterYear.toString() : true;
        return isOilAndGas && matchesSearch && matchesAct && matchesDiv && matchesReg && matchesYear;
    });

    const getFilteredGoals = () => goals.filter(g => {
        if (!g) return false;
        const yr = String(g.year || '');
        const target = String(g.target_amount || '');
        return yr.includes(searchTerm || '') || target.includes(searchTerm || '');
    });

    const getFilteredBaseYears = () => (baseYearsData.history || []).filter((b: any) => {
        if (!b) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const yr = String(b.year || '');
        const reason = String(b.reason || '').toLowerCase();
        return yr.includes(searchTerm || '') || reason.includes(sTerm);
    });

    const getFilteredCbam = () => cbamExports.filter(item => {
        if (!item) return false;
        const sTerm = (searchTerm || '').toLowerCase();
        const fac = facilities.find(f => f && f.id === item.facility_id);
        if (filterActivity && (!fac || !matchesActivity(fac.activity, filterActivity))) return false;
        if (filterDivision && (!fac || fac.division !== filterDivision)) return false;
        if (filterRegion && filterRegion !== 'all' && !matchesRegionCheck(fac, filterRegion)) return false;
        if (filterYear && filterYear !== 'all' && item.year?.toString() !== filterYear.toString()) return false;
        if (searchTerm && !String(item.product_name || '').toLowerCase().includes(sTerm)) return false;
        return true;
    });

    const filteredFactors = getFilteredFactors();
    const filteredFacilities = getFilteredFacilities();
    const filteredProduction = getFilteredProduction();
    const filteredSources = getFilteredSources();
    const filteredMitigations = getFilteredMitigations();
    const filteredOgmp = getFilteredOgmp();
    const filteredGoals = getFilteredGoals();
    const filteredBaseYears = getFilteredBaseYears();
    const filteredCbam = getFilteredCbam();

    const isAdminLike = Boolean(user?.role && ['admin', 'superuser'].includes(user.role));
    const NAV = [
        { id: 'pending', label: 'Pending Review', icon: Clock, show: isAdminLike, count: pendingMetrics.totalCount },
        { id: 'factors', label: 'Emission Factors', show: true },
        { id: 'facilities', label: 'Regions', show: isAdminLike },
        { id: 'production', label: 'Production Data', show: true },
        { id: 'sources', label: 'Emission Sources', show: true },
        { id: 'goals', label: 'Emission Goals & Base Years', show: true },
        { id: 'mitigation', label: 'Mitigation Projects', show: true },
        { id: 'ogmp', label: 'OGMP 2.0 Surveys', show: true },
        { id: 'cbam', label: 'CBAM Products', show: true },
    ].filter((n) => n.show);
    const hasFilters = filterActivity || filterDivision || filterRegion || filterYear;
    const filterSelect = "w-auto " + controlClass;

    return (
        <div className="manage-data-page">
            <div className="manage-container">
                <div className="manage-layout mx-auto grid w-full max-w-[1600px] items-start gap-6 p-4 md:grid-cols-[240px_1fr] md:p-6">
                    {/* Sidebar Navigation */}
                    <Card as="aside" className="p-4 md:sticky md:top-6">
                        <h3 className="m-0 mb-4 ml-3 text-sm font-semibold uppercase tracking-widest text-text-secondary">Management</h3>
                        <nav aria-label="Manage data sections" className="flex flex-col gap-1">
                            {NAV.map((n) => (
                                <button
                                    key={n.id}
                                    type="button"
                                    aria-current={activeTab === n.id ? 'page' : undefined}
                                    onClick={() => handleTabChange(n.id)}
                                    className={cn(
                                        "manage-nav-item flex w-full cursor-pointer items-center justify-between gap-3 rounded-md border-0 bg-transparent px-4 py-3 text-left text-base font-medium text-text-secondary transition-colors hover:bg-ink-100 hover:text-text",
                                        activeTab === n.id && "active bg-brand-50 font-semibold text-link hover:bg-brand-50 hover:text-link",
                                    )}
                                >
                                    <span className="inline-flex items-center gap-2">
                                        {n.icon && <n.icon className="size-4" aria-hidden="true" />}
                                        {n.label}
                                    </span>
                                    {n.count && n.count > 0 ? <Badge tone="warning" className="min-w-5 justify-center px-1.5">{n.count}</Badge> : null}
                                </button>
                            ))}
                        </nav>
                    </Card>

                    {/* Content Area */}
                    <section className="min-w-0 flex-1">
                        <div className="mb-6 flex flex-wrap items-center gap-3">
                            <div className="relative min-w-[250px] flex-1">
                                <Search className="pointer-events-none absolute left-3 top-1/2 size-[18px] -translate-y-1/2 text-text-secondary" aria-hidden="true" />
                                <Input
                                    type="text"
                                    aria-label="Search records"
                                    placeholder={activeTab === 'goals' ? "Search goals or base years..." : `Search ${activeTab}...`}
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10"
                                />
                            </div>

                            {activeTab !== 'factors' && activeTab !== 'goals' && (
                                <>
                                    <NativeSelect aria-label="Activity" value={filterActivity} onChange={(e) => { setFilterActivity(e.target.value); setFilterDivision(''); }} className={filterSelect}>
                                        <option value="">All Activities</option>
                                        {activityFilterOptions.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                                    </NativeSelect>

                                    <NativeSelect aria-label="Division" value={filterDivision} onChange={(e) => setFilterDivision(e.target.value)} className={filterSelect} disabled={!filterActivity}>
                                        <option value="">All Divisions</option>
                                        {divisionFilterOptions.map(d => <option key={d} value={d}>{d}</option>)}
                                    </NativeSelect>

                                    <NativeSelect aria-label="Region" value={filterRegion} onChange={(e) => setFilterRegion(e.target.value)} className={filterSelect}>
                                        <option value="">All Regions</option>
                                        {availableFilters.regions?.map(r => <option key={r} value={r}>{r}</option>)}
                                    </NativeSelect>

                                    {(activeTab === 'production' || activeTab === 'mitigation') && (
                                        <NativeSelect aria-label="Year" value={filterYear} onChange={(e) => setFilterYear(e.target.value)} className={filterSelect}>
                                            <option value="">All Years</option>
                                            {availableFilters.years?.map(y => <option key={y} value={y}>{y}</option>)}
                                        </NativeSelect>
                                    )}

                                    {hasFilters && (
                                        <Button variant="ghost" onClick={() => { setFilterActivity(''); setFilterDivision(''); setFilterRegion(''); setFilterYear(''); }}>
                                            Clear Filters
                                        </Button>
                                    )}
                                </>
                            )}
                        </div>

                        {/* Pending Review Tab */}
                        {activeTab === 'pending' && isPrivileged && (
                            <PendingReviewTab
                                QUICK_REJECTION_REASONS={QUICK_REJECTION_REASONS}
                                facilities={facilities}
                                fetchPendingEmissions={fetchPendingEmissions}
                                filteredPendingRecords={filteredPendingRecords}
                                handleApproveAllInScope={(s) => handleApproveAllInScope(s)}
                                handleApproveSingle={handleApproveSingle}
                                handleBatchApproveSelected={handleBatchApproveSelected}
                                handleConfirmReject={handleConfirmReject}
                                handleOpenBatchRejectModal={handleOpenBatchRejectModal}
                                handleOpenRejectModal={handleOpenRejectModal}
                                handleSelectAllPendingToggle={handleSelectAllPendingToggle}
                                handleToggleSelectPending={handleToggleSelectPending}
                                isBatchWizardOpen={isBatchWizardOpen}
                                isProcessingBatch={isProcessingBatch}
                                isRefreshingPending={isRefreshingPending}
                                pendingMetrics={pendingMetrics}
                                pendingQaFilter={pendingQaFilter}
                                pendingScopeFilter={pendingScopeFilter}
                                pendingSearch={pendingSearch}
                                rejectionModal={rejectionModal}
                                selectedPendingImpactTco2e={selectedPendingImpactTco2e}
                                selectedPendingKeys={selectedPendingKeys}
                                setIsBatchWizardOpen={setIsBatchWizardOpen}
                                setPendingQaFilter={setPendingQaFilter}
                                setPendingScopeFilter={setPendingScopeFilter}
                                setPendingSearch={setPendingSearch}
                                setRejectionModal={setRejectionModal}
                                setSelectedPendingKeys={setSelectedPendingKeys}
                                user={user}
                            />
                        )}

                        {activeTab === 'pending' && !isPrivileged && (
                            <PendingAccessNotice handleTabChange={handleTabChange} />
                        )}

                        {activeTab === 'factors' && (
                            <FactorsTab
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                currentPage={currentPage}
                                editingFactorId={editingFactorId}
                                factorForm={factorForm}
                                filteredFactors={filteredFactors}
                                handleArchiveFactor={handleArchiveFactor}
                                handleApproveFactor={handleApproveFactor}
                                user={user}
                                handleDeleteFactor={handleDeleteFactor}
                                handleEditFactor={handleEditFactor}
                                handleFactorChange={handleFactorChange}
                                handleSaveFactor={handleSaveFactor}
                                setCurrentPage={setCurrentPage}
                                setEditingFactorId={setEditingFactorId}
                                setFactorForm={setFactorForm}
                                setImportModal={setImportModal}
                                setWorkbench={setWorkbench}
                                workbench={workbench}
                            />
                        )}

                        {/* Regions Tab — Admin and Superuser */}
                        {activeTab === 'facilities' && Boolean(user?.role && ['admin', 'superuser'].includes(user.role)) && (
                            <FacilitiesTab
                                ACTIVITY_LABELS={ACTIVITY_LABELS}
                                HIERARCHY={HIERARCHY}
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                currentPage={currentPage}
                                exportToCSV={exportToCSV}
                                facilities={facilities}
                                facilityForm={facilityForm}
                                filteredFacilities={filteredFacilities}
                                handleAddFacility={handleAddFacility}
                                handleDeleteFacility={handleDeleteFacility}
                                handleFacilityChange={handleFacilityChange}
                                setCurrentPage={setCurrentPage}
                                setFacilityForm={setFacilityForm}
                                setImportModal={setImportModal}
                                user={user}
                            />
                        )}

                        {/* Production Tab */}
                        {activeTab === 'production' && (
                            <ProductionTab
                                ACTIVITY_LABELS={ACTIVITY_LABELS}
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                currentPage={currentPage}
                                exportToCSV={exportToCSV}
                                facilities={facilities}
                                filteredProduction={filteredProduction}
                                getAvailableActivities={getAvailableActivities}
                                getAvailableDivisions={getAvailableDivisions}
                                handleDeleteProduction={handleDeleteProduction}
                                handleSaveProduction={handleSaveProduction}
                                isPrivileged={isPrivileged}
                                openGasConverter={openGasConverter}
                                openOilConverter={openOilConverter}
                                prodForm={prodForm}
                                productionData={productionData}
                                setCurrentPage={setCurrentPage}
                                setImportModal={setImportModal}
                                setProdForm={setProdForm}
                            />
                        )}

                        {/* Sources Tab */}
                        {activeTab === 'sources' && (
                            <SourcesTab
                                ACTIVITY_LABELS={ACTIVITY_LABELS}
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                currentPage={currentPage}
                                exportToCSV={exportToCSV}
                                facilities={facilities}
                                filteredSources={filteredSources}
                                getAvailableActivities={getAvailableActivities}
                                getAvailableDivisions={getAvailableDivisions}
                                handleDeleteSource={handleDeleteSource}
                                handleSaveSource={handleSaveSource}
                                isPrivileged={isPrivileged}
                                setCurrentPage={setCurrentPage}
                                setImportModal={setImportModal}
                                setSourceForm={setSourceForm}
                                sourceForm={sourceForm}
                                sources={sources}
                            />
                        )}

                        {/* Emission Goals & Base Years Tab */}
                        {activeTab === 'goals' && (
                            <GoalsTab
                                baseYearForm={baseYearForm}
                                baseYearsData={baseYearsData}
                                editingGoalYear={editingGoalYear}
                                filteredBaseYears={filteredBaseYears}
                                filteredGoals={filteredGoals}
                                goalForm={goalForm}
                                goals={goals}
                                handleDeleteBaseYearRecalc={handleDeleteBaseYearRecalc}
                                handleDeleteGoal={handleDeleteGoal}
                                handleEditGoal={handleEditGoal}
                                handleSaveBaseYear={handleSaveBaseYear}
                                handleSaveGoal={handleSaveGoal}
                                handleSaveSbti={handleSaveSbti}
                                hasSbti={hasSbti}
                                sbtiConfig={sbtiConfig}
                                setBaseYearForm={setBaseYearForm}
                                setEditingGoalYear={setEditingGoalYear}
                                setGoalForm={setGoalForm}
                                setSbtiConfig={setSbtiConfig}
                            />
                        )}

                        {/* Mitigation Tab */}
                        {activeTab === 'mitigation' && (
                            <MitigationTab
                                ACTIVITY_LABELS={ACTIVITY_LABELS}
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                currentPage={currentPage}
                                facilities={facilities}
                                filteredMitigations={filteredMitigations}
                                getAvailableActivities={getAvailableActivities}
                                getAvailableDivisions={getAvailableDivisions}
                                handleDeleteMitigation={handleDeleteMitigation}
                                handleSaveMitigation={handleSaveMitigation}
                                isPrivileged={isPrivileged}
                                mitigationForm={mitigationForm}
                                mitigations={mitigations}
                                setCurrentPage={setCurrentPage}
                                setImportModal={setImportModal}
                                setMitigationForm={setMitigationForm}
                            />
                        )}

                        {activeTab === 'cbam' && (
                            <CbamTab
                                ACTIVITY_LABELS={ACTIVITY_LABELS}
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                cbamForm={cbamForm}
                                currentPage={currentPage}
                                editingCbamId={editingCbamId}
                                facilities={facilities}
                                filteredCbam={filteredCbam}
                                getAvailableActivities={getAvailableActivities}
                                getAvailableDivisions={getAvailableDivisions}
                                handleDeleteCbamExport={handleDeleteCbamExport}
                                handleSaveCbamExport={handleSaveCbamExport}
                                setCbamForm={setCbamForm}
                                setCurrentPage={setCurrentPage}
                                setEditingCbamId={setEditingCbamId}
                            />
                        )}

                        {activeTab === 'ogmp' && (
                            <OgmpTab
                                ACTIVITY_LABELS={ACTIVITY_LABELS}
                                ITEMS_PER_PAGE={ITEMS_PER_PAGE}
                                NON_OG_ACTIVITIES={NON_OG_ACTIVITIES}
                                currentPage={currentPage}
                                editingOgmpId={editingOgmpId}
                                facilities={facilities}
                                filteredOgmp={filteredOgmp}
                                getAvailableActivities={getAvailableActivities}
                                getAvailableDivisions={getAvailableDivisions}
                                handleDeleteOgmpSurvey={handleDeleteOgmpSurvey}
                                handleSaveOgmpSurvey={handleSaveOgmpSurvey}
                                ogmpForm={ogmpForm}
                                setCurrentPage={setCurrentPage}
                                setEditingOgmpId={setEditingOgmpId}
                                setOgmpForm={setOgmpForm}
                            />
                        )}
                    </section>
                </div>
            </div>

            {importModal.isOpen && (
                <ColumnMappingWizard
                    type={importModal.type}
                    onClose={() => setImportModal({ ...importModal, isOpen: false })}
                    onUploadSuccess={() => {
                        if (importModal.type === 'sources') fetchSources();
                        if (importModal.type === 'custom_factors') fetchCustomFactors();
                        if (importModal.type === 'production') fetchProduction();
                        if (importModal.type === 'mitigation') fetchMitigations();
                        if (importModal.type === 'facilities') fetchFacilities();
                        if (importModal.type === 'activity') {
                            fetchProduction();
                            toast.success('Activity data imported and emissions calculated!');
                        }
                    }}
                />
            )}

            <Modal
                isOpen={convertModal.isOpen}
                onClose={() => setConvertModal(prev => ({ ...prev, isOpen: false }))}
                title={`Convert Volume (${convertModal.type === 'gas' ? 'Gas: m³ → mscf' : 'Oil: m³ → bbl'})`}
            >
                <form onSubmit={handleApplyConversion} className="p-[8px_0]!">
                    <label className="block! mb-[8px]! text-[length:0.88rem]! font-semibold! text-[color:var(--text-secondary)]!">
                        Enter volume in cubic meters (m³):
                    </label>
                    <Input
                        type="number"
                        step="any"
                        autoFocus
                        placeholder="e.g. 1000"
                        value={convertModal.value}
                        onChange={(e) => setConvertModal(prev => ({ ...prev, value: e.target.value }))}
                        className="w-full! mb-[12px]! p-[10px]!"
                    />
                    <div className="text-[length:0.8rem]! text-[color:var(--text-secondary)]! mb-[20px]!">
                        {convertModal.type === 'gas' 
                            ? 'Conversion Factor: m³ × 0.0353147 = mcf (mscf)'
                            : 'Conversion Factor: m³ × 6.28981 = barrels (bbl)'}
                    </div>
                    <div className="flex! justify-end! gap-[10px]!">
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => setConvertModal(prev => ({ ...prev, isOpen: false }))}
                        >
                            Cancel
                        </Button>
                        <Button type="submit">
                            Convert & Apply
                        </Button>
                    </div>
                </form>
            </Modal>

            <ConfirmModal
                isOpen={confirmDialog.isOpen}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmLabel={confirmDialog.confirmLabel}
                confirmVariant={confirmDialog.confirmVariant}
                onConfirm={confirmDialog.onConfirm || (() => {})}
                onCancel={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
            />
        </div>
    );
};

// FE-03 FIX: Wrap inner component in ErrorBoundary
const ManageData: React.FC = () => (
    <ErrorBoundary>
        <ManageDataInner />
    </ErrorBoundary>
);

export default ManageData;
