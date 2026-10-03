import React from "react";
import { AlertTriangle, Check, CheckCircle, ChevronLeft, ChevronRight, Search, X } from "lucide-react";

// Extracted from QADashboard.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const QADashboardZeroAnomaliesDetected = ({ PAGE_SIZE, anomaliesSummary, currentPage, data, filteredRecords, handleBulkResolve, handleSingleResolve, offset, resolving, returned_count, searchQuery, selectedIds, setOffset, setSearchQuery, setSelectedIds, setStatusFilter, statusFilter, toggleSelect, toggleSelectAll, totalPages, total_flagged_count }) => (
<div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.9))]! [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! [border-radius:var(--radius-lg)]! [box-shadow:var(--shadow-card,_0_4px_20px_-2px_rgba(15,_23,_42,_0.05))]! [overflow:hidden]! [display:flex]! [flex-direction:column]">
                        {/* Table Toolbar */}
                        <div className="[padding:18px_24px]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [display:flex]! [justify-content:space-between] [align-items:center] [flex-wrap:wrap] [gap:14px] [background:rgba(248,_250,_252,_0.4)]!">
                            <div className="flex! gap-[12px]! items-center! flex-wrap!">
                                {/* Search Box */}
                                <div className="qa-search-box">
                                    <Search size={14} />
                                    <input
                                        type="text"
                                        className="qa-search-input"
                                        placeholder="Search by ID, process, or reason…"
                                        value={searchQuery}
                                        onChange={e => setSearchQuery(e.target.value)}
                                    />
                                </div>

                                {/* Status Filters */}
                                <div className="[display:flex]! [gap:6px] [align-items:center]">
                                    <button
                                        aria-pressed={statusFilter === 'all'}
                                        className={`qa-status-filter-btn ${statusFilter === 'all' ? 'active' : ''}`}
                                        onClick={() => { setStatusFilter('all'); setOffset(0); }}
                                    >
                                        <span>All Statuses</span>
                                        {anomaliesSummary.all > 0 && (
                                            <span className="qa-status-pill-count">{anomaliesSummary.all}</span>
                                        )}
                                    </button>
                                    <button
                                        aria-pressed={statusFilter === 'pending'}
                                        className={`qa-status-filter-btn ${statusFilter === 'pending' ? 'active' : ''}`}
                                        onClick={() => { setStatusFilter('pending'); setOffset(0); }}
                                    >
                                        <span>Pending Review</span>
                                        {anomaliesSummary.pending > 0 && (
                                            <span className="qa-status-pill-count">{anomaliesSummary.pending}</span>
                                        )}
                                    </button>
                                    <button
                                        aria-pressed={statusFilter === 'verified'}
                                        className={`qa-status-filter-btn ${statusFilter === 'verified' ? 'active' : ''}`}
                                        onClick={() => { setStatusFilter('verified'); setOffset(0); }}
                                    >
                                        <span>Verified</span>
                                        {anomaliesSummary.verified > 0 && (
                                            <span className="qa-status-pill-count">{anomaliesSummary.verified}</span>
                                        )}
                                    </button>
                                    <button
                                        aria-pressed={statusFilter === 'rejected'}
                                        className={`qa-status-filter-btn ${statusFilter === 'rejected' ? 'active' : ''}`}
                                        onClick={() => { setStatusFilter('rejected'); setOffset(0); }}
                                    >
                                        <span>Rejected</span>
                                        {anomaliesSummary.rejected > 0 && (
                                            <span className="qa-status-pill-count">{anomaliesSummary.rejected}</span>
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Bulk Action Controls (When items selected) */}
                            {selectedIds.size > 0 ? (
                                <div className="[display:flex]! [align-items:center] [gap:12px] [background:rgba(255,_247,_237,_0.9)]! [padding:8px_16px]! [border-radius:var(--radius-md)]! [border:1px_solid_rgba(255,_102,_0,_0.25)]!">
                                    <span className="text-[length:0.82rem]! text-[color:#9a3412]! font-semibold!">
                                        {selectedIds.size} record{selectedIds.size > 1 ? 's' : ''} selected
                                    </span>
                                    <button
                                        className="[padding:4px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [cursor:pointer]! [transition:all_0.15s_ease]! [border:1px_solid_transparent]! qa-btn-approve p-[6px_12px]! text-[length:0.8rem]!"
                                       
                                        onClick={() => handleBulkResolve('Verified')}
                                        disabled={resolving}
                                    >
                                        <Check size={13} className="mr-[4px]!" />
                                        {resolving ? '…' : 'Approve Selected'}
                                    </button>
                                    <button
                                        className="[padding:4px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [cursor:pointer]! [transition:all_0.15s_ease]! [border:1px_solid_transparent]! qa-btn-reject p-[6px_12px]! text-[length:0.8rem]!"
                                       
                                        onClick={() => handleBulkResolve('Rejected')}
                                        disabled={resolving}
                                    >
                                        <X size={13} className="mr-[4px]!" />
                                        {resolving ? '…' : 'Reject Flags'}
                                    </button>
                                    <button
                                        style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.78rem', textDecoration: 'underline' }}
                                        onClick={() => setSelectedIds(new Set())}
                                    >
                                        Deselect
                                    </button>
                                </div>
                            ) : (
                                <span className="text-[length:0.82rem]! text-[color:#64748b]!">
                                    Showing {filteredRecords.length} flagged records
                                </span>
                            )}
                        </div>

                        {/* Table or Empty State */}
                        {filteredRecords.length === 0 ? (
                            <div className="p-[64px_24px]! text-center!">
                                {total_flagged_count === 0 ? (
                                    <>
                                        <div style={{ 
                                            background: '#ecfdf5', color: "#2e7d32", width: '64px', height: '64px', 
                                            borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', 
                                            margin: '0 auto 16px auto' 
                                        }}>
                                            <CheckCircle size={32} />
                                        </div>
                                        <h3 className="text-[length:1.25rem]! text-[color:#0f172a]! font-bold! mb-[8px]!">
                                            Zero Anomalies Detected
                                        </h3>
                                        <p className="text-[color:#64748b]! max-w-[440px]! m-[0_auto]!">
                                            No statistical outliers or data quality flags detected matching your current filters.
                                            {/* BUG-084: say what is actually known, not "fully verified" */}
                                            {data.pending_review_count > 0
                                                ? ` ${data.pending_review_count} record(s) are still awaiting reviewer approval.`
                                                : " All records in scope have been reviewed."}
                                        </p>
                                    </>
                                ) : (
                                    <>
                                        <div style={{ 
                                            background: '#fef3c7', color: '#b45309', width: '64px', height: '64px', 
                                            borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', 
                                            margin: '0 auto 16px auto' 
                                        }}>
                                            <Search size={32} />
                                        </div>
                                        <h3 className="text-[length:1.25rem]! text-[color:#0f172a]! font-bold! mb-[8px]!">
                                            No Matching Records
                                        </h3>
                                        <p className="text-[color:#64748b]! max-w-[440px]! m-[0_auto_16px_auto]!">
                                            No flagged records match your current search query "{searchQuery}" or status filter "{statusFilter}".
                                        </p>
                                        <button
                                            className="qa-btn-action qa-btn-secondary"
                                            onClick={() => { setSearchQuery(''); setStatusFilter('all'); setOffset(0); }}
                                        >
                                            Clear Filters
                                        </button>
                                    </>
                                )}
                            </div>
                        ) : (
                            <>
                                <div className="[overflow-x:auto]! [width:100%]!">
                                    <table className="[width:100%]! [border-collapse:collapse]! [text-align:left]!">
                                        <thead>
                                            <tr>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap] w-[40px]!">
                                                    <input
                                                        type="checkbox"
                                                        aria-label="Select all records"
                                                        checked={
                                                            filteredRecords.length > 0 && 
                                                            filteredRecords.every(r => selectedIds.has(`${r.scope}-${r.id}`))
                                                        }
                                                        onChange={() => toggleSelectAll(filteredRecords)}
                                                    />
                                                </th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">Record ID</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">Scope</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">Period</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">Process / Source</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">QA Flag Reason</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">Emissions (tCO₂e)</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap]">Status</th>
                                                <th className="[padding:14px_18px]! [font-size:var(--text-xs)]! [text-transform:uppercase]! [letter-spacing:0.06em] [font-weight:700]! [color:var(--color-ink-500)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.8)]! [background:rgba(248,_250,_252,_0.7)]! [white-space:nowrap] text-right!">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredRecords.map(record => {
                                                const key = `${record.scope}-${record.id}`;
                                                const isSelected = selectedIds.has(key);
                                                const status = (record.status || 'Pending Review').toLowerCase();
                                                const statusClass = status.includes('verified') ? 'verified' : status.includes('rejected') ? 'rejected' : 'pending';

                                                return (
                                                    <tr 
                                                        key={key} 
                                                        className={`qa-tr ${isSelected ? 'selected' : ''}`}
                                                    >
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle]">
                                                            <input
                                                                type="checkbox"
                                                                aria-label={`Select record ${record.id}`}
                                                                checked={isSelected}
                                                                onChange={() => toggleSelect(record.scope, record.id)}
                                                            />
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle] font-mono! font-semibold! text-[color:#0f172a]!">
                                                            {record.record_id || `REC-${record.id}`}
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle]">
                                                            <span className={`qa-scope-badge scope-${record.scope}`}>
                                                                Scope {record.scope}
                                                            </span>
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle] text-[color:#475569]!">
                                                            {record.year || '—'} {record.month ? `/ M${record.month}` : ''}
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle] font-medium! text-[color:#1e293b]!">
                                                            {record.process_type || '—'}
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle]">
                                                            <span className="[display:inline-flex]! [align-items:center] [gap:6px] [padding:4px_10px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:500]! [background:var(--color-amber-50)]! [color:var(--color-amber-700)]! [border:1px_solid_#fef3c7]!">
                                                                <AlertTriangle size={13} />
                                                                {record.qa_flag}
                                                            </span>
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle] font-mono! font-bold! text-[color:#0f172a]!">
                                                            {record.co2e != null ? Number(record.co2e).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle]">
                                                            <span className={`qa-status-pill ${statusClass}`}>
                                                                {record.status || 'Pending Review'}
                                                            </span>
                                                        </td>
                                                        <td className="[padding:14px_18px]! [font-size:var(--text-base)]! [color:var(--color-ink-700)]! [border-bottom:1px_solid_rgba(226,_232,_240,_0.6)]! [vertical-align:middle] text-right!">
                                                            <div className="inline-flex! gap-[6px]!">
                                                                <button
                                                                    className="[padding:4px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [cursor:pointer]! [transition:all_0.15s_ease]! [border:1px_solid_transparent]! qa-btn-approve"
                                                                    onClick={() => handleSingleResolve(record.scope, record.id, 'Verified')}
                                                                    disabled={resolving}
                                                                    title="Approve / Mark Verified"
                                                                >
                                                                    <Check size={13} />
                                                                </button>
                                                                <button
                                                                    className="[padding:4px_8px]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [font-weight:600]! [cursor:pointer]! [transition:all_0.15s_ease]! [border:1px_solid_transparent]! qa-btn-reject"
                                                                    onClick={() => handleSingleResolve(record.scope, record.id, 'Rejected')}
                                                                    disabled={resolving}
                                                                    title="Reject / Outlier"
                                                                >
                                                                    <X size={13} />
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Pagination Controls */}
                                {total_flagged_count > PAGE_SIZE && (
                                    <div style={{ 
                                        padding: '16px 24px', display: 'flex', alignItems: 'center', 
                                        justifyContent: 'space-between', borderTop: '1px solid rgba(226,232,240,0.8)' 
                                    }}>
                                        <span className="text-[length:0.82rem]! text-[color:#64748b]!">
                                            {searchQuery || statusFilter !== 'all'
                                                ? `Showing ${filteredRecords.length} filtered record${filteredRecords.length === 1 ? '' : 's'} on this page (${total_flagged_count} total in inventory)`
                                                : `Showing ${offset + 1}–${Math.min(offset + returned_count, total_flagged_count)} of ${total_flagged_count} flagged records`
                                            }
                                        </span>
                                        <div className="flex! gap-[6px]! items-center!">
                                            <button
                                                className="qa-btn-action qa-btn-secondary h-[32px]! p-[0_10px]!"
                                               
                                                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                                                disabled={offset === 0}
                                            >
                                                <ChevronLeft size={14} />
                                            </button>
                                            <span className="text-[length:0.82rem]! text-[color:#334155]! font-semibold! p-[0_8px]!">
                                                Page {currentPage} / {totalPages}
                                            </span>
                                            <button
                                                className="qa-btn-action qa-btn-secondary h-[32px]! p-[0_10px]!"
                                               
                                                onClick={() => setOffset(offset + PAGE_SIZE)}
                                                disabled={offset + PAGE_SIZE >= total_flagged_count}
                                            >
                                                <ChevronRight size={14} />
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
);

export default QADashboardZeroAnomaliesDetected;
