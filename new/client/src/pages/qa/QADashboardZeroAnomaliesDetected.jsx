import React from "react";
import { AlertTriangle, Check, CheckCircle, ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { Badge, Button, Card, EmptyState, IconButton, Input, StatusPill } from "../../ui";
import { cn } from "../../ui/cn";

const STATUS_FILTERS = [
  { value: "all", label: "All Statuses", count: "all" },
  { value: "pending", label: "Pending Review", count: "pending" },
  { value: "verified", label: "Verified", count: "verified" },
  { value: "rejected", label: "Rejected", count: "rejected" },
];
const SCOPE_TONE = { 1: "brand", 2: "info", 3: "neutral" };

const th = "whitespace-nowrap border-b border-border px-4 py-3.5 text-left text-xs font-bold uppercase tracking-wide text-text-secondary";
const td = "border-b border-ink-100 px-4 py-3.5 align-middle text-base text-ink-700";

/** Flagged-record review queue: filters, bulk approve/reject, row actions and paging. */
const QADashboardZeroAnomaliesDetected = ({ PAGE_SIZE, anomaliesSummary, currentPage, data, filteredRecords, handleBulkResolve, handleSingleResolve, offset, resolving, returned_count, searchQuery, selectedIds, setOffset, setSearchQuery, setSelectedIds, setStatusFilter, statusFilter, toggleSelect, toggleSelectAll, totalPages, total_flagged_count }) => {
  const resetFilters = () => {
    setSearchQuery("");
    setStatusFilter("all");
    setOffset(0);
  };
  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-60">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
            <Input aria-label="Search flagged records" className="h-9 pl-9" placeholder="Search by ID, process, or reason…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          <div role="group" aria-label="Status filter" className="flex flex-wrap items-center gap-1.5">
            {STATUS_FILTERS.map((f) => (
              <Button
                key={f.value}
                size="sm"
                variant={statusFilter === f.value ? "primary" : "secondary"}
                aria-pressed={statusFilter === f.value}
                onClick={() => {
                  setStatusFilter(f.value);
                  setOffset(0);
                }}
              >
                {f.label}
                {anomaliesSummary[f.count] > 0 && <span className="qa-status-pill-count rounded-md bg-black/10 px-1.5 text-xs font-bold">{anomaliesSummary[f.count]}</span>}
              </Button>
            ))}
          </div>
        </div>

        {selectedIds.size > 0 ? (
          <div className="flex flex-wrap items-center gap-3 rounded-md border border-brand-100 bg-brand-50 px-4 py-2">
            <span className="text-sm font-semibold text-brand-700">
              {selectedIds.size} record{selectedIds.size > 1 ? "s" : ""} selected
            </span>
            <Button size="sm" onClick={() => handleBulkResolve("Verified")} disabled={resolving}>
              <Check className="size-3.5" aria-hidden="true" /> {resolving ? "…" : "Approve Selected"}
            </Button>
            <Button size="sm" variant="danger" onClick={() => handleBulkResolve("Rejected")} disabled={resolving}>
              <X className="size-3.5" aria-hidden="true" /> {resolving ? "…" : "Reject Flags"}
            </Button>
            <Button size="sm" variant="link" onClick={() => setSelectedIds(new Set())}>
              Deselect
            </Button>
          </div>
        ) : (
          <span className="text-sm text-text-secondary">Showing {filteredRecords.length} flagged records</span>
        )}
      </div>

      {filteredRecords.length === 0 ? (
        total_flagged_count === 0 ? (
          <EmptyState
            icon={CheckCircle}
            title="Zero Anomalies Detected"
            className="py-16"
            description={
              /* BUG-084: say what is actually known, not "fully verified" */
              `No statistical outliers or data quality flags detected matching your current filters.${data.pending_review_count > 0 ? ` ${data.pending_review_count} record(s) are still awaiting reviewer approval.` : " All records in scope have been reviewed."}`
            }
          />
        ) : (
          <EmptyState
            icon={Search}
            title="No Matching Records"
            className="py-16"
            description={`No flagged records match your current search query "${searchQuery}" or status filter "${statusFilter}".`}
            action={<Button variant="secondary" onClick={resetFilters}>Clear Filters</Button>}
          />
        )
      ) : (
        <>
          <div className="w-full overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr>
                  <th scope="col" className={th}>
                    <input
                      type="checkbox"
                      className="size-4 accent-brand-500"
                      aria-label="Select all records"
                      checked={filteredRecords.length > 0 && filteredRecords.every((r) => selectedIds.has(`${r.scope}-${r.id}`))}
                      onChange={() => toggleSelectAll(filteredRecords)}
                    />
                  </th>
                  {["Record ID", "Scope", "Period", "Process", "QA Flag", "Emissions (tCO₂e)", "Status", "Actions"].map((h) => (
                    <th key={h} scope="col" className={th}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((record) => {
                  const key = `${record.scope}-${record.id}`;
                  const isSelected = selectedIds.has(key);
                  return (
                    <tr key={key} className={cn("hover:bg-ink-50", isSelected && "selected bg-success-bg/40")}>
                      <td className={td}>
                        <input type="checkbox" className="size-4 accent-brand-500" aria-label={`Select record ${record.id}`} checked={isSelected} onChange={() => toggleSelect(record.scope, record.id)} />
                      </td>
                      <td className={cn(td, "font-mono font-semibold")}>{record.record_id || `REC-${record.id}`}</td>
                      <td className={td}>
                        <Badge tone={SCOPE_TONE[record.scope] || "neutral"}>Scope {record.scope}</Badge>
                      </td>
                      <td className={cn(td, "text-ink-600")}>
                        {record.year || "—"} {record.month ? `/ M${record.month}` : ""}
                      </td>
                      <td className={cn(td, "font-medium")}>{record.process_type || "—"}</td>
                      <td className={td}>
                        <Badge tone="warning" className="gap-1.5">
                          <AlertTriangle className="size-3.5" aria-hidden="true" />
                          {record.qa_flag}
                        </Badge>
                      </td>
                      <td className={cn(td, "font-mono font-bold")}>{record.co2e != null ? Number(record.co2e).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0.00"}</td>
                      <td className={td}>
                        <StatusPill status={(record.status || "Pending Review").split(" ")[0]}>{record.status || "Pending Review"}</StatusPill>
                      </td>
                      <td className={td}>
                        <div className="inline-flex gap-1.5">
                          <IconButton label="Approve / Mark Verified" title="Approve / Mark Verified" className="size-8 text-success-fg" disabled={resolving} onClick={() => handleSingleResolve(record.scope, record.id, "Verified")}>
                            <Check className="size-3.5" aria-hidden="true" />
                          </IconButton>
                          <IconButton label="Reject / Outlier" title="Reject / Outlier" className="size-8 text-danger-fg" disabled={resolving} onClick={() => handleSingleResolve(record.scope, record.id, "Rejected")}>
                            <X className="size-3.5" aria-hidden="true" />
                          </IconButton>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {total_flagged_count > PAGE_SIZE && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-6 py-4">
              <span className="text-sm text-text-secondary">
                {searchQuery || statusFilter !== "all"
                  ? `Showing ${filteredRecords.length} filtered record${filteredRecords.length === 1 ? "" : "s"} on this page (${total_flagged_count} total in inventory)`
                  : `Showing ${offset + 1}–${Math.min(offset + returned_count, total_flagged_count)} of ${total_flagged_count} flagged records`}
              </span>
              <div className="flex items-center gap-1.5">
                <IconButton label="Previous page" variant="secondary" className="size-8" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0}>
                  <ChevronLeft className="size-3.5" aria-hidden="true" />
                </IconButton>
                <span className="px-2 text-sm font-semibold text-ink-700">
                  Page {currentPage} / {totalPages}
                </span>
                <IconButton label="Next page" variant="secondary" className="size-8" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total_flagged_count}>
                  <ChevronRight className="size-3.5" aria-hidden="true" />
                </IconButton>
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
};

export default QADashboardZeroAnomaliesDetected;
