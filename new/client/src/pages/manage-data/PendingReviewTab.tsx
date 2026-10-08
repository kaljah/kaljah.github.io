import React, { useState } from "react";
import { Button } from "../../ui";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle,
  CheckSquare,
  Clock,
  Filter,
  Flame,
  Pencil,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  Square,
  X,
} from "lucide-react";
import BatchReviewWizard from "../../components/BatchReviewWizard";
import EditEmissionModal from "../../components/modals/EditEmissionModal";

export interface PendingEmissionRecord {
  id: string | number;
  key: string;
  scope: string | number;
  date?: string;
  facility_id?: string | number;
  desc?: string;
  tco2e: number;
  qa_flag?: string | null;
  created_by?: string | number | null;
  [key: string]: any;
}

export interface PendingMetrics {
  totalCount: number;
  count1: number;
  count2: number;
  count3: number;
  totalTco2e: number;
  flaggedCount: number;
  cleanCount: number;
  loadedCount: number;
  [key: string]: any;
}

export interface RejectionModalState {
  isOpen: boolean;
  isBatch: boolean;
  recordIds: any[];
  reason: string;
  [key: string]: any;
}

export interface PendingReviewTabProps {
  QUICK_REJECTION_REASONS: string[];
  facilities: Array<{
    id: string | number;
    name: string;
    [key: string]: any;
  }>;
  fetchPendingEmissions: (force?: boolean) => void;
  filteredPendingRecords: PendingEmissionRecord[];
  handleApproveAllInScope: (scope: string) => void;
  handleApproveSingle: (scope: number | string, id: number | string) => void;
  handleBatchApproveSelected: () => void;
  handleConfirmReject: () => void;
  handleOpenBatchRejectModal: () => void;
  handleOpenRejectModal: (scope: number | string, id: number | string) => void;
  handleSelectAllPendingToggle: () => void;
  handleToggleSelectPending: (key: string) => void;
  isBatchWizardOpen: boolean;
  isProcessingBatch: boolean;
  isRefreshingPending: boolean;
  pendingMetrics: PendingMetrics;
  pendingQaFilter: string;
  pendingScopeFilter: string;
  pendingSearch: string;
  rejectionModal: RejectionModalState;
  selectedPendingImpactTco2e: number;
  selectedPendingKeys: Set<string>;
  setIsBatchWizardOpen: (open: boolean) => void;
  setPendingQaFilter: (filter: string) => void;
  setPendingScopeFilter: (filter: string) => void;
  setPendingSearch: (search: string) => void;
  setRejectionModal: React.Dispatch<React.SetStateAction<RejectionModalState>>;
  setSelectedPendingKeys: React.Dispatch<React.SetStateAction<Set<string>>>;
  user?: { id?: string | number; role?: string; [key: string]: any } | null;
}

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const PendingReviewTab: React.FC<PendingReviewTabProps> = ({
  QUICK_REJECTION_REASONS,
  facilities,
  fetchPendingEmissions,
  filteredPendingRecords,
  handleApproveAllInScope,
  handleApproveSingle,
  handleBatchApproveSelected,
  handleConfirmReject,
  handleOpenBatchRejectModal,
  handleOpenRejectModal,
  handleSelectAllPendingToggle,
  handleToggleSelectPending,
  isBatchWizardOpen,
  isProcessingBatch,
  isRefreshingPending,
  pendingMetrics,
  pendingQaFilter,
  pendingScopeFilter,
  pendingSearch,
  rejectionModal,
  selectedPendingImpactTco2e,
  selectedPendingKeys,
  setIsBatchWizardOpen,
  setPendingQaFilter,
  setPendingScopeFilter,
  setPendingSearch,
  setRejectionModal,
  setSelectedPendingKeys,
  user,
}) => {
  const [editingRecord, setEditingRecord] = useState<PendingEmissionRecord | null>(null);

  return (
    <div className="manage-tab-content [display:flex] [flex-direction:column] [gap:24px] [width:100%]">
      {/* Rejection Modal */}
      {rejectionModal.isOpen && (
        <div
          role="presentation"
          className="[position:fixed] [inset:0] [background:rgba(15,_23,_42,_0.5)] [backdrop-filter:blur(6px)] [display:flex] [align-items:center] [justify-content:center] [z-index:1000] [animation:fadeIn_0.2s_ease-out]"
          onClick={() => !isProcessingBatch && setRejectionModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div
            role="presentation"
            className="[background:var(--bg-card-elevated)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [width:90%] [max-width:520px] [padding:28px] [box-shadow:var(--shadow-card-elevated)] [display:flex] [flex-direction:column] [gap:20px] [animation:scaleUp_0.25s_cubic-bezier(0.16,_1,_0.3,_1)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex! justify-between! items-center!">
              <div className="flex! items-center! gap-[12px]!">
                <div className="w-[42px]! h-[42px]! rounded-[12px]! bg-[color:rgba(239,_68,_68,_0.12)]! flex! items-center! justify-center! text-[color:#dc2626]!">
                  <AlertTriangle size={22} />
                </div>
                <div>
                  <h3 className="m-[0px]! text-[length:1.15rem]! font-bold!">
                    {rejectionModal.isBatch
                      ? `Reject ${rejectionModal.recordIds.length} Selected Record${rejectionModal.recordIds.length > 1 ? "s" : ""}`
                      : "Reject Emission Record"}
                  </h3>
                  <p className="m-[2px_0_0_0]! text-[length:0.8rem]! text-[color:var(--text-secondary)]!">
                    Maker-Checker Audit Trail & Reason
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                type="submit"
                className="p-[6px]! rounded-[8px]!"
                onClick={() => !isProcessingBatch && setRejectionModal((prev) => ({ ...prev, isOpen: false }))}
              >
                <X size={18} />
              </Button>
            </div>

            <div className="bg-[color:rgba(239,_68,_68,_0.06)]! [border:1px_solid_rgba(239,_68,_68,_0.2)]! rounded-[12px]! p-[12px_14px]! text-[length:0.84rem]! text-[color:#b91c1c]! flex! gap-[10px]! items-start!">
              <AlertCircle size={16} className="shrink-0! mt-[2px]!" />
              <span>
                The record will be marked Rejected and excluded from totals; it is kept for the audit trail. The submitter is notified with your reason.
              </span>
            </div>

            <div>
              <label className="block! text-[length:0.78rem]! font-semibold! text-[color:var(--text-secondary)]! mb-[10px]! uppercase! [letter-spacing:0.05em]!">
                Quick Rejection Reason Presets
              </label>
              <div className="[display:flex] [flex-wrap:wrap] [gap:8px]">
                {QUICK_REJECTION_REASONS.map((reason) => (
                  <button
                    key={reason}
                    type="button"
                    className={`rejection-chip ${rejectionModal.reason === reason ? "selected" : ""}`}
                    onClick={() => setRejectionModal((prev) => ({ ...prev, reason }))}
                  >
                    {reason}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block! text-[length:0.78rem]! font-semibold! text-[color:var(--text-secondary)]! mb-[8px]! uppercase! [letter-spacing:0.05em]!">
                Audit Reason / Justification <span className="text-[color:#b91c1c]!">*</span>
              </label>
              <textarea
                className="custom-input w-full! [resize:vertical]! text-[length:0.88rem]! p-[10px_12px]! rounded-[10px]!"
                rows={3}
                placeholder="Specify the detailed reason for rejection..."
                value={rejectionModal.reason}
                onChange={(e) => setRejectionModal((prev) => ({ ...prev, reason: e.target.value }))}
              />
            </div>

            <div className="flex! justify-end! gap-[12px]! mt-[4px]!">
              <Button
                type="button"
                variant="ghost"
                disabled={isProcessingBatch}
                onClick={() => setRejectionModal((prev) => ({ ...prev, isOpen: false }))}
                className="p-[8px_16px]! rounded-[8px]!"
              >
                Cancel
              </Button>
              <button
                type="button"
                className="[background:#fee2e2] [color:var(--color-red-700)] [border:1px_solid_#fecaca] [cursor:pointer] [font-size:var(--text-base)] [transition:all_0.2s] hover:[background:var(--color-red-700)] hover:[color:white] inline-flex! items-center! gap-[8px]! p-[8px_18px]! rounded-[8px]!"
                disabled={isProcessingBatch || !rejectionModal.reason.trim()}
                onClick={handleConfirmReject}
              >
                <X size={16} />
                {isProcessingBatch ? "Rejecting..." : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Header */}
      <div className="manage-tab-header mb-[0px]!">
        <div>
          <div className="flex! items-center! gap-[12px]! mb-[6px]!">
            <h2 className="m-[0px]! font-bold! [letter-spacing:-0.02em]!">Pending Review & Approvals</h2>
            {pendingMetrics.totalCount > 0 && (
              <span className="bg-[color:rgba(255,_102,_0,_0.1)]! text-[color:var(--color-link)]! [border:1px_solid_rgba(255,_102,_0,_0.25)]! text-[length:0.75rem]! font-bold! p-[3px_10px]! rounded-[12px]!">
                {pendingMetrics.totalCount} Awaiting Review
              </span>
            )}
          </div>
          <p className="m-[0px]! text-[color:var(--text-secondary)]! text-[length:0.9rem]!">
            Maker-Checker Segregation: Audit and approve bulk-imported emissions data prior to greenhouse gas inventory inclusion.
          </p>
        </div>
        <div className="flex! gap-[10px]! items-center!">
          <Button
            variant="ghost"
            type="submit"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              border: "1px solid var(--border-color)",
              borderRadius: "10px",
              padding: "8px 16px",
              background: "var(--bg-card)",
              fontWeight: 500,
              cursor: "pointer",
            }}
            onClick={() => fetchPendingEmissions()}
            disabled={isRefreshingPending}
          >
            <RefreshCw size={15} style={{ animation: isRefreshingPending ? "spin 1s linear infinite" : "none" }} />
            {isRefreshingPending ? "Refreshing..." : "Refresh Queue"}
          </Button>
          <Button
            type="submit"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              borderRadius: "10px",
              padding: "8px 18px",
              background: "linear-gradient(135deg, #ff6600, #ea580c)",
              color: "var(--color-white)",
              fontWeight: 600,
              border: "none",
              boxShadow: "0 4px 14px rgba(255, 102, 0, 0.35)",
              cursor: "pointer",
            }}
            onClick={() => setIsBatchWizardOpen(true)}
          >
            <Sparkles size={16} />
            Launch Review Wizard
          </Button>
        </div>
      </div>

      {/* Top Hero KPI Metrics Strip */}
      <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(220px,_1fr))] [gap:16px] [width:100%]">
        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:20px] [display:flex] [align-items:center] [gap:16px] [box-shadow:var(--shadow-card)] [transition:all_0.2s_cubic-bezier(0.4,_0,_0.2,_1)] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated)] hover:[border-color:rgba(255,_102,_0,_0.3)]">
          <div className="[width:48px] [height:48px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [flex-shrink:0] bg-[color:rgba(255,_102,_0,_0.1)]! text-[color:var(--color-link)]!">
            <Clock size={22} />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:2px] [min-width:0]">
            <span className="[font-size:var(--text-sm)] [font-weight:600] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary)]">Pending Records</span>
            <span className="[font-size:var(--text-xl)] [font-weight:700] [color:var(--text-primary)] [line-height:1.2]">{pendingMetrics.totalCount}</span>
            <span className="[font-size:var(--text-sm)] [color:var(--text-muted)] [white-space:nowrap] [overflow:hidden] [text-overflow:ellipsis]">
              S1: {pendingMetrics.count1} · S2: {pendingMetrics.count2} · S3: {pendingMetrics.count3}
            </span>
          </div>
        </div>

        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:20px] [display:flex] [align-items:center] [gap:16px] [box-shadow:var(--shadow-card)] [transition:all_0.2s_cubic-bezier(0.4,_0,_0.2,_1)] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated)] hover:[border-color:rgba(255,_102,_0,_0.3)]">
          <div className="[width:48px] [height:48px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [flex-shrink:0] bg-[color:rgba(239,_68,_68,_0.1)]! text-[color:#b91c1c]!">
            <Flame size={22} />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:2px] [min-width:0]">
            <span className="[font-size:var(--text-sm)] [font-weight:600] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary)]">Pending Impact</span>
            <span className="[font-size:var(--text-xl)] [font-weight:700] [color:var(--text-primary)] [line-height:1.2]">
              {pendingMetrics.totalTco2e.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
              <span className="text-[length:0.8rem]! font-medium! text-[color:var(--text-secondary)]! ml-[4px]!">tCO₂e</span>
            </span>
            <span className="[font-size:var(--text-sm)] [color:var(--text-muted)] [white-space:nowrap] [overflow:hidden] [text-overflow:ellipsis]">Awaiting inventory commit</span>
          </div>
        </div>

        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:20px] [display:flex] [align-items:center] [gap:16px] [box-shadow:var(--shadow-card)] [transition:all_0.2s_cubic-bezier(0.4,_0,_0.2,_1)] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated)] hover:[border-color:rgba(255,_102,_0,_0.3)]">
          <div className={`[width:48px] [height:48px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [flex-shrink:0] ${pendingMetrics.flaggedCount > 0 ? "[background:rgba(245,_158,_11,_0.1)]!" : "[background:rgba(16,_185,_129,_0.1)]!"} ${pendingMetrics.flaggedCount > 0 ? "[color:#d97706]!" : "[color:#059669]!"}`}>
            {pendingMetrics.flaggedCount > 0 ? <AlertTriangle size={22} /> : <CheckCircle size={22} />}
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:2px] [min-width:0]">
            <span className="[font-size:var(--text-sm)] [font-weight:600] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary)]">Quality Audit</span>
            <span className={`[font-size:var(--text-xl)] [font-weight:700] [line-height:1.2] ${pendingMetrics.flaggedCount > 0 ? "[color:#d97706]!" : "[color:inherit]!"}`}>
              {pendingMetrics.flaggedCount} Flagged
            </span>
            <span className="[font-size:var(--text-sm)] [color:var(--text-muted)] [white-space:nowrap] [overflow:hidden] [text-overflow:ellipsis]">{pendingMetrics.cleanCount} clean records verified</span>
          </div>
        </div>

        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:20px] [display:flex] [align-items:center] [gap:16px] [box-shadow:var(--shadow-card)] [transition:all_0.2s_cubic-bezier(0.4,_0,_0.2,_1)] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated)] hover:[border-color:rgba(255,_102,_0,_0.3)]">
          <div className="[width:48px] [height:48px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [flex-shrink:0] bg-[color:rgba(59,_130,_246,_0.1)]! text-[color:#2563eb]!">
            <Shield size={22} />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:2px] [min-width:0]">
            <span className="[font-size:var(--text-sm)] [font-weight:600] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary)]">Scope Segregation</span>
            <span className="[font-weight:700] [color:var(--text-primary)] [line-height:1.2] text-[length:1.15rem]!">
              {pendingMetrics.totalCount > 0
                ? `S1(${pendingMetrics.count1}) S2(${pendingMetrics.count2}) S3(${pendingMetrics.count3})`
                : "Queue Clear"}
            </span>
            <span className="[font-size:var(--text-sm)] [color:var(--text-muted)] [white-space:nowrap] [overflow:hidden] [text-overflow:ellipsis]">Maker-Checker active</span>
          </div>
        </div>
      </div>

      {/* Filter & Controls Toolbar */}
      <div className="[display:flex] [flex-wrap:wrap] [align-items:center] [justify-content:space-between] [gap:16px] [background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:16px_20px] [box-shadow:var(--shadow-card)]">
        <div className="[display:inline-flex] [background:rgba(15,_23,_42,_0.05)] [border-radius:var(--radius-md)] [padding:4px] [gap:4px]">
          <button
            className={`pending-tab-btn ${pendingScopeFilter === "all" ? "active" : ""}`}
            onClick={() => setPendingScopeFilter("all")}
          >
            <span>All Scopes</span>
            <span className="pending-count-chip [display:inline-flex] [align-items:center] [justify-content:center] [min-width:20px] [height:20px] [padding:0_6px] [border-radius:var(--radius-md)] [font-size:var(--text-xs)] [font-weight:600] [background:rgba(15,_23,_42,_0.08)] [color:var(--text-secondary)]">
              {pendingMetrics.totalCount}
            </span>
          </button>
          <button
            className={`pending-tab-btn ${pendingScopeFilter === "1" ? "active" : ""}`}
            onClick={() => setPendingScopeFilter("1")}
          >
            <span className="scope-tag [background:rgba(255,_102,_0,_0.1)] [color:var(--color-brand-700)] [border:1px_solid_rgba(255,_102,_0,_0.25)]! p-[1px_6px]! text-[length:0.7rem]!">S1</span>
            <span>Scope 1</span>
            <span className="pending-count-chip [display:inline-flex] [align-items:center] [justify-content:center] [min-width:20px] [height:20px] [padding:0_6px] [border-radius:var(--radius-md)] [font-size:var(--text-xs)] [font-weight:600] [background:rgba(15,_23,_42,_0.08)] [color:var(--text-secondary)]">
              {pendingMetrics.count1}
            </span>
          </button>
          <button
            className={`pending-tab-btn ${pendingScopeFilter === "2" ? "active" : ""}`}
            onClick={() => setPendingScopeFilter("2")}
          >
            <span className="scope-tag [background:rgba(59,_130,_246,_0.1)] [color:var(--color-blue-600)] [border:1px_solid_rgba(59,_130,_246,_0.25)]! p-[1px_6px]! text-[length:0.7rem]!">S2</span>
            <span>Scope 2</span>
            <span className="pending-count-chip [display:inline-flex] [align-items:center] [justify-content:center] [min-width:20px] [height:20px] [padding:0_6px] [border-radius:var(--radius-md)] [font-size:var(--text-xs)] [font-weight:600] [background:rgba(15,_23,_42,_0.08)] [color:var(--text-secondary)]">
              {pendingMetrics.count2}
            </span>
          </button>
          <button
            className={`pending-tab-btn ${pendingScopeFilter === "3" ? "active" : ""}`}
            onClick={() => setPendingScopeFilter("3")}
          >
            <span className="scope-tag [background:rgba(147,_51,_234,_0.1)] [color:#7c3aed] [border:1px_solid_rgba(147,_51,_234,_0.25)]! p-[1px_6px]! text-[length:0.7rem]!">S3</span>
            <span>Scope 3</span>
            <span className="pending-count-chip [display:inline-flex] [align-items:center] [justify-content:center] [min-width:20px] [height:20px] [padding:0_6px] [border-radius:var(--radius-md)] [font-size:var(--text-xs)] [font-weight:600] [background:rgba(15,_23,_42,_0.08)] [color:var(--text-secondary)]">
              {pendingMetrics.count3}
            </span>
          </button>
        </div>

        <div className="flex! items-center! gap-[12px]! flex-wrap!">
          {/* QA Filter Pills */}
          <div className="inline-flex! bg-[color:rgba(15,_23,_42,_0.05)]! rounded-[10px]! p-[3px]! gap-[3px]!">
            <button
              className={`pending-tab-btn ${pendingQaFilter === "all" ? "active" : ""}`}
              style={{ padding: "6px 12px", fontSize: "0.78rem" }}
              onClick={() => setPendingQaFilter("all")}
            >
              All QA
            </button>
            <button
              className={`pending-tab-btn ${pendingQaFilter === "clean" ? "active" : ""}`}
              style={{ padding: "6px 12px", fontSize: "0.78rem", color: pendingQaFilter === "clean" ? "#059669" : "inherit" }}
              onClick={() => setPendingQaFilter("clean")}
            >
              Clean Only
            </button>
            <button
              className={`pending-tab-btn ${pendingQaFilter === "flagged" ? "active" : ""}`}
              style={{ padding: "6px 12px", fontSize: "0.78rem", color: pendingQaFilter === "flagged" ? "#d97706" : "inherit" }}
              onClick={() => setPendingQaFilter("flagged")}
            >
              Flagged Only
            </button>
          </div>

          {/* Search Box */}
          <div className="[display:flex] [align-items:center] [gap:8px] [background:var(--bg-body)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-md)] [padding:8px_14px] [min-width:240px] [transition:border-color_0.2s] focus-within:[border-color:var(--accent-color)] focus-within:[box-shadow:0_0_0_3px_rgba(255,_102,_0,_0.1)] focus-within:[background:var(--color-white)]">
            <Search size={16} color="var(--text-secondary)" />
            <input
              type="text"
              className="[border:none] [background:transparent] [font-size:var(--text-base)] [color:var(--text-primary)] [width:100%] [outline:none] placeholder:[color:var(--text-muted)]"
              placeholder="Search by facility, fuel, category..."
              value={pendingSearch}
              onChange={(e) => setPendingSearch(e.target.value)}
            />
            {pendingSearch && (
              <Button
                variant="ghost"
                type="submit"
                className="p-[2px]! text-[color:var(--text-secondary)]!"
                onClick={() => setPendingSearch("")}
              >
                <X size={14} />
              </Button>
            )}
          </div>

          {/* Scope-level Bulk Action when Scoped */}
          {pendingScopeFilter !== "all" && pendingMetrics[`count${pendingScopeFilter}`] > 0 && (
            <Button
              type="submit"
              className="bg-[color:#10b981]! text-[length:0.82rem]! p-[8px_14px]! inline-flex! items-center! gap-[6px]!"
              disabled={isProcessingBatch}
              onClick={() => handleApproveAllInScope(pendingScopeFilter)}
            >
              <Check size={14} />
              Approve All Scope {pendingScopeFilter} ({pendingMetrics[`count${pendingScopeFilter}`]})
            </Button>
          )}
        </div>
      </div>

      {/* Floating Sticky Batch Action Bar */}
      {selectedPendingKeys.size > 0 && (
        <div className="[display:flex] [align-items:center] [justify-content:space-between] [background:linear-gradient(135deg,_var(--color-ink-800)_0%,_var(--color-ink-900)_100%)] [color:var(--color-white)] [padding:14px_24px] [border-radius:var(--radius-lg)] [box-shadow:var(--shadow-raised)] [animation:slideUp_0.25s_cubic-bezier(0.16,_1,_0.3,_1)]">
          <div className="flex! items-center! gap-[14px]! flex-wrap!">
            <span className="font-bold! text-[length:0.94rem]! inline-flex! items-center! gap-[8px]!">
              <CheckSquare size={18} color="#38bdf8" />
              {selectedPendingKeys.size} record{selectedPendingKeys.size > 1 ? "s" : ""} selected
            </span>
            <span className="text-[color:rgba(255,255,255,0.3)]!">•</span>
            <span className="text-[length:0.84rem]! text-[color:#cbd5e1]!">
              Cumulative: <strong className="text-[color:#ffffff]!">{selectedPendingImpactTco2e.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong> tCO₂e
            </span>
          </div>
          <div className="[display:flex] [align-items:center] [gap:10px]">
            <button
              className="[display:inline-flex] [align-items:center] [gap:6px] [background:var(--color-green-700)] [color:var(--color-white)] [border:none] [padding:8px_18px] [&&]:[border-radius:var(--radius-md)] [font-size:var(--text-base)] [font-weight:600] [cursor:pointer] [transition:background_0.15s,_transform_0.1s] hover:[background:var(--color-green-600)] hover:[transform:translateY(-1px)]"
              disabled={isProcessingBatch}
              onClick={handleBatchApproveSelected}
            >
              <Check size={16} />
              Approve Selected
            </button>
            <button
              className="[display:inline-flex] [align-items:center] [gap:6px] [background:rgba(239,_68,_68,_0.15)] [color:#fca5a5] [border:1px_solid_rgba(239,_68,_68,_0.4)] [padding:8px_18px] [&&]:[border-radius:var(--radius-md)] [font-size:var(--text-base)] [font-weight:600] [cursor:pointer] [transition:all_0.15s] hover:[background:var(--color-red-700)] hover:[color:var(--color-white)] hover:[border-color:var(--color-red-500)] hover:[transform:translateY(-1px)]"
              disabled={isProcessingBatch}
              onClick={handleOpenBatchRejectModal}
            >
              <X size={16} />
              Reject Selected
            </button>
            <button
              className="[background:transparent] [border:1px_solid_rgba(255,_255,_255,_0.2)] [color:var(--color-ink-600)] [padding:7px_14px] [&&]:[border-radius:var(--radius-md)] [font-size:var(--text-sm)] [cursor:pointer] [transition:all_0.15s] hover:[color:var(--color-white)] hover:[border-color:rgba(255,_255,_255,_0.4)]"
              onClick={() => setSelectedPendingKeys(new Set())}
            >
              Deselect
            </button>
          </div>
        </div>
      )}

      {/* Main Content: Queue Empty vs Table Card */}
      {pendingMetrics.totalCount === 0 ? (
        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:64px_32px] [text-align:center] [box-shadow:var(--shadow-card)] [display:flex] [flex-direction:column] [align-items:center] [gap:16px] [max-width:600px] [margin:20px_auto]">
          <div className="[width:72px] [height:72px] [border-radius:var(--radius-lg)] [background:linear-gradient(135deg,_rgba(16,_185,_129,_0.15),_rgba(16,_185,_129,_0.05))] [border:1px_solid_rgba(16,_185,_129,_0.3)] [display:flex] [align-items:center] [justify-content:center] [color:var(--color-green-700)] [box-shadow:0_8px_20px_-4px_rgba(16,_185,_129,_0.2)]">
            <CheckCircle size={36} />
          </div>
          <div className="max-w-[440px]!">
            <h3 className="m-[0_0_8px_0]! text-[length:1.25rem]! font-bold! text-[color:var(--text-primary)]!">
              All Caught Up & Verified!
            </h3>
            <p className="m-[0px]! text-[color:var(--text-secondary)]! text-[length:0.9rem]! leading-[1.5]!">
              There are currently no bulk import records awaiting Maker-Checker approval. Staged emissions records will appear here as soon as files are imported.
            </p>
          </div>
        </div>
      ) : filteredPendingRecords.length === 0 ? (
        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [text-align:center] [box-shadow:var(--shadow-card)] [display:flex] [flex-direction:column] [align-items:center] [gap:16px] [max-width:600px] [margin:20px_auto] p-[48px_24px]!">
          <div className="[width:72px] [height:72px] [border-radius:var(--radius-lg)] [border:1px_solid_rgba(16,_185,_129,_0.3)] [display:flex] [align-items:center] [justify-content:center] [box-shadow:0_8px_20px_-4px_rgba(16,_185,_129,_0.2)] bg-[color:rgba(148,_163,_184,_0.1)]! text-[color:var(--text-secondary)]! [border-color:rgba(148,_163,_184,_0.3)]!">
            <Filter size={32} />
          </div>
          <div>
            <h3 className="m-[0_0_8px_0]! text-[length:1.15rem]! font-bold!">
              No Matching Records Found
            </h3>
            <p className="m-[0_0_16px_0]! text-[color:var(--text-secondary)]! text-[length:0.88rem]!">
              No pending records match your active search and filter settings.
            </p>
            <Button
              type="submit"
              className="text-[length:0.85rem]! p-[8px_16px]!"
              onClick={() => {
                setPendingScopeFilter("all");
                setPendingQaFilter("all");
                setPendingSearch("");
              }}
            >
              Clear Filters
            </Button>
          </div>
        </div>
      ) : (
        <div className="[background:var(--bg-card)] [backdrop-filter:blur(10px)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-lg)] [padding:0] [overflow:hidden]! [box-shadow:var(--shadow-card)] [@media(max-width:768px)]:[overflow-x:auto]! [@media(max-width:768px)]:[-webkit-overflow-scrolling:touch]">
          <div className="[display:flex] [justify-content:space-between] [align-items:center] [padding:20px_24px] [border-bottom:1px_solid_var(--border-color)]">
            <div className="flex! items-center! gap-[10px]!">
              <h3 className="m-[0px]! text-[length:1.02rem]! font-bold!">
                {pendingScopeFilter === "all"
                  ? "All Pending Import Records"
                  : `Scope ${pendingScopeFilter} Pending Records`}
              </h3>
              <span className="bg-[color:rgba(15,_23,_42,_0.06)]! text-[color:var(--text-secondary)]! text-[length:0.78rem]! font-semibold! p-[2px_8px]! rounded-[8px]!">
                Showing {filteredPendingRecords.length} of {pendingMetrics.totalCount}
              </span>
              {pendingMetrics.loadedCount < pendingMetrics.totalCount && (
                <span className="text-[length:0.78rem]! text-[color:#b45309]! ml-[8px]!">
                  The first {pendingMetrics.loadedCount} are listed (200 per scope); decide on them to load the next ones, or use the Review Wizard to approve all
                </span>
              )}
            </div>

            <div className="flex! items-center! gap-[8px]!">
              <Button
                variant="ghost"
                type="submit"
                style={{
                  fontSize: "0.8rem",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "6px 12px",
                  border: "1px solid var(--border-color)",
                  borderRadius: "8px",
                }}
                onClick={handleSelectAllPendingToggle}
              >
                {filteredPendingRecords.every((r) => selectedPendingKeys.has(r.key)) ? (
                  <>
                    <CheckSquare size={14} color="var(--accent-color)" />
                    Deselect All in View
                  </>
                ) : (
                  <>
                    <Square size={14} />
                    Select All in View
                  </>
                )}
              </Button>
            </div>
          </div>

          <div className="[overflow-x:auto]!">
            <table className="pending-table">
              <thead>
                <tr>
                  <th className="w-[44px]! text-center!">
                    <input
                      type="checkbox"
                      className="cursor-pointer!"
                      checked={
                        filteredPendingRecords.length > 0 &&
                        filteredPendingRecords.every((r) => selectedPendingKeys.has(r.key))
                      }
                      onChange={handleSelectAllPendingToggle}
                    />
                  </th>
                  <th className="w-[80px]!">Ref ID</th>
                  <th className="w-[90px]!">Scope</th>
                  <th className="w-[100px]!">Period</th>
                  <th className="min-w-[150px]!">Facility</th>
                  <th className="min-w-[220px]!">Activity & Fuel / Category</th>
                  <th className="w-[120px]! text-right!">Emissions</th>
                  <th className="w-[120px]!">QA Status</th>
                  <th className="w-[110px]! text-center!">Review Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredPendingRecords.map((item) => {
                  const isSelected = selectedPendingKeys.has(item.key);
                  const facName = facilities.find((f) => f.id === item.facility_id)?.name || item.facility_id;

                  return (
                    <tr key={item.key} className={isSelected ? "row-selected" : ""}>
                      <td className="text-center!">
                        <input
                          type="checkbox"
                          className="cursor-pointer!"
                          checked={isSelected}
                          onChange={() => handleToggleSelectPending(item.key)}
                        />
                      </td>
                      <td>
                        <span className="font-mono! text-[length:0.8rem]! text-[color:var(--text-secondary)]!">
                          #{String(item.id).slice(-5)}
                        </span>
                      </td>
                      <td>
                        <span className={`scope-tag scope-tag-${item.scope}`}>
                          Scope {item.scope}
                        </span>
                      </td>
                      <td>
                        <span className="font-medium!">{item.date}</span>
                      </td>
                      <td>
                        <span className="font-semibold! text-[color:var(--text-primary)]!">
                          {facName}
                        </span>
                      </td>
                      <td>
                        <span className="text-[color:var(--text-secondary)]! text-[length:0.85rem]!">
                          {item.desc}
                        </span>
                      </td>
                      <td className="text-right!">
                        <span className="font-bold! text-[length:0.92rem]! text-[color:var(--text-primary)]!">
                          {item.tco2e.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </span>
                        <span className="text-[length:0.72rem]! text-[color:var(--text-secondary)]! ml-[4px]!">
                          tCO₂e
                        </span>
                      </td>
                      <td>
                        {item.qa_flag ? (
                          <span
                            className="[display:inline-flex] [align-items:center] [gap:4px] [padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-sm)] [font-weight:600] [background:rgba(245,_158,_11,_0.1)] [color:var(--color-amber-700)] [border:1px_solid_rgba(245,_158,_11,_0.3)]"
                            title={item.qa_flag}
                          >
                            <AlertTriangle size={12} />
                            Flagged
                          </span>
                        ) : (
                          <span className="[display:inline-flex] [align-items:center] [gap:4px] [padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-sm)] [font-weight:600] [background:rgba(16,_185,_129,_0.1)] [color:var(--color-green-700)] [border:1px_solid_rgba(16,_185,_129,_0.25)]">
                            <Check size={12} />
                            Clean
                          </span>
                        )}
                      </td>
                      <td className="text-center!">
                        <div className="[display:flex] [align-items:center] [gap:8px] justify-center!">
                          {item.created_by && String(item.created_by) === String(user?.id) ? (
                            <span
                              className="badge-maker text-[length:0.7rem]! p-[4px_8px]! rounded-[6px]! bg-[color:rgba(239,_68,_68,_0.1)]! text-[color:#b91c1c]! [border:1px_solid_rgba(239,_68,_68,_0.25)]! font-semibold! whitespace-nowrap!"
                              title="Maker-Checker: You created this record and cannot self-approve."
                            >
                              Self-Submitted
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="btn-review-action approve"
                              title="Approve Record"
                              onClick={() => handleApproveSingle(item.scope, item.id)}
                            >
                              <Check size={16} />
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn-review-action reject"
                            title="Reject Record (specify reason)"
                            onClick={() => handleOpenRejectModal(item.scope, item.id)}
                          >
                            <X size={16} />
                          </button>
                          <button
                            type="button"
                            className="btn-review-action edit"
                            title="Edit Record"
                            onClick={() => setEditingRecord(item)}
                          >
                            <Pencil size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {isBatchWizardOpen && (
        <BatchReviewWizard
          isOpen={isBatchWizardOpen}
          onClose={() => {
            setIsBatchWizardOpen(false);
            fetchPendingEmissions(true);
          }}
          facilities={facilities}
        />
      )}
      {editingRecord && (
        <EditEmissionModal
          isOpen={Boolean(editingRecord)}
          onClose={() => setEditingRecord(null)}
          emission={editingRecord}
          facilities={facilities}
          onSuccess={() => fetchPendingEmissions(true)}
        />
      )}
    </div>
  );
};

export default PendingReviewTab;
