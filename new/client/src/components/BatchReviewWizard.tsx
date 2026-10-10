import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button, Textarea } from "../ui";
import { NativeSelect } from "../ui/NativeSelect";
import { showReviewResult } from "../utils/reviewResult";
import { createPortal } from 'react-dom';
import { 
  Sparkles, X, Check, Trash2, Search, Filter, AlertTriangle, 
  CheckCircle, RefreshCw, CheckSquare 
} from 'lucide-react';
import api from '../api';
import { useToast } from './Toast';
import { useAuth } from '../context/AuthContext';
import { getUserOperationalDefaults } from '../utils/userDefaults';
import ConfirmModal from './ConfirmModal';
import './BatchReviewWizard.css';
import { t } from "../i18n";

const QUICK_REJECTION_REASONS = [
  "Incorrect Emission Factor Applied",
  "Facility Allocation Mismatch",
  "Missing Activity Documentation",
  "Value Exceeds Operational Threshold",
  "Duplicate Batch Entry Detected",
  "Incomplete Activity Metric"
];

interface AnomalyResult {
  isWeird: boolean;
  reasons: string[];
  severity: 'clean' | 'warning' | 'danger';
}

const detectAnomalies = (record: any, facilitiesList: any[]): AnomalyResult => {
  const reasons: string[] = [];
  let severity: 'clean' | 'warning' | 'danger' = 'clean';

  // 1. Backend QA flag
  if (record.qa_flag) {
    reasons.push(record.qa_flag);
    severity = 'danger';
  }

  // 2. Zero or negative values
  const val = Number(record.co2e_total ?? record.co2e ?? 0);
  const qty = Number(record.quantity ?? record.electricity_kwh ?? record.activity_data ?? 0);
  if (val <= 0 || qty <= 0) {
    reasons.push(`Zero or negative value (Impact: ${val}, Qty: ${qty})`);
    severity = 'danger';
  }

  // 3. Extreme outliers
  if (val > 10000) {
    reasons.push(`Extreme emission spike: ${val.toLocaleString()} tCO2e`);
    if (severity !== 'danger') severity = 'warning';
  }
  if (qty > 10000000) {
    reasons.push(`High volume metric: ${qty.toLocaleString()}`);
    if (severity !== 'danger') severity = 'warning';
  }

  // 4. Unlinked / unknown facility
  const hasFac = facilitiesList?.some(f => String(f.id) === String(record.facility_id));
  if (!record.facility_id || !hasFac) {
    reasons.push(`Unlinked facility ID: #${record.facility_id || 'null'}`);
    severity = 'danger';
  }

  // 5. Temporal anomaly
  const yr = Number(record.year);
  const mo = Number(record.month);
  const currYear = new Date().getFullYear();
  if (!yr || yr < 2000 || yr > currYear + 1) {
    reasons.push(`Unusual year: ${yr}`);
    if (severity !== 'danger') severity = 'warning';
  }
  if (!mo || mo < 1 || mo > 12) {
    reasons.push(`Invalid month: ${mo}`);
    severity = 'danger';
  }

  // 6. Missing scope category info
  if (record.scope === '1' && !record.process_type && !record.fuel_type) {
    reasons.push('Missing process & fuel type');
    if (severity !== 'danger') severity = 'warning';
  }
  if (record.scope === '2' && !record.source_type) {
    reasons.push('Missing electricity/steam source');
    if (severity !== 'danger') severity = 'warning';
  }
  if (record.scope === '3' && !record.category) {
    reasons.push('Missing Scope 3 category');
    if (severity !== 'danger') severity = 'warning';
  }

  return {
    isWeird: reasons.length > 0,
    reasons,
    severity
  };
};

export interface NormalizedRecord {
  key: string;
  id: number | string;
  scope: string;
  year?: number;
  month?: number;
  date: string;
  facility_id?: number | string;
  created_by?: number | string;
  desc: string;
  tco2e: number;
  qa_flag?: string;
  isWeird: boolean;
  reasons: string[];
  severity: 'clean' | 'warning' | 'danger';
}

export interface BatchReviewWizardProps {
  isOpen: boolean;
  onClose: () => void;
  facilities?: Array<{ id: number | string; name: string }>;
}

const BatchReviewWizard: React.FC<BatchReviewWizardProps> = ({ isOpen, onClose, facilities = [] }) => {
  const { user } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [rawPending, setRawPending] = useState<{
    scope1?: any[];
    scope2?: any[];
    scope3?: any[];
    total_pending?: number;
  }>({ scope1: [], scope2: [], scope3: [], total_pending: 0 });

  // Filter States
  const [scopeFilter, setScopeFilter] = useState<string>('all'); // 'all' | '1' | '2' | '3'
  const [qaFilter, setQaFilter] = useState<string>('all'); // 'all' | 'weird' | 'clean'
  const [facilityFilter, setFacilityFilter] = useState<string>('all');
  const [yearFilter, setYearFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selection
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // Rejection Modal
  const [rejectionModal, setRejectionModal] = useState<{
    isOpen: boolean;
    mode: 'single' | 'selected' | 'all' | 'filtered';
    targetItem: NormalizedRecord | null;
    reason: string;
  }>({
    isOpen: false,
    mode: 'selected',
    targetItem: null,
    reason: ''
  });

  // Approval Confirm Modal
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: (() => Promise<void>) | null;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  // Fetch ALL pending data without exception
  const fetchAllPendingData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/emissions/pending?all=true');
      setRawPending(res.data);
    } catch (err) {
      console.error("Failed to load all pending records", err);
      toast.error(t("Failed to load pending records for wizard"));
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (isOpen) {
      fetchAllPendingData();
      setSelectedKeys(new Set());
      const opDefaults = getUserOperationalDefaults(user, facilities);
      // a reviewer of a region with several facilities sees all of them (not the first one only)
      if (opDefaults.isRestricted && opDefaults.defaultFacilityId && (facilities || []).length === 1) {
        setFacilityFilter(String(opDefaults.defaultFacilityId));
      }
    }
  }, [isOpen, fetchAllPendingData, user, facilities]);

  // Handle ESC key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !rejectionModal.isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, rejectionModal.isOpen]);

  // Normalize all records with anomaly detection
  const normalizedRecords = useMemo<NormalizedRecord[]>(() => {
    const list: NormalizedRecord[] = [];

    (rawPending.scope1 || []).forEach(r => {
      const anomaly = detectAnomalies(r, facilities);
      list.push({
        key: `1-${r.id}`,
        id: r.id,
        scope: '1',
        year: r.year,
        month: r.month,
        date: `${r.year}-${String(r.month || 1).padStart(2, '0')}`,
        facility_id: r.facility_id,
        created_by: r.created_by,
        desc: `${r.process_type || 'General'} · ${r.fuel_type || ''} (${Number(r.quantity || 0).toLocaleString()} ${r.unit || ''})`,
        tco2e: Number(r.co2e_total || 0),
        qa_flag: r.qa_flag,
        ...anomaly
      });
    });

    (rawPending.scope2 || []).forEach(r => {
      const anomaly = detectAnomalies(r, facilities);
      list.push({
        key: `2-${r.id}`,
        id: r.id,
        scope: '2',
        year: r.year,
        month: r.month,
        date: `${r.year}-${String(r.month || 1).padStart(2, '0')}`,
        facility_id: r.facility_id,
        created_by: r.created_by,
        desc: `${r.source_type || 'Electricity'} (${Number(r.electricity_kwh || 0).toLocaleString()} kWh)`,
        tco2e: Number(r.co2e || 0),
        qa_flag: r.qa_flag,
        ...anomaly
      });
    });

    (rawPending.scope3 || []).forEach(r => {
      const anomaly = detectAnomalies(r, facilities);
      list.push({
        key: `3-${r.id}`,
        id: r.id,
        scope: '3',
        year: r.year,
        month: r.month,
        date: `${r.year}-${String(r.month || 1).padStart(2, '0')}`,
        facility_id: r.facility_id,
        created_by: r.created_by,
        desc: `${r.category || 'Scope 3'}${r.sub_category ? ` · ${r.sub_category}` : ''}`,
        tco2e: Number(r.co2e || 0),
        qa_flag: r.qa_flag,
        ...anomaly
      });
    });

    return list;
  }, [rawPending, facilities]);

  // Overall statistics
  const stats = useMemo(() => {
    const totalCount = normalizedRecords.length;
    const totalTco2e = normalizedRecords.reduce((acc, r) => acc + r.tco2e, 0);
    const count1 = normalizedRecords.filter(r => r.scope === '1').length;
    const count2 = normalizedRecords.filter(r => r.scope === '2').length;
    const count3 = normalizedRecords.filter(r => r.scope === '3').length;
    const weirdCount = normalizedRecords.filter(r => r.isWeird).length;
    const cleanCount = totalCount - weirdCount;

    return { totalCount, totalTco2e, count1, count2, count3, weirdCount, cleanCount };
  }, [normalizedRecords]);

  // Available unique years in records
  const availableYears = useMemo(() => {
    const years = new Set<number>();
    normalizedRecords.forEach(r => {
      if (r.year) years.add(r.year);
    });
    return Array.from(years).sort((a, b) => b - a);
  }, [normalizedRecords]);

  // Filtered Records
  const filteredRecords = useMemo(() => {
    return normalizedRecords.filter(item => {
      if (scopeFilter !== 'all' && item.scope !== scopeFilter) return false;
      if (qaFilter === 'weird' && !item.isWeird) return false;
      if (qaFilter === 'clean' && item.isWeird) return false;
      if (facilityFilter !== 'all' && String(item.facility_id) !== String(facilityFilter)) return false;
      if (yearFilter !== 'all' && String(item.year) !== String(yearFilter)) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const facName = facilities.find(f => f.id === item.facility_id)?.name?.toLowerCase() || '';
        const matchId = String(item.id).includes(q);
        const matchDate = item.date.toLowerCase().includes(q);
        const matchDesc = item.desc.toLowerCase().includes(q);
        const matchFac = facName.includes(q) || String(item.facility_id).includes(q);
        const matchReason = item.reasons.some(r => r.toLowerCase().includes(q));
        if (!matchId && !matchDate && !matchDesc && !matchFac && !matchReason) return false;
      }

      return true;
    });
  }, [normalizedRecords, scopeFilter, qaFilter, facilityFilter, yearFilter, searchQuery, facilities]);

  // Selected Impact
  const selectedImpactTco2e = useMemo(() => {
    let total = 0;
    normalizedRecords.forEach(r => {
      if (selectedKeys.has(r.key)) total += r.tco2e;
    });
    return total;
  }, [normalizedRecords, selectedKeys]);

  // Select all visible / Deselect all
  const handleToggleSelectAllInView = () => {
    const visibleKeys = filteredRecords.map(r => r.key);
    const allVisibleSelected = visibleKeys.length > 0 && visibleKeys.every(k => selectedKeys.has(k));

    setSelectedKeys(prev => {
      const next = new Set(prev);
      if (allVisibleSelected) {
        visibleKeys.forEach(k => next.delete(k));
      } else {
        visibleKeys.forEach(k => next.add(k));
      }
      return next;
    });
  };

  // Select All Weird Records
  const handleSelectAllWeird = () => {
    const weirdKeys = filteredRecords.filter(r => r.isWeird).map(r => r.key);
    if (weirdKeys.length === 0) {
      toast.info(t("No anomalous records in current view"));
      return;
    }
    setSelectedKeys(new Set(weirdKeys));
    toast.info(`Selected ${weirdKeys.length} anomalous records for review`);
  };

  // Toggle single item selection
  const handleToggleKey = (key: string) => {
    setSelectedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // ── Actions ─────────────────────────────────────────────────────────────

  // Single Approve
  const handleApproveSingle = async (scope: string, id: number | string) => {
    try {
      await api.post(`/emissions/approve/${id}`, { scope: String(scope) });
      toast.success(t("Record verified and committed to inventory"));
      setSelectedKeys(prev => {
        const next = new Set(prev);
        next.delete(`${scope}-${id}`);
        return next;
      });
      fetchAllPendingData();
    } catch (err: any) {
      toast.error(err.response?.data?.error || t("Failed to approve record"));
    }
  };

  // Approve Selected
  const handleApproveSelected = async () => {
    if (selectedKeys.size === 0) return;
    setIsProcessing(true);
    try {
      const by_scope: Record<string, number[]> = { "1": [], "2": [], "3": [] };
      const ids: number[] = [];
      selectedKeys.forEach(k => {
        const [scope, id] = k.split('-');
        if (by_scope[scope]) by_scope[scope].push(Number(id));
        ids.push(Number(id));
      });

      const res = await api.post('/emissions/approve/batch', {
        scope: "all",
        ids,
        by_scope
      });

      showReviewResult(toast, "approved", res.data.approved_count, selectedKeys.size, res.data.skipped);
      setSelectedKeys(new Set());
      fetchAllPendingData();
    } catch (err: any) {
      toast.error(err.response?.data?.error || t("Failed to approve selected records"));
    } finally {
      setIsProcessing(false);
    }
  };

  // Approve All (Global or Filtered)
  const handleApproveAll = (isFiltered = false) => {
    const targetCount = isFiltered ? filteredRecords.length : stats.totalCount;
    if (targetCount === 0) return;

    const msg = isFiltered
      ? `Approve all ${targetCount} currently filtered records across active criteria?`
      : `Approve ALL ${targetCount} pending records in the system across all scopes?`;

    setConfirmModal({
      isOpen: true,
      title: isFiltered ? "Batch Approve Filtered Records" : "Batch Approve All Records",
      message: msg,
      onConfirm: async () => {
        setConfirmModal(prev => ({ ...prev, isOpen: false }));
        setIsProcessing(true);
        try {
          if (!isFiltered) {
            // Pure global approve all
            const res = await api.post('/emissions/approve/batch', {
              scope: "all",
              approve_all: true
            });
            showReviewResult(toast, "approved", res.data.approved_count, undefined, res.data.skipped);
          } else {
            // Scoped to current filters
            const by_scope: Record<string, number[]> = { "1": [], "2": [], "3": [] };
            const ids: number[] = [];
            filteredRecords.forEach(r => {
              by_scope[r.scope].push(Number(r.id));
              ids.push(Number(r.id));
            });
            const res = await api.post('/emissions/approve/batch', {
              scope: "all",
              ids,
              by_scope
            });
            showReviewResult(toast, "approved", res.data.approved_count, undefined, res.data.skipped);
          }
          setSelectedKeys(new Set());
          fetchAllPendingData();
        } catch (err: any) {
          toast.error(err.response?.data?.error || t("Batch approval failed"));
        } finally {
          setIsProcessing(false);
        }
      }
    });
  };

  // Confirm Rejection Modal Submission
  const handleConfirmRejection = async () => {
    if (!rejectionModal.reason.trim()) {
      toast.warning(t("Please provide or select a rejection justification"));
      return;
    }

    setIsProcessing(true);
    try {
      const reason = rejectionModal.reason.trim();

      if (rejectionModal.mode === 'single' && rejectionModal.targetItem) {
        await api.post(`/emissions/reject/${rejectionModal.targetItem.id}`, {
          scope: rejectionModal.targetItem.scope,
          reason
        });
        toast.success(t("Record rejected and removed"));
      } else if (rejectionModal.mode === 'selected') {
        const by_scope: Record<string, number[]> = { "1": [], "2": [], "3": [] };
        const ids: number[] = [];
        selectedKeys.forEach(k => {
          const [scope, id] = k.split('-');
          if (by_scope[scope]) by_scope[scope].push(Number(id));
          ids.push(Number(id));
        });
        const res = await api.post('/emissions/reject/batch', {
          scope: "all",
          ids,
          by_scope,
          reason
        });
        showReviewResult(toast, "rejected", res.data.rejected_count ?? res.data.deleted_count, selectedKeys.size, res.data.skipped);
      } else if (rejectionModal.mode === 'all') {
        const res = await api.post('/emissions/reject/batch', {
          scope: "all",
          reject_all: true,
          reason
        });
        showReviewResult(toast, "rejected", res.data.rejected_count ?? res.data.deleted_count, undefined, res.data.skipped);
      } else if (rejectionModal.mode === 'filtered') {
        const by_scope: Record<string, number[]> = { "1": [], "2": [], "3": [] };
        const ids: number[] = [];
        filteredRecords.forEach(r => {
          by_scope[r.scope].push(Number(r.id));
          ids.push(Number(r.id));
        });
        const res = await api.post('/emissions/reject/batch', {
          scope: "all",
          ids,
          by_scope,
          reason
        });
        showReviewResult(toast, "rejected", res.data.rejected_count ?? res.data.deleted_count, undefined, res.data.skipped);
      }

      setRejectionModal({ isOpen: false, mode: 'selected', targetItem: null, reason: '' });
      setSelectedKeys(new Set());
      fetchAllPendingData();
    } catch (err: any) {
      toast.error(err.response?.data?.error || t("Failed to reject record(s)"));
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  const modalContent = (
    <div role="presentation" className="[position:fixed] [inset:0] [background:rgba(15,_23,_42,_0.65)] [backdrop-filter:blur(8px)] [-webkit-backdrop-filter:blur(8px)] [z-index:10000] [display:flex] [align-items:center] [justify-content:center] [padding:24px] [animation:wizardFadeIn_0.2s_cubic-bezier(0.16,_1,_0.3,_1)]" onClick={(e) => { if (e.target === e.currentTarget && !rejectionModal.isOpen) onClose(); }}>
      <div className="[background:var(--bg-card-elevated,_var(--color-white))] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.9))] [&&]:[border-radius:var(--radius-lg)] [width:100%] [max-width:1440px] [height:calc(100vh_-_48px)] [max-height:940px] [display:flex] [flex-direction:column] [box-shadow:var(--shadow-overlay)] [overflow:hidden] [animation:wizardSlideUp_0.25s_cubic-bezier(0.16,_1,_0.3,_1)]">
        {/* ── Wizard Header ── */}
        <div className="[padding:18px_28px] [border-bottom:1px_solid_var(--border-color,_var(--color-ink-200))] [background:rgba(255,_255,_255,_0.95)] [display:flex] [justify-content:space-between] [align-items:center] [gap:20px] [flex-shrink:0]">
          <div className="[display:flex] [align-items:center] [gap:14px]">
            <div className="[width:44px] [height:44px] [border-radius:var(--radius-md)] [background:linear-gradient(135deg,_rgba(255,_102,_0,_0.15)_0%,_rgba(255,_102,_0,_0.05)_100%)] [border:1px_solid_rgba(255,_102,_0,_0.25)] [color:var(--color-link)] [display:flex] [align-items:center] [justify-content:center] [flex-shrink:0]">
              <Sparkles size={24} />
            </div>
            <div className="wizard-title-text">
              <h2>{t("Pending Data Audit & Verification Wizard")}</h2>
              <p>{t("Unrestricted Maker-Checker verification pipeline · Auditing 100% of staged records across Scope 1, 2, and 3")}</p>
            </div>
          </div>

          <div className="[display:flex] [align-items:center] [gap:12px]">
            <Button
              variant="ghost" type="button"
              onClick={fetchAllPendingData}
              disabled={loading || isProcessing}
              className="[display:inline-flex]! [align-items:center]! [gap:6px]! [border:1px_solid_var(--border-color)]! [border-radius:9px]! [padding:7px_14px]! [font-size:0.82rem]! [background:var(--color-white)]! [cursor:pointer]!"
            >
              <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
              {t("Reload All")}
            </Button>
            <Button
              variant="ghost" type="button"
              onClick={onClose}
              className="[padding:7px]! [border-radius:9px]! [border:1px_solid_var(--border-color)]! [cursor:pointer]! [background:var(--color-white)]!"
              title={t("Close Wizard (Esc)")}
            >
              <X size={18} />
            </Button>
          </div>
        </div>

        {/* ── KPI Summary Strip ── */}
        <div className="[padding:14px_28px] [background:var(--bg-body,_var(--color-ink-50))] [border-bottom:1px_solid_var(--border-color,_var(--color-ink-200))] [display:flex] [align-items:center] [justify-content:space-between] [gap:16px] [flex-wrap:wrap] [flex-shrink:0]">
          <div className="[display:flex] [align-items:center] [gap:10px] [flex-wrap:wrap]">
            <div className="kpi-chip">
              <span>{t("Total Staged:")}</span>
              <strong>{stats.totalCount}{" "}{t("records")}</strong>
            </div>
            <div className="kpi-chip">
              <span>{t("Cumulative Impact:")}</span>
              <strong>{stats.totalTco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{" "}{t("tCO₂e")}</strong>
            </div>
            <div className="kpi-chip">
              <span>{t("Scope Distribution:")}</span>
              <strong>S1({stats.count1}) S2({stats.count2}) S3({stats.count3})</strong>
            </div>
            <div className={`kpi-chip ${stats.weirdCount > 0 ? 'weird' : ''}`}>
              <AlertTriangle size={14} />
              <span>{t("Suspicious / Weird:")}</span>
              <strong>{stats.weirdCount}{" "}{t("flagged")}</strong>
            </div>
          </div>

          <div className="flex! gap-[10px]! items-center!">
            {stats.weirdCount > 0 && (
              <button
                type="button"
                className="[display:inline-flex] [align-items:center] [gap:6px] [padding:8px_14px] [border-radius:var(--radius-md)] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:rgba(245,_158,_11,_0.12)] [color:var(--color-amber-700)] [&&]:[border-color:rgba(245,_158,_11,_0.3)] hover:[background:var(--color-amber-700)] hover:[color:var(--color-white)]"
                onClick={handleSelectAllWeird}
                title={t("Select all flagged anomalies for batch rejection or inspection")}
              >
                <AlertTriangle size={14} />
                {t("Select All Weird (")}{stats.weirdCount})
              </button>
            )}
            <button
              type="button"
              className="[display:inline-flex] [align-items:center] [gap:6px] [padding:8px_14px] [border-radius:var(--radius-md)] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:var(--color-green-700)] [color:var(--color-white)] hover:[background:var(--color-green-600)] hover:[transform:translateY(-1px)] hover:[box-shadow:0_3px_8px_rgba(16,_185,_129,_0.3)]"
              onClick={() => handleApproveAll(false)}
              disabled={loading || isProcessing || stats.totalCount === 0}
              title={t("Verify all pending records across all scopes without exception")}
            >
              <Check size={14} />
              {t("Approve All (")}{stats.totalCount})
            </button>
            <button
              type="button"
              className="[display:inline-flex] [align-items:center] [gap:6px] [padding:8px_14px] [border-radius:var(--radius-md)] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:rgba(239,_68,_68,_0.1)] [color:var(--color-red-700)] [&&]:[border-color:rgba(239,_68,_68,_0.25)] hover:[background:var(--color-red-700)] hover:[color:var(--color-white)] hover:[transform:translateY(-1px)] hover:[box-shadow:0_3px_8px_rgba(239,_68,_68,_0.3)]"
              onClick={() => setRejectionModal({ isOpen: true, mode: 'all', targetItem: null, reason: '' })}
              disabled={loading || isProcessing || stats.totalCount === 0}
              title={t("Delete all pending records with audit justification")}
            >
              <Trash2 size={14} />
              {t("Delete All (")}{stats.totalCount})
            </button>
          </div>
        </div>

        {/* ── Toolbar: Filters & Filtered Actions ── */}
        <div className="[padding:12px_28px] [border-bottom:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--color-white)] [display:flex] [align-items:center] [justify-content:space-between] [gap:16px] [flex-wrap:wrap] [flex-shrink:0]">
          <div className="[display:flex] [align-items:center] [gap:10px] [flex-wrap:wrap]">
            {/* Scope Tabs */}
            <div className="[display:inline-flex] [background:var(--bg-body,_var(--color-ink-100))] [border-radius:var(--radius-md)] [padding:3px] [gap:3px]">
              <button type="button" className={`segmented-item-btn ${scopeFilter === 'all' ? 'active' : ''}`} onClick={() => setScopeFilter('all')}>
                {t("All Scopes (")}{stats.totalCount})
              </button>
              <button type="button" className={`segmented-item-btn ${scopeFilter === '1' ? 'active' : ''}`} onClick={() => setScopeFilter('1')}>
                {t("Scope 1 (")}{stats.count1})
              </button>
              <button type="button" className={`segmented-item-btn ${scopeFilter === '2' ? 'active' : ''}`} onClick={() => setScopeFilter('2')}>
                {t("Scope 2 (")}{stats.count2})
              </button>
              <button type="button" className={`segmented-item-btn ${scopeFilter === '3' ? 'active' : ''}`} onClick={() => setScopeFilter('3')}>
                {t("Scope 3 (")}{stats.count3})
              </button>
            </div>

            {/* QA Anomaly Filter */}
            <div className="[display:inline-flex] [background:var(--bg-body,_var(--color-ink-100))] [border-radius:var(--radius-md)] [padding:3px] [gap:3px]">
              <button type="button" className={`segmented-item-btn ${qaFilter === 'all' ? 'active' : ''}`} onClick={() => setQaFilter('all')}>
                {t("All Data")}
              </button>
              <button type="button" className={`segmented-item-btn ${qaFilter === 'weird' ? 'active weird-active' : ''}`} onClick={() => setQaFilter('weird')}>
                <AlertTriangle size={13} />
                {t("Weird Only (")}{stats.weirdCount})
              </button>
              <button type="button" className={`segmented-item-btn ${qaFilter === 'clean' ? 'active' : ''}`} onClick={() => setQaFilter('clean')}>
                <CheckCircle size={13} color="var(--color-green-500)" />
                {t("Clean Only (")}{stats.cleanCount})
              </button>
            </div>

            {/* Facility Select */}
            <NativeSelect
              value={facilityFilter}
              onChange={(e) => setFacilityFilter(e.target.value)}
              className="component-select [width:auto]! [padding:6px_30px_6px_12px]! [font-size:0.8rem]! [height:34px]!"
             
            >
              <option value="all">{t("All Facilities")}</option>
              {facilities.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </NativeSelect>

            {/* Year Select */}
            {availableYears.length > 0 && (
              <NativeSelect
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
                className="component-select [width:auto]! [padding:6px_30px_6px_12px]! [font-size:0.8rem]! [height:34px]!"
               
              >
                <option value="all">{t("All Years")}</option>
                {availableYears.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </NativeSelect>
            )}

            {/* Search Box */}
            <div className="[display:flex] [align-items:center] [gap:8px] [background:var(--bg-body,_var(--color-ink-100))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-md)] [padding:6px_12px] [min-width:220px] [transition:border-color_0.2s] focus-within:[border-color:var(--accent-color,_var(--color-brand-500))] focus-within:[background:var(--color-white)] focus-within:[box-shadow:0_0_0_3px_rgba(255,_102,_0,_0.12)]">
              <Search size={14} color="var(--text-secondary)" />
              <input
                type="text"
                placeholder={t("Search by facility, fuel, category...")}
                className="[border:none] [background:transparent] [font-size:var(--text-base)] [color:var(--text-primary,_var(--color-ink-900))] [width:100%] [outline:none]"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <Button variant="ghost" type="button" onClick={() => setSearchQuery('')} className="p-[2px]! cursor-pointer!">
                  <X size={12} />
                </Button>
              )}
            </div>
          </div>

          <div className="[display:flex] [align-items:center] [gap:10px] [flex-wrap:wrap]">
            <span className="text-[length:0.8rem]! text-[color:var(--text-secondary)]! font-semibold!">
              {t("Showing")}{" "}{filteredRecords.length}{" "}{t("of")}{" "}{stats.totalCount}
            </span>

            {/* Action on Filtered Set */}
            {(scopeFilter !== 'all' || qaFilter !== 'all' || facilityFilter !== 'all' || yearFilter !== 'all' || searchQuery) && filteredRecords.length > 0 && (
              <div className="flex! gap-[8px]!">
                <button
                  type="button"
                  className="[display:inline-flex] [align-items:center] [gap:6px] [border-radius:var(--radius-md)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:var(--color-green-700)] [color:var(--color-white)] hover:[background:var(--color-green-600)] hover:[transform:translateY(-1px)] hover:[box-shadow:0_3px_8px_rgba(16,_185,_129,_0.3)] p-[6px_12px]! text-[length:0.78rem]!"
                  onClick={() => handleApproveAll(true)}
                  disabled={isProcessing}
                >
                  <Check size={13} />
                  {t("Approve Filtered (")}{filteredRecords.length})
                </button>
                <button
                  type="button"
                  className="[display:inline-flex] [align-items:center] [gap:6px] [border-radius:var(--radius-md)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:rgba(239,_68,_68,_0.1)] [color:var(--color-red-700)] [&&]:[border-color:rgba(239,_68,_68,_0.25)] hover:[background:var(--color-red-700)] hover:[color:var(--color-white)] hover:[transform:translateY(-1px)] hover:[box-shadow:0_3px_8px_rgba(239,_68,_68,_0.3)] p-[6px_12px]! text-[length:0.78rem]!"
                  onClick={() => setRejectionModal({ isOpen: true, mode: 'filtered', targetItem: null, reason: '' })}
                  disabled={isProcessing}
                >
                  <Trash2 size={13} />
                  {t("Reject Filtered (")}{filteredRecords.length})
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── Floating Selected Batch Bar ── */}
        {selectedKeys.size > 0 && (
          <div className="[padding:10px_28px] [background:linear-gradient(135deg,_var(--color-ink-800)_0%,_var(--color-ink-900)_100%)] [color:var(--color-white)] [display:flex] [align-items:center] [justify-content:space-between] [gap:16px] [flex-shrink:0] [animation:wizardBannerIn_0.2s_ease-out]">
            <div className="flex! items-center! gap-[14px]!">
              <span className="font-bold! text-[length:0.92rem]! inline-flex! items-center! gap-[8px]!">
                <CheckSquare size={16} color="var(--color-legacy-38bdf8)" />
                {selectedKeys.size}{" "}{t("record")}{selectedKeys.size > 1 ? 's' : ''}{" "}{t("selected")}
              </span>
              <span className="text-[color:rgba(255,255,255,0.4)]!">•</span>
              <span className="text-[length:0.84rem]! text-[color:var(--color-ink-300)]!">
                {t("Impact:")}{" "}<strong className="text-[color:var(--color-white)]!">{selectedImpactTco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>{" "}{t("tCO₂e")}
              </span>
            </div>

            <div className="flex! gap-[10px]! items-center!">
              <button
                type="button"
                className="[display:inline-flex] [align-items:center] [gap:6px] [padding:8px_14px] [border-radius:var(--radius-md)] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:var(--color-green-700)] [color:var(--color-white)] hover:[background:var(--color-green-600)] hover:[transform:translateY(-1px)] hover:[box-shadow:0_3px_8px_rgba(16,_185,_129,_0.3)]"
                onClick={handleApproveSelected}
                disabled={isProcessing}
              >
                <Check size={14} />
                {t("Approve Selected (")}{selectedKeys.size})
              </button>
              <button
                type="button"
                className="[display:inline-flex] [align-items:center] [gap:6px] [padding:8px_14px] [border-radius:var(--radius-md)] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [border:1px_solid_transparent] [transition:all_0.15s_ease] [background:rgba(239,_68,_68,_0.1)] [color:var(--color-red-700)] [&&]:[border-color:rgba(239,_68,_68,_0.25)] hover:[background:var(--color-red-700)] hover:[color:var(--color-white)] hover:[transform:translateY(-1px)] hover:[box-shadow:0_3px_8px_rgba(239,_68,_68,_0.3)]"
                onClick={() => setRejectionModal({ isOpen: true, mode: 'selected', targetItem: null, reason: '' })}
                disabled={isProcessing}
              >
                <X size={14} />
                {t("Reject Selected (")}{selectedKeys.size})
              </button>
              <Button
                variant="ghost" type="button"
                onClick={() => setSelectedKeys(new Set())}
                className="text-[color:var(--color-ink-600)]! text-[length:0.82rem]! p-[6px_10px]! cursor-pointer!"
              >
                {t("Deselect")}
              </Button>
            </div>
          </div>
        )}

        {/* ── Table Body ── */}
        <div className="[flex:1] [overflow-y:auto] [overflow-x:auto] [padding:0] [position:relative]">
          {loading ? (
            <div className="[padding:64px_24px] [text-align:center] [display:flex] [flex-direction:column] [align-items:center] [gap:14px] [color:var(--text-secondary,_var(--color-ink-500))]">
              <RefreshCw size={36} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-link)' }} />
              <p className="font-semibold!">{t("Loading 100% of pending records across all scopes...")}</p>
            </div>
          ) : stats.totalCount === 0 ? (
            <div className="[padding:64px_24px] [text-align:center] [display:flex] [flex-direction:column] [align-items:center] [gap:14px] [color:var(--text-secondary,_var(--color-ink-500))]">
              <div className="[width:64px] [height:64px] [border-radius:var(--radius-lg)] [background:rgba(16,_185,_129,_0.1)] [color:var(--color-green-700)] [display:flex] [align-items:center] [justify-content:center]">
                <CheckCircle size={32} />
              </div>
              <h3 className="m-[0px]! text-[length:1.2rem]! text-[color:var(--text-primary)]!">{t("All Pending Data Verified")}</h3>
              <p className="m-[0px]! max-w-[460px]! text-[length:0.88rem]!">
                {t("There are currently no records awaiting Maker-Checker approval. Staged bulk import entries will appear here automatically.")}
              </p>
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="[padding:64px_24px] [text-align:center] [display:flex] [flex-direction:column] [align-items:center] [gap:14px] [color:var(--text-secondary,_var(--color-ink-500))]">
              <Filter size={32} color="var(--text-muted)" />
              <h3 className="m-[0px]! text-[length:1.1rem]!">{t("No Matching Records")}</h3>
              <p className="m-[0px]! text-[length:0.86rem]!">{t("No records match your active scope, anomaly, or search filters.")}</p>
              <Button
                variant="ghost" type="button"
                onClick={() => { setScopeFilter('all'); setQaFilter('all'); setFacilityFilter('all'); setYearFilter('all'); setSearchQuery(''); }}
                className="[border:1px_solid_var(--border-color)]! [border-radius:8px]! [padding:6px_14px]! [font-size:0.82rem]! [margin-top:8px]! [cursor:pointer]!"
              >
                {t("Reset Filters")}
              </Button>
            </div>
          ) : (
            <table className="wizard-table">
              <thead>
                <tr>
                  <th className="w-[44px]! text-center!">
                    <input
                      type="checkbox"
                      className="cursor-pointer!"
                      checked={filteredRecords.length > 0 && filteredRecords.every(r => selectedKeys.has(r.key))}
                      onChange={handleToggleSelectAllInView}
                    />
                  </th>
                  <th className="w-[80px]!">{t("Ref ID")}</th>
                  <th className="w-[90px]!">{t("Scope")}</th>
                  <th className="w-[100px]!">{t("Period")}</th>
                  <th className="min-w-[160px]!">{t("Facility")}</th>
                  <th className="min-w-[240px]!">{t("Activity Details")}</th>
                  <th className="w-[130px]! text-right!">{t("Emissions")}</th>
                  <th className="w-[190px]!">{t("Integrity Status")}</th>
                  <th className="w-[100px]! text-center!">{t("Review Action")}</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map(item => {
                  const isSelected = selectedKeys.has(item.key);
                  const facName = facilities.find(f => f.id === item.facility_id)?.name || (item.facility_id ? `Facility #${item.facility_id}` : 'Unassigned');

                  return (
                    <tr key={item.key} className={`${isSelected ? 'row-selected' : ''} ${item.isWeird ? 'row-weird' : ''}`}>
                      <td className="text-center!">
                        <input
                          type="checkbox"
                          className="cursor-pointer!"
                          checked={isSelected}
                          onChange={() => handleToggleKey(item.key)}
                        />
                      </td>
                      <td>
                        <span className="font-mono! text-[length:0.8rem]! text-[color:var(--text-secondary)]!">
                          #{String(item.id).slice(-5)}
                        </span>
                      </td>
                      <td>
                        <span className={`scope-tag scope-tag-${item.scope}`}>
                          {t("Scope")}{" "}{item.scope}
                        </span>
                      </td>
                      <td>
                        <span className="font-medium!">{item.date}</span>
                      </td>
                      <td>
                        <span className="font-semibold! text-[color:var(--text-primary)]!">{facName}</span>
                      </td>
                      <td>
                        <div className="flex! flex-col! gap-[2px]!">
                          <span className="text-[length:0.84rem]!">{item.desc}</span>
                        </div>
                      </td>
                      <td className="text-right!">
                        <strong className="num-tabular text-[length:0.9rem]!">
                          {item.tco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </strong>
                        <span className="text-[length:0.75rem]! text-[color:var(--text-secondary)]! ml-[4px]!">{t("tCO₂e")}</span>
                      </td>
                      <td>
                        {item.isWeird ? (
                          <div className="flex! flex-col! gap-[3px]!">
                            <span
                              className={`anomaly-pill ${item.severity}`}
                              title={item.reasons.join(" · ")}
                            >
                              <AlertTriangle size={12} />
                              {item.severity === 'danger' ? t("Suspicious Data") : t("Notice")}
                            </span>
                            <span className={`[font-size:0.72rem]! [line-height:1.2]! ${item.severity === 'danger' ? "[color:var(--color-red-600)]!" : "[color:var(--color-amber-700)]!"}`}>
                              {item.reasons[0]}
                              {item.reasons.length > 1 && ` (+${item.reasons.length - 1} more)`}
                            </span>
                          </div>
                        ) : (
                          <span className="anomaly-pill clean">
                            <Check size={12} />
                            {t("Verified Structure")}
                          </span>
                        )}
                      </td>
                      <td className="text-center!">
                        <div className="[display:flex] [align-items:center] [gap:8px] justify-center!">
                          {item.created_by && String(item.created_by) === String(user?.id) ? (
                            <span 
                              className="badge-maker text-[length:0.7rem]! p-[4px_8px]! rounded-[6px]! bg-[color:rgba(239,_68,_68,_0.1)]! text-[color:var(--color-red-700)]! [border:1px_solid_rgba(239,_68,_68,_0.25)]! font-semibold! whitespace-nowrap!"
                             
                              title={t("Maker-Checker: You created this record and cannot self-approve.")}
                            >
                              {t("Self-Submitted")}
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="btn-review-action approve"
                              title={t("Approve & Commit")}
                              onClick={() => handleApproveSingle(item.scope, item.id)}
                            >
                              <Check size={16} />
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn-review-action reject"
                            title={t("Reject (Specify Reason)")}
                            onClick={() => setRejectionModal({ isOpen: true, mode: 'single', targetItem: item, reason: '' })}
                          >
                            <X size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Nested Rejection Reason Prompt Modal ── */}
      {rejectionModal.isOpen && (
        <div role="presentation" className="[position:fixed] [inset:0] [background:rgba(15,_23,_42,_0.5)] [backdrop-filter:blur(6px)] [display:flex] [align-items:center] [justify-content:center] [z-index:1000] [animation:fadeIn_0.2s_ease-out]" onClick={(e) => { if (e.target === e.currentTarget && !isProcessing) setRejectionModal(prev => ({ ...prev, isOpen: false })); }}>
          <div className="[background:var(--bg-card-elevated)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [width:90%] [max-width:520px] [padding:28px] [box-shadow:var(--shadow-card-elevated)] [display:flex] [flex-direction:column] [gap:20px] [animation:scaleUp_0.25s_cubic-bezier(0.16,_1,_0.3,_1)]">
            <div className="flex! justify-between! items-center!">
              <div className="flex! items-center! gap-[10px]!">
                <div className="w-[36px]! h-[36px]! rounded-[10px]! bg-[color:rgba(239,_68,_68,_0.1)]! text-[color:var(--color-red-600)]! flex! items-center! justify-center!">
                  <Trash2 size={20} />
                </div>
                <h3 className="m-[0px]! font-bold! text-[length:1.1rem]!">
                  {rejectionModal.mode === 'single'
                    ? `Reject Record #${rejectionModal.targetItem?.id}`
                    : rejectionModal.mode === 'selected'
                    ? `Reject ${selectedKeys.size} Selected Records`
                    : rejectionModal.mode === 'all'
                    ? `Delete ALL ${stats.totalCount} Pending Records`
                    : `Reject ${filteredRecords.length} Filtered Records`}
                </h3>
              </div>
              <Button
                variant="ghost" type="button"
                onClick={() => !isProcessing && setRejectionModal(prev => ({ ...prev, isOpen: false }))}
                className="p-[6px]! cursor-pointer!"
              >
                <X size={18} />
              </Button>
            </div>

            <p className="m-[0px]! text-[length:0.86rem]! text-[color:var(--text-secondary)]! leading-[1.5]!">
              {t("Maker-Checker governance requires a recorded audit reason before rejecting staged bulk entries. This justification will be logged in the tamper-evident audit trail.")}
            </p>

            <div>
              <label className="block! mb-[8px]! text-[length:0.78rem]! font-semibold! text-[color:var(--text-secondary)]! uppercase!">
                {t("Quick Audit Justifications")}
              </label>
              <div className="[display:flex] [flex-wrap:wrap] [gap:8px]">
                {QUICK_REJECTION_REASONS.map(reason => (
                  <button
                    key={reason}
                    type="button"
                    className={`rejection-chip ${rejectionModal.reason === reason ? 'selected' : ''}`}
                    onClick={() => setRejectionModal(prev => ({ ...prev, reason }))}
                  >
                    {reason}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block! mb-[8px]! text-[length:0.78rem]! font-semibold! text-[color:var(--text-secondary)]! uppercase!">
                {t("Custom Justification / Details")}
              </label>
              <Textarea
               
                rows={3}
                placeholder={t("Describe reason for refusal...")}
                value={rejectionModal.reason}
                onChange={(e) => setRejectionModal(prev => ({ ...prev, reason: e.target.value }))}
                className="[resize:vertical]!"
              />
            </div>

            <div className="flex! justify-end! gap-[10px]!">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setRejectionModal(prev => ({ ...prev, isOpen: false }))}
                disabled={isProcessing}
                className="p-[8px_16px]! rounded-[10px]! cursor-pointer!"
              >
                {t("Cancel")}
              </Button>
              <Button
                type="button"
                
                className="bg-[color:var(--color-red-500)]! p-[8px_18px]! rounded-[10px]!"
                onClick={handleConfirmRejection}
                disabled={isProcessing || !rejectionModal.reason.trim()}
              >
                {isProcessing ? t("Processing...") : t("Confirm Rejection")}
              </Button>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmLabel={t("Approve Records")}
        confirmVariant="primary"
        loading={isProcessing}
        onConfirm={confirmModal.onConfirm || (() => {})}
        onCancel={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
      />
    </div>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null;
};

export default BatchReviewWizard;
