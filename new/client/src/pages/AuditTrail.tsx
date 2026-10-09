import AuditTrailFiltersBarCard from "./audit-trail/AuditTrailFiltersBarCard";
import AuditTrailAuditTimeline from "./audit-trail/AuditTrailAuditTimeline";
import { AuditEmpty, AuditHeader, AuditIntegrityCheck, AuditPagination, AuditSkeleton, AuditStats, actionStyle } from "./audit-trail/AuditTrailChrome";
import { Badge, DataTable, Dialog, type BadgeTone } from "../ui";
import React, { useState, useEffect, useCallback } from "react";
import api from "../api";
import { useToast } from "../components/Toast";
import type { ColumnDef } from "@tanstack/react-table";

export interface AuditLog {
  id: string | number;
  timestamp?: string;
  user?: string;
  action?: string;
  entity?: string;
  description?: string;
  details?: string;
  entityId?: string | number;
  recordId?: string | number;
  ipAddress?: string;
  changes?: Record<string, any>;
  metadata?: Record<string, any>;
  [key: string]: any;
}

const AuditTrail: React.FC = () => {
  const toast = useToast();

  // Core Data States
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [stats, setStats] = useState({
    totalEvents: 0,
    totalLogins: 0,
    dataMutations: 0,
    securityAlerts: 0,
    uniqueUsers: 0,
  });

  // Filter & Search States
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [filterUser, setFilterUser] = useState<string>("all");
  const [filterAction, setFilterAction] = useState<string>("all");
  const [filterEntity, setFilterEntity] = useState<string>("all");
  const [timeframe, setTimeframe] = useState<string>("all");
  const [customStartDate, setCustomStartDate] = useState<string>("");
  const [customEndDate, setCustomEndDate] = useState<string>("");

  // Pagination States
  const [page, setPage] = useState<number>(1);
  const [limit, setLimit] = useState<number>(50);

  // Filter Option Lists
  const [availableFilters, setAvailableFilters] = useState<{
    users: string[];
    actions: string[];
    entities: string[];
  }>({
    users: [],
    actions: [],
    entities: [],
  });

  // Expanded Raw JSON Inspection Set
  const [expandedRows, setExpandedRows] = useState<Set<string | number>>(new Set());
  const [view, setView] = useState<string>("table");
  const [detailLog, setDetailLog] = useState<AuditLog | null>(null);

  // Debounce search query changes
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setPage(1); // reset to page 1 on new search
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Compute ISO dates based on timeframe preset
  const getDateRangeParams = useCallback((): { start_date?: string; end_date?: string } => {
    const now = new Date();
    if (timeframe === "today") {
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      return { start_date: start.toISOString() };
    }
    if (timeframe === "7days") {
      const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return { start_date: start.toISOString() };
    }
    if (timeframe === "30days") {
      const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      return { start_date: start.toISOString() };
    }
    if (timeframe === "custom") {
      if (customStartDate && customEndDate) {
        const start = new Date(customStartDate);
        const end = new Date(customEndDate);
        end.setHours(23, 59, 59, 999);
        return {
          start_date: start.toISOString(),
          end_date: end.toISOString(),
        };
      }
      return {};
    }
    return {};
  }, [timeframe, customStartDate, customEndDate]);

  // Fetch filter options
  const fetchFilters = async () => {
    try {
      const res = await api.get("/audit/filters");
      if (res.data) {
        setAvailableFilters({
          users: res.data.users || [],
          actions: res.data.actions || [],
          entities: res.data.entities || [],
        });
      }
    } catch (error) {
      console.error("Failed to fetch audit filters:", error);
    }
  };

  // Fetch stats overview
  const fetchStats = async () => {
    try {
      const res = await api.get("/audit/stats");
      if (res.data) {
        setStats(res.data);
      }
    } catch {
      // Endpoint may be 404 if Flask backend has not been restarted yet
      // Fallback is computed automatically from audit records in fetchAuditLogs
    }
  };

  // Fetch paginated & filtered audit logs
  const fetchAuditLogs = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setIsRefreshing(true);
    try {
      const params: Record<string, any> = {
        page,
        limit,
      };

      if (filterUser !== "all") params.user = filterUser;
      if (filterAction !== "all") params.action = filterAction;
      if (filterEntity !== "all") params.entity = filterEntity;
      if (debouncedSearch) params.search = debouncedSearch;

      const dateParams = getDateRangeParams();
      Object.assign(params, dateParams);

      const res = await api.get("/audit", { params });
      const rawLogs: AuditLog[] = (Array.isArray(res.data) ? res.data : (res.data?.logs || [])).map((l: any, idx: number) => ({ ...l, id: l.id ?? idx }));
      const total = res.data?.total ?? rawLogs.length;
      const pages = res.data?.pages ?? Math.max(1, Math.ceil(total / limit));

      setAuditLogs(rawLogs);
      setTotalRecords(total);
      setTotalPages(pages);

      // Auto-compute or update stats from loaded records if server stats not yet loaded
      setStats((prev) => {
        if (prev.totalEvents > 0 && prev.totalLogins > 0) return prev;
        const logins = rawLogs.filter((l: AuditLog) => (l.action || "").toUpperCase() === "LOGIN").length;
        const mutations = rawLogs.filter((l: AuditLog) =>
          ["CREATE", "UPDATE", "DELETE"].includes((l.action || "").toUpperCase())
        ).length;
        const alerts = rawLogs.filter((l: AuditLog) =>
          ["SECURITY", "FAILED_LOGIN", "SUSPICIOUS"].includes((l.action || "").toUpperCase())
        ).length;
        const unique = new Set(rawLogs.map((l: AuditLog) => l.user).filter(Boolean)).size;
        return {
          totalEvents: total || rawLogs.length,
          totalLogins: logins,
          dataMutations: mutations,
          securityAlerts: alerts,
          uniqueUsers: unique || 1,
        };
      });
    } catch (error) {
      console.error("Failed to fetch audit logs:", error);
      toast.error("Failed to load audit logs");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [page, limit, filterUser, filterAction, filterEntity, debouncedSearch, getDateRangeParams, toast]);

  // Initial load
  useEffect(() => {
    fetchFilters();
    fetchStats();
  }, []);

  // Fetch on filter or page change
  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  // Handle Export (CSV or JSON)
  const handleExport = async (format: "csv" | "json") => {
    toast.info(`Preparing ${format.toUpperCase()} compliance export...`);
    try {
      const params: Record<string, any> = { format };
      if (filterUser !== "all") params.user = filterUser;
      if (filterAction !== "all") params.action = filterAction;
      if (filterEntity !== "all") params.entity = filterEntity;
      if (debouncedSearch) params.search = debouncedSearch;

      const dateParams = getDateRangeParams();
      Object.assign(params, dateParams);

      const response = await api.get("/audit/export", {
        params,
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      const dateStr = new Date().toISOString().slice(0, 10);
      link.setAttribute("download", `carbon_tech_audit_${dateStr}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Exported audit logs successfully (${format.toUpperCase()})`);
      fetchStats(); // Update stats as export is logged
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("Failed to export audit logs");
    }
  };

  // Toggle raw payload inspection
  const toggleRawData = (id: string | number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Reset all filters
  const resetFilters = () => {
    setSearchQuery("");
    setFilterUser("all");
    setFilterAction("all");
    setFilterEntity("all");
    setTimeframe("all");
    setCustomStartDate("");
    setCustomEndDate("");
    setPage(1);
    toast.info("Filters reset to default");
  };

  const hasActiveFilters =
    searchQuery !== "" ||
    filterUser !== "all" ||
    filterAction !== "all" ||
    filterEntity !== "all" ||
    timeframe !== "all";

  // Format relative timestamp safely
  const formatTimestamp = (timestamp?: string | number | Date) => {
    if (!timestamp) return "Unknown time";
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return "Invalid date";

    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (diff < 60000) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Full formatted date & time
  const formatFullDateTime = (timestamp?: string | number | Date) => {
    if (!timestamp) return "—";
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return "—";
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  // Safe formatting for diff values (primitives, booleans, objects)
  const formatDiffVal = (val: any) => {
    if (val === null || val === undefined) return "null";
    if (typeof val === "boolean") return val ? "true" : "false";
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  };

  const actionTone = (action?: string): BadgeTone => {
    const a = String(action || "").toUpperCase();
    if (/CREATE|REGISTER|APPROVE|VERIFY/.test(a)) return "success";
    if (/DELETE|REJECT|FAIL|DENY/.test(a)) return "danger";
    if (/UPDATE|EDIT|CHANGE/.test(a)) return "info";
    if (/WARN|FLAG/.test(a)) return "warning";
    return "neutral";
  };

  const tableColumns: ColumnDef<AuditLog, any>[] = [
    {
      id: "time",
      header: "Time",
      accessorFn: (l: AuditLog) => l.timestamp,
      cell: (c) => (
        <span title={formatFullDateTime(c.getValue())} className="text-text-secondary">
          {formatTimestamp(c.getValue())}
        </span>
      ),
    },
    { id: "user", header: "User", accessorFn: (l: AuditLog) => l.user || "System" },
    {
      id: "action",
      header: "Action",
      accessorFn: (l: AuditLog) => l.action,
      cell: (c) => <Badge tone={actionTone(c.getValue())}>{c.getValue()}</Badge>,
    },
    { id: "entity", header: "Entity", accessorFn: (l: AuditLog) => l.entity || "-" },
    {
      id: "description",
      header: "Description",
      accessorFn: (l: AuditLog) => l.description || l.details || "No details recorded",
      cell: (c) => <span className="block max-w-[32rem] truncate" title={c.getValue()}>{c.getValue()}</span>,
    },
    { id: "ref", header: "Ref", accessorFn: (l: AuditLog) => l.entityId || l.recordId || "-" },
    { id: "ip", header: "IP", accessorFn: (l: AuditLog) => l.ipAddress || "Local / System" },
    {
      id: "details",
      header: "",
      enableSorting: false,
      enableHiding: false,
      meta: { pin: "right" },
      cell: (c) => (
        <button
          type="button"
          className="cursor-pointer rounded-md border border-border bg-surface px-2 py-1 text-sm font-semibold text-text hover:bg-ink-100"
          onClick={() => setDetailLog(c.row.original)}
        >
          Details
        </button>
      ),
    },
  ];

  const refreshAll = () => {
    fetchAuditLogs(true);
    fetchStats();
    fetchFilters();
    toast.info("Refreshed audit trail");
  };

  return (
    <div>
      <div className="mx-auto max-w-[1400px] px-4 py-5 md:px-7 md:py-6">
        <AuditHeader view={view} onView={setView} refreshing={isRefreshing} onRefresh={refreshAll} onExport={handleExport} />
        <AuditIntegrityCheck />
        <AuditStats stats={stats} />

        <AuditTrailFiltersBarCard
          auditLogs={auditLogs}
          availableFilters={availableFilters}
          customEndDate={customEndDate}
          customStartDate={customStartDate}
          filterAction={filterAction}
          filterEntity={filterEntity}
          filterUser={filterUser}
          hasActiveFilters={hasActiveFilters}
          resetFilters={resetFilters}
          searchQuery={searchQuery}
          setCustomEndDate={setCustomEndDate}
          setCustomStartDate={setCustomStartDate}
          setFilterAction={setFilterAction}
          setFilterEntity={setFilterEntity}
          setFilterUser={setFilterUser}
          setPage={setPage}
          setSearchQuery={setSearchQuery}
          setTimeframe={setTimeframe}
          timeframe={timeframe}
          totalRecords={totalRecords}
        />

        {loading ? (
          <AuditSkeleton />
        ) : auditLogs.length === 0 ? (
          <AuditEmpty filtered={hasActiveFilters} onReset={resetFilters} />
        ) : view === "table" ? (
          <DataTable
            tableId="audit-trail"
            caption="Audit trail events"
            density="compact"
            pageSize={100}
            data={auditLogs}
            columns={tableColumns}
            getRowId={(l) => String(l.id)}
          />
        ) : (
          <AuditTrailAuditTimeline
            auditLogs={auditLogs}
            expandedRows={expandedRows}
            formatDiffVal={formatDiffVal}
            formatFullDateTime={formatFullDateTime}
            formatTimestamp={formatTimestamp}
            actionStyle={actionStyle}
            toggleRawData={toggleRawData}
          />
        )}

        {totalRecords > 0 && (
          <AuditPagination
            page={page}
            totalPages={totalPages}
            totalRecords={totalRecords}
            limit={limit}
            onLimit={(n) => {
              setLimit(n);
              setPage(1);
            }}
            onPage={setPage}
          />
        )}
      </div>

      <Dialog
        open={Boolean(detailLog)}
        onOpenChange={(o) => !o && setDetailLog(null)}
        title="Audit event"
        description={detailLog ? `${detailLog.action} by ${detailLog.user || "System"} (${formatFullDateTime(detailLog.timestamp)})` : undefined}
        maxWidth="44rem"
      >
        {detailLog && (
          <div className="flex flex-col gap-3">
            <p className="text-base text-text">{detailLog.description || detailLog.details || "No details recorded"}</p>
            <pre className="max-h-96 overflow-auto rounded-md bg-ink-50 p-3 text-sm text-text">
              {JSON.stringify(detailLog, null, 2)}
            </pre>
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default AuditTrail;
