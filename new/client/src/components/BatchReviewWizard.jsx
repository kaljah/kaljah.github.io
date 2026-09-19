import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { 
  Sparkles, X, Check, Trash2, Search, Filter, AlertTriangle, 
  CheckCircle, RefreshCw, Layers, ShieldAlert, CheckSquare, 
  Square, Clock, ArrowUpDown, ChevronDown 
} from 'lucide-react';
import api from '../api';
import { useToast } from './Toast';
import { useAuth } from '../context/AuthContext';
import ConfirmModal from './ConfirmModal';
import './BatchReviewWizard.css';

const QUICK_REJECTION_REASONS = [
  "Incorrect Emission Factor Applied",
  "Facility Allocation Mismatch",
  "Missing Activity Documentation",
  "Value Exceeds Operational Threshold",
  "Duplicate Batch Entry Detected",
  "Incomplete Activity Metric"
];

const detectAnomalies = (record, facilitiesList) => {
  const reasons = [];
  let severity = 'clean';

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

const BatchReviewWizard = ({ isOpen, onClose, facilities = [] }) => {
  const { user } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [rawPending, setRawPending] = useState({ scope1: [], scope2: [], scope3: [], total_pending: 0 });

  // Filter States
  const [scopeFilter, setScopeFilter] = useState('all'); // 'all' | '1' | '2' | '3'
  const [qaFilter, setQaFilter] = useState('all'); // 'all' | 'weird' | 'clean'
  const [facilityFilter, setFacilityFilter] = useState('all');
  const [yearFilter, setYearFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Selection
  const [selectedKeys, setSelectedKeys] = useState(new Set());

  // Rejection Modal
  const [rejectionModal, setRejectionModal] = useState({
    isOpen: false,
    mode: 'selected', // 'single' | 'selected' | 'all' | 'filtered'
    targetItem: null,
    reason: ''
  });

  // Approval Confirm Modal
  const [confirmModal, setConfirmModal] = useState({
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
      toast.error("Failed to load pending records for wizard");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (isOpen) {
      fetchAllPendingData();
      setSelectedKeys(new Set());
    }
  }, [isOpen, fetchAllPendingData]);

  // Handle ESC key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !rejectionModal.isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, rejectionModal.isOpen]);

  // Normalize all records with anomaly detection
  const normalizedRecords = useMemo(() => {
    const list = [];

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
    const years = new Set();
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
      toast.info("No anomalous records in current view");
      return;
    }
    setSelectedKeys(new Set(weirdKeys));
    toast.info(`Selected ${weirdKeys.length} anomalous records for review`);
  };

  // Toggle single item selection
  const handleToggleKey = (key) => {
    setSelectedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // ── Actions ─────────────────────────────────────────────────────────────

  // Single Approve
  const handleApproveSingle = async (scope, id) => {
    try {
      await api.post(`/emissions/approve/${id}`, { scope: String(scope) });
      toast.success("Record verified and committed to inventory");
      setSelectedKeys(prev => {
        const next = new Set(prev);
        next.delete(`${scope}-${id}`);
        return next;
      });
      fetchAllPendingData();
    } catch (err) {
      toast.error(err.response?.data?.error || "Failed to approve record");
    }
  };

  // Approve Selected
  const handleApproveSelected = async () => {
    if (selectedKeys.size === 0) return;
    setIsProcessing(true);
    try {
      const by_scope = { "1": [], "2": [], "3": [] };
      const ids = [];
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

      toast.success(`Successfully approved ${res.data.approved_count || selectedKeys.size} records`);
      setSelectedKeys(new Set());
      fetchAllPendingData();
    } catch (err) {
      toast.error(err.response?.data?.error || "Failed to approve selected records");
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
            toast.success(`Approved all ${res.data.approved_count} pending records`);
          } else {
            // Scoped to current filters
            const by_scope = { "1": [], "2": [], "3": [] };
            const ids = [];
            filteredRecords.forEach(r => {
              by_scope[r.scope].push(Number(r.id));
              ids.push(Number(r.id));
            });
            const res = await api.post('/emissions/approve/batch', {
              scope: "all",
              ids,
              by_scope
            });
            toast.success(`Approved ${res.data.approved_count} filtered records`);
          }
          setSelectedKeys(new Set());
          fetchAllPendingData();
        } catch (err) {
          toast.error(err.response?.data?.error || "Batch approval failed");
        } finally {
          setIsProcessing(false);
        }
      }
    });
  };

  // Confirm Rejection Modal Submission
  const handleConfirmRejection = async () => {
    if (!rejectionModal.reason.trim()) {
      toast.warning("Please provide or select a rejection justification");
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
        toast.success("Record rejected and removed");
      } else if (rejectionModal.mode === 'selected') {
        const by_scope = { "1": [], "2": [], "3": [] };
        const ids = [];
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
        toast.success(`Rejected ${res.data.deleted_count || selectedKeys.size} records`);
      } else if (rejectionModal.mode === 'all') {
        const res = await api.post('/emissions/reject/batch', {
          scope: "all",
          reject_all: true,
          reason
        });
        toast.success(`Purged all ${res.data.deleted_count} pending records`);
      } else if (rejectionModal.mode === 'filtered') {
        const by_scope = { "1": [], "2": [], "3": [] };
        const ids = [];
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
        toast.success(`Rejected ${res.data.deleted_count} filtered records`);
      }

      setRejectionModal({ isOpen: false, mode: 'selected', targetItem: null, reason: '' });
      setSelectedKeys(new Set());
      fetchAllPendingData();
    } catch (err) {
      toast.error(err.response?.data?.error || "Failed to reject record(s)");
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  const modalContent = (
    <div className="batch-wizard-backdrop" onClick={(e) => { if (e.target === e.currentTarget && !rejectionModal.isOpen) onClose(); }}>
      <div className="batch-wizard-modal">
        {/* ── Wizard Header ── */}
        <div className="batch-wizard-header">
          <div className="wizard-header-title-group">
            <div className="wizard-badge-icon">
              <Sparkles size={24} />
            </div>
            <div className="wizard-title-text">
              <h2>Pending Data Audit & Verification Wizard</h2>
              <p>Unrestricted Maker-Checker verification pipeline · Auditing 100% of staged records across Scope 1, 2, and 3</p>
            </div>
          </div>

          <div className="wizard-header-actions">
            <button
              className="btn-ghost"
              onClick={fetchAllPendingData}
              disabled={loading || isProcessing}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', border: '1px solid var(--border-color)', borderRadius: '9px', padding: '7px 14px', fontSize: '0.82rem', background: '#ffffff', cursor: 'pointer' }}
            >
              <RefreshCw size={14} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
              Reload All
            </button>
            <button
              className="btn-ghost"
              onClick={onClose}
              style={{ padding: '7px', borderRadius: '9px', border: '1px solid var(--border-color)', cursor: 'pointer', background: '#ffffff' }}
              title="Close Wizard (Esc)"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* ── KPI Summary Strip ── */}
        <div className="batch-wizard-kpis">
          <div className="kpi-chip-group">
            <div className="kpi-chip">
              <span>Total Staged:</span>
              <strong>{stats.totalCount} records</strong>
            </div>
            <div className="kpi-chip">
              <span>Cumulative Impact:</span>
              <strong>{stats.totalTco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} tCO₂e</strong>
            </div>
            <div className="kpi-chip">
              <span>Scope Distribution:</span>
              <strong>S1({stats.count1}) S2({stats.count2}) S3({stats.count3})</strong>
            </div>
            <div className={`kpi-chip ${stats.weirdCount > 0 ? 'weird' : ''}`}>
              <AlertTriangle size={14} />
              <span>Suspicious / Weird:</span>
              <strong>{stats.weirdCount} flagged</strong>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {stats.weirdCount > 0 && (
              <button
                className="btn-wizard-action btn-wizard-select-weird"
                onClick={handleSelectAllWeird}
                title="Select all flagged anomalies for batch rejection or inspection"
              >
                <AlertTriangle size={14} />
                Select All Weird ({stats.weirdCount})
              </button>
            )}
            <button
              className="btn-wizard-action btn-wizard-approve-all"
              onClick={() => handleApproveAll(false)}
              disabled={loading || isProcessing || stats.totalCount === 0}
              title="Verify all pending records across all scopes without exception"
            >
              <Check size={14} />
              Approve All ({stats.totalCount})
            </button>
            <button
              className="btn-wizard-action btn-wizard-reject-all"
              onClick={() => setRejectionModal({ isOpen: true, mode: 'all', targetItem: null, reason: '' })}
              disabled={loading || isProcessing || stats.totalCount === 0}
              title="Delete all pending records with audit justification"
            >
              <Trash2 size={14} />
              Delete All ({stats.totalCount})
            </button>
          </div>
        </div>

        {/* ── Toolbar: Filters & Filtered Actions ── */}
        <div className="batch-wizard-toolbar">
          <div className="toolbar-filter-cluster">
            {/* Scope Tabs */}
            <div className="segmented-group">
              <button className={`segmented-item-btn ${scopeFilter === 'all' ? 'active' : ''}`} onClick={() => setScopeFilter('all')}>
                All Scopes ({stats.totalCount})
              </button>
              <button className={`segmented-item-btn ${scopeFilter === '1' ? 'active' : ''}`} onClick={() => setScopeFilter('1')}>
                Scope 1 ({stats.count1})
              </button>
              <button className={`segmented-item-btn ${scopeFilter === '2' ? 'active' : ''}`} onClick={() => setScopeFilter('2')}>
                Scope 2 ({stats.count2})
              </button>
              <button className={`segmented-item-btn ${scopeFilter === '3' ? 'active' : ''}`} onClick={() => setScopeFilter('3')}>
                Scope 3 ({stats.count3})
              </button>
            </div>

            {/* QA Anomaly Filter */}
            <div className="segmented-group">
              <button className={`segmented-item-btn ${qaFilter === 'all' ? 'active' : ''}`} onClick={() => setQaFilter('all')}>
                All Data
              </button>
              <button className={`segmented-item-btn ${qaFilter === 'weird' ? 'active weird-active' : ''}`} onClick={() => setQaFilter('weird')}>
                <AlertTriangle size={13} />
                Weird Only ({stats.weirdCount})
              </button>
              <button className={`segmented-item-btn ${qaFilter === 'clean' ? 'active' : ''}`} onClick={() => setQaFilter('clean')}>
                <CheckCircle size={13} color="#10b981" />
                Clean Only ({stats.cleanCount})
              </button>
            </div>

            {/* Facility Select */}
            <select
              value={facilityFilter}
              onChange={(e) => setFacilityFilter(e.target.value)}
              className="component-select"
              style={{ width: 'auto', padding: '6px 30px 6px 12px', fontSize: '0.8rem', height: '34px' }}
            >
              <option value="all">All Facilities</option>
              {facilities.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>

            {/* Year Select */}
            {availableYears.length > 0 && (
              <select
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
                className="component-select"
                style={{ width: 'auto', padding: '6px 30px 6px 12px', fontSize: '0.8rem', height: '34px' }}
              >
                <option value="all">All Years</option>
                {availableYears.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            )}

            {/* Search Box */}
            <div className="wizard-search-box">
              <Search size={14} color="var(--text-secondary)" />
              <input
                type="text"
                placeholder="Search by facility, fuel, category..."
                className="wizard-search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="btn-ghost" onClick={() => setSearchQuery('')} style={{ padding: 2, cursor: 'pointer' }}>
                  <X size={12} />
                </button>
              )}
            </div>
          </div>

          <div className="toolbar-action-cluster">
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              Showing {filteredRecords.length} of {stats.totalCount}
            </span>

            {/* Action on Filtered Set */}
            {(scopeFilter !== 'all' || qaFilter !== 'all' || facilityFilter !== 'all' || yearFilter !== 'all' || searchQuery) && filteredRecords.length > 0 && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn-wizard-action btn-wizard-approve-all"
                  style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  onClick={() => handleApproveAll(true)}
                  disabled={isProcessing}
                >
                  <Check size={13} />
                  Approve Filtered ({filteredRecords.length})
                </button>
                <button
                  className="btn-wizard-action btn-wizard-reject-all"
                  style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  onClick={() => setRejectionModal({ isOpen: true, mode: 'filtered', targetItem: null, reason: '' })}
                  disabled={isProcessing}
                >
                  <Trash2 size={13} />
                  Reject Filtered ({filteredRecords.length})
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── Floating Selected Batch Bar ── */}
        {selectedKeys.size > 0 && (
          <div className="wizard-batch-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <span style={{ fontWeight: 700, fontSize: '0.92rem', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <CheckSquare size={16} color="#38bdf8" />
                {selectedKeys.size} record{selectedKeys.size > 1 ? 's' : ''} selected
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>•</span>
              <span style={{ fontSize: '0.84rem', color: '#cbd5e1' }}>
                Impact: <strong style={{ color: '#ffffff' }}>{selectedImpactTco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong> tCO₂e
              </span>
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                className="btn-wizard-action btn-wizard-approve-all"
                onClick={handleApproveSelected}
                disabled={isProcessing}
              >
                <Check size={14} />
                Approve Selected ({selectedKeys.size})
              </button>
              <button
                className="btn-wizard-action btn-wizard-reject-all"
                onClick={() => setRejectionModal({ isOpen: true, mode: 'selected', targetItem: null, reason: '' })}
                disabled={isProcessing}
              >
                <X size={14} />
                Reject Selected ({selectedKeys.size})
              </button>
              <button
                className="btn-ghost"
                onClick={() => setSelectedKeys(new Set())}
                style={{ color: '#94a3b8', fontSize: '0.82rem', padding: '6px 10px', cursor: 'pointer' }}
              >
                Deselect
              </button>
            </div>
          </div>
        )}

        {/* ── Table Body ── */}
        <div className="batch-wizard-body">
          {loading ? (
            <div className="wizard-empty-state">
              <RefreshCw size={36} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent-color)' }} />
              <p style={{ fontWeight: 600 }}>Loading 100% of pending records across all scopes...</p>
            </div>
          ) : stats.totalCount === 0 ? (
            <div className="wizard-empty-state">
              <div className="wizard-empty-icon">
                <CheckCircle size={32} />
              </div>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-primary)' }}>All Pending Data Verified</h3>
              <p style={{ margin: 0, maxWidth: 460, fontSize: '0.88rem' }}>
                There are currently no records awaiting Maker-Checker approval. Staged bulk import entries will appear here automatically.
              </p>
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="wizard-empty-state">
              <Filter size={32} color="var(--text-muted)" />
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>No Matching Records</h3>
              <p style={{ margin: 0, fontSize: '0.86rem' }}>No records match your active scope, anomaly, or search filters.</p>
              <button
                className="btn-ghost"
                onClick={() => { setScopeFilter('all'); setQaFilter('all'); setFacilityFilter('all'); setYearFilter('all'); setSearchQuery(''); }}
                style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '6px 14px', fontSize: '0.82rem', marginTop: '8px', cursor: 'pointer' }}
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <table className="wizard-table">
              <thead>
                <tr>
                  <th style={{ width: 44, textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      style={{ cursor: 'pointer' }}
                      checked={filteredRecords.length > 0 && filteredRecords.every(r => selectedKeys.has(r.key))}
                      onChange={handleToggleSelectAllInView}
                    />
                  </th>
                  <th style={{ width: 80 }}>Ref ID</th>
                  <th style={{ width: 90 }}>Scope</th>
                  <th style={{ width: 100 }}>Period</th>
                  <th style={{ minWidth: 160 }}>Facility</th>
                  <th style={{ minWidth: 240 }}>Activity Details</th>
                  <th style={{ width: 130, textAlign: 'right' }}>Emissions</th>
                  <th style={{ width: 190 }}>Integrity Status</th>
                  <th style={{ width: 100, textAlign: 'center' }}>Review Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map(item => {
                  const isSelected = selectedKeys.has(item.key);
                  const facName = facilities.find(f => f.id === item.facility_id)?.name || (item.facility_id ? `Facility #${item.facility_id}` : 'Unassigned');

                  return (
                    <tr key={item.key} className={`${isSelected ? 'row-selected' : ''} ${item.isWeird ? 'row-weird' : ''}`}>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          style={{ cursor: 'pointer' }}
                          checked={isSelected}
                          onChange={() => handleToggleKey(item.key)}
                        />
                      </td>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          #{String(item.id).slice(-5)}
                        </span>
                      </td>
                      <td>
                        <span className={`scope-tag scope-tag-${item.scope}`}>
                          Scope {item.scope}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 500 }}>{item.date}</span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{facName}</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span style={{ fontSize: '0.84rem' }}>{item.desc}</span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <strong className="num-tabular" style={{ fontSize: '0.9rem' }}>
                          {item.tco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: '4px' }}>tCO₂e</span>
                      </td>
                      <td>
                        {item.isWeird ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                            <span
                              className={`anomaly-pill ${item.severity}`}
                              title={item.reasons.join(" · ")}
                            >
                              <AlertTriangle size={12} />
                              {item.severity === 'danger' ? 'Suspicious Data' : 'Notice'}
                            </span>
                            <span style={{ fontSize: '0.72rem', color: item.severity === 'danger' ? '#dc2626' : '#b45309', lineHeight: 1.2 }}>
                              {item.reasons[0]}
                              {item.reasons.length > 1 && ` (+${item.reasons.length - 1} more)`}
                            </span>
                          </div>
                        ) : (
                          <span className="anomaly-pill clean">
                            <Check size={12} />
                            Verified Structure
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div className="review-actions-group" style={{ justifyContent: 'center' }}>
                          {item.created_by && String(item.created_by) === String(user?.id) ? (
                            <span 
                              className="badge-maker"
                              style={{ 
                                fontSize: '0.7rem', 
                                padding: '4px 8px', 
                                borderRadius: '6px', 
                                background: 'rgba(239, 68, 68, 0.1)', 
                                color: '#ef4444', 
                                border: '1px solid rgba(239, 68, 68, 0.25)', 
                                fontWeight: 600, 
                                whiteSpace: 'nowrap' 
                              }}
                              title="Maker-Checker: You created this record and cannot self-approve."
                            >
                              Self-Submitted
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="btn-review-action approve"
                              title="Approve & Commit"
                              onClick={() => handleApproveSingle(item.scope, item.id)}
                            >
                              <Check size={16} />
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn-review-action reject"
                            title="Reject (Specify Reason)"
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
        <div className="rejection-modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget && !isProcessing) setRejectionModal(prev => ({ ...prev, isOpen: false })); }}>
          <div className="rejection-modal">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: 36, height: 36, borderRadius: '10px', background: 'rgba(239, 68, 68, 0.1)', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Trash2 size={20} />
                </div>
                <h3 style={{ margin: 0, fontWeight: 700, fontSize: '1.1rem' }}>
                  {rejectionModal.mode === 'single'
                    ? `Reject Record #${rejectionModal.targetItem?.id}`
                    : rejectionModal.mode === 'selected'
                    ? `Reject ${selectedKeys.size} Selected Records`
                    : rejectionModal.mode === 'all'
                    ? `Delete ALL ${stats.totalCount} Pending Records`
                    : `Reject ${filteredRecords.length} Filtered Records`}
                </h3>
              </div>
              <button
                className="btn-ghost"
                onClick={() => !isProcessing && setRejectionModal(prev => ({ ...prev, isOpen: false }))}
                style={{ padding: '6px', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Maker-Checker governance requires a recorded audit reason before rejecting staged bulk entries. This justification will be logged in the immutable audit trail.
            </p>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                Quick Audit Justifications
              </label>
              <div className="rejection-quick-chips">
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
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                Custom Justification / Details
              </label>
              <textarea
                className="mole-input"
                rows={3}
                placeholder="Describe reason for refusal..."
                value={rejectionModal.reason}
                onChange={(e) => setRejectionModal(prev => ({ ...prev, reason: e.target.value }))}
                style={{ resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setRejectionModal(prev => ({ ...prev, isOpen: false }))}
                disabled={isProcessing}
                style={{ padding: '8px 16px', borderRadius: '10px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                style={{ background: '#ef4444', padding: '8px 18px', borderRadius: '10px' }}
                onClick={handleConfirmRejection}
                disabled={isProcessing || !rejectionModal.reason.trim()}
              >
                {isProcessing ? 'Processing...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmLabel="Approve Records"
        confirmVariant="primary"
        loading={isProcessing}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
      />
    </div>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null;
};

export default BatchReviewWizard;
