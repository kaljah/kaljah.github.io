import AuditTrailFiltersBarCard from "./audit-trail/AuditTrailFiltersBarCard";
import AuditTrailAuditTimeline from "./audit-trail/AuditTrailAuditTimeline";
import { Badge, DataTable, Dialog, SegmentedControl } from "../ui";
import { NativeSelect } from "../ui/NativeSelect";
import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "../api";
import {
  Plus,
  Edit3,
  Trash2,
  Eye,
  Download,
  Search,
  RefreshCw,
  Shield,
  ShieldAlert,
  LogIn,
  User as UserIcon,
  History,
  Clock,
  ArrowRight,
  Filter,
  Activity,
  Database,
  FileText,
  Globe,
  X,
  CheckCircle2,
  XCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Code,
  FileSpreadsheet,
  RotateCcw,
} from "lucide-react";
import { useToast } from "../components/Toast";
import "./AuditTrail.css";

const AuditTrail = () => {
  const toast = useToast();

  // Core Data States
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [stats, setStats] = useState({
    totalEvents: 0,
    totalLogins: 0,
    dataMutations: 0,
    securityAlerts: 0,
    uniqueUsers: 0,
  });

  // Filter & Search States
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filterUser, setFilterUser] = useState("all");
  const [filterAction, setFilterAction] = useState("all");
  const [filterEntity, setFilterEntity] = useState("all");
  const [timeframe, setTimeframe] = useState("all");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");

  // Pagination States
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);

  // Filter Option Lists
  const [availableFilters, setAvailableFilters] = useState({
    users: [],
    actions: [],
    entities: [],
  });

  // Expanded Raw JSON Inspection Set
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [view, setView] = useState("table");
  const [detailLog, setDetailLog] = useState(null);
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false);
  const exportMenuRef = useRef(null);

  // Debounce search query changes
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setPage(1); // reset to page 1 on new search
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Click outside to close export menu
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target)) {
        setExportDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Compute ISO dates based on timeframe preset
  const getDateRangeParams = useCallback(() => {
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
      const params = {
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
      const rawLogs = Array.isArray(res.data) ? res.data : (res.data?.logs || []);
      const total = res.data?.total ?? rawLogs.length;
      const pages = res.data?.pages ?? Math.max(1, Math.ceil(total / limit));

      setAuditLogs(rawLogs);
      setTotalRecords(total);
      setTotalPages(pages);

      // Auto-compute or update stats from loaded records if server stats not yet loaded
      setStats((prev) => {
        if (prev.totalEvents > 0 && prev.totalLogins > 0) return prev;
        const logins = rawLogs.filter((l) => (l.action || "").toUpperCase() === "LOGIN").length;
        const mutations = rawLogs.filter((l) =>
          ["CREATE", "UPDATE", "DELETE"].includes((l.action || "").toUpperCase())
        ).length;
        const alerts = rawLogs.filter((l) =>
          ["SECURITY", "FAILED_LOGIN", "SUSPICIOUS"].includes((l.action || "").toUpperCase())
        ).length;
        const unique = new Set(rawLogs.map((l) => l.user).filter(Boolean)).size;
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
  const handleExport = async (format) => {
    setExportDropdownOpen(false);
    toast.info(`Preparing ${format.toUpperCase()} compliance export...`);
    try {
      const params = { format };
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
  const toggleRawData = (id) => {
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

  // Action badge visuals
  const getActionConfig = (action) => {
    const act = (action || "").toUpperCase();
    switch (act) {
      case "CREATE":
      case "REGISTER":
        return {
          icon: <Plus size={18} />,
          color: "#10b981",
          bg: "rgba(16, 185, 129, 0.12)",
          border: "rgba(16, 185, 129, 0.3)",
        };
      case "UPDATE":
        return {
          icon: <Edit3 size={18} />,
          color: "#3b82f6",
          bg: "rgba(59, 130, 246, 0.12)",
          border: "rgba(59, 130, 246, 0.3)",
        };
      case "DELETE":
        return {
          icon: <Trash2 size={18} />,
          color: "#ef4444",
          bg: "rgba(239, 68, 68, 0.12)",
          border: "rgba(239, 68, 68, 0.3)",
        };
      case "LOGIN":
        return {
          icon: <LogIn size={18} />,
          color: "#0ea5e9",
          bg: "rgba(14, 165, 233, 0.12)",
          border: "rgba(14, 165, 233, 0.3)",
        };
      case "SECURITY":
        return {
          icon: <ShieldAlert size={18} />,
          color: "#f59e0b",
          bg: "rgba(245, 158, 11, 0.12)",
          border: "rgba(245, 158, 11, 0.3)",
        };
      case "EXPORT":
        return {
          icon: <Download size={18} />,
          color: "#8b5cf6",
          bg: "rgba(139, 92, 246, 0.12)",
          border: "rgba(139, 92, 246, 0.3)",
        };
      case "VIEW":
        return {
          icon: <Eye size={18} />,
          color: "#64748b",
          bg: "rgba(100, 116, 139, 0.12)",
          border: "rgba(100, 116, 139, 0.3)",
        };
      case "APPROVE":
        return {
          icon: <CheckCircle2 size={18} />,
          color: "#16a34a",
          bg: "rgba(22, 163, 74, 0.12)",
          border: "rgba(22, 163, 74, 0.3)",
        };
      case "REJECT":
        return {
          icon: <XCircle size={18} />,
          color: "#dc2626",
          bg: "rgba(220, 38, 38, 0.12)",
          border: "rgba(220, 38, 38, 0.3)",
        };
      default:
        return {
          icon: <Activity size={18} />,
          color: "#64748b",
          bg: "rgba(100, 116, 139, 0.12)",
          border: "rgba(100, 116, 139, 0.3)",
        };
    }
  };

  // Format relative timestamp safely
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "Unknown time";
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return "Invalid date";

    const now = new Date();
    const diff = now - date;
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
  const formatFullDateTime = (timestamp) => {
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
  const formatDiffVal = (val) => {
    if (val === null || val === undefined) return "null";
    if (typeof val === "boolean") return val ? "true" : "false";
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  };

  const actionTone = (action) => {
    const a = String(action || "").toUpperCase();
    if (/CREATE|REGISTER|APPROVE|VERIFY/.test(a)) return "success";
    if (/DELETE|REJECT|FAIL|DENY/.test(a)) return "danger";
    if (/UPDATE|EDIT|CHANGE/.test(a)) return "info";
    if (/WARN|FLAG/.test(a)) return "warning";
    return "neutral";
  };

  const tableColumns = [
    {
      id: "time",
      header: "Time",
      accessorFn: (l) => l.timestamp,
      cell: (c) => (
        <span title={formatFullDateTime(c.getValue())} className="text-text-secondary">
          {formatTimestamp(c.getValue())}
        </span>
      ),
    },
    { id: "user", header: "User", accessorFn: (l) => l.user || "System" },
    {
      id: "action",
      header: "Action",
      accessorFn: (l) => l.action,
      cell: (c) => <Badge tone={actionTone(c.getValue())}>{c.getValue()}</Badge>,
    },
    { id: "entity", header: "Entity", accessorFn: (l) => l.entity || "-" },
    {
      id: "description",
      header: "Description",
      accessorFn: (l) => l.description || l.details || "No details recorded",
      cell: (c) => <span className="block max-w-[32rem] truncate" title={c.getValue()}>{c.getValue()}</span>,
    },
    { id: "ref", header: "Ref", accessorFn: (l) => l.entityId || l.recordId || "-" },
    { id: "ip", header: "IP", accessorFn: (l) => l.ipAddress || "Local / System" },
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

  return (
    <div className="audit-trail">
      <div className="audit-container">
        {/* Header Title & Actions */}
        <div className="audit-page-header">
          <div>
            <div className="audit-badge-tag">
              <Shield size={14} />
              <span>Immutable Compliance Log</span>
            </div>
            <h1 className="section-title">Audit Trail &amp; System Activity</h1>
            <p className="[color:var(--text-secondary,_var(--color-ink-500))]! [font-size:var(--text-md)]! [margin:0]! [max-width:780px]! [line-height:1.5]">
              Comprehensive tamper-evident record of all emissions data, authentication, calculations, and administrative actions
            </p>
          </div>

          <div className="audit-header-actions">
            <SegmentedControl
              label="Audit view"
              value={view}
              onChange={setView}
              options={[
                { value: "table", label: "Table" },
                { value: "timeline", label: "Timeline" },
              ]}
            />
            <button
              className="btn-refresh-main"
              onClick={() => {
                fetchAuditLogs(true);
                fetchStats();
                fetchFilters();
                toast.info("Refreshed audit trail");
              }}
              disabled={isRefreshing}
            >
              <RefreshCw size={15} className={isRefreshing ? "[animation:spin_1s_linear_infinite]!" : ""} />
              <span>Refresh</span>
            </button>

            {/* Export Dropdown */}
            <div className="[position:relative]" ref={exportMenuRef}>
              <button
                className="btn-export-main"
                onClick={() => setExportDropdownOpen(!exportDropdownOpen)}
              >
                <Download size={15} />
                <span>Export Audit Log</span>
                <ChevronDown size={14} />
              </button>

              {exportDropdownOpen && (
                <div className="export-menu">
                  <button onClick={() => handleExport("csv")}>
                    <FileSpreadsheet size={15} className="[margin-top:2px]! [flex-shrink:0] [color:var(--color-green-700)]!" />
                    <div className="export-text">
                      <strong>CSV Spreadsheet</strong>
                      <span>Compliant with audit tools &amp; Excel</span>
                    </div>
                  </button>
                  <button onClick={() => handleExport("json")}>
                    <FileText size={15} className="[margin-top:2px]! [flex-shrink:0] [color:var(--color-violet-700)]!" />
                    <div className="export-text">
                      <strong>JSON Structured Data</strong>
                      <span>Full metadata &amp; field diffs</span>
                    </div>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* KPI Metric Summary Cards */}
        <div className="audit-stats-grid">
          <div className="stat-card">
            <div className="stat-icon-box total-events">
              <Activity size={20} />
            </div>
            <div className="[display:flex]! [flex-direction:column]">
              <span className="stat-label">Total Events Logged</span>
              <span className="stat-value">{stats.totalEvents.toLocaleString()}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-box logins">
              <LogIn size={20} />
            </div>
            <div className="[display:flex]! [flex-direction:column]">
              <span className="stat-label">User Logins</span>
              <span className="stat-value">{stats.totalLogins.toLocaleString()}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-box data-changes">
              <Database size={20} />
            </div>
            <div className="[display:flex]! [flex-direction:column]">
              <span className="stat-label">Data Changes</span>
              <span className="stat-value">{stats.dataMutations.toLocaleString()}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-box security-events">
              <ShieldAlert size={20} />
            </div>
            <div className="[display:flex]! [flex-direction:column]">
              <span className="stat-label">Security &amp; Alerts</span>
              <span className="stat-value">{stats.securityAlerts.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Search & Multi-Filter Control Bar */}
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

        {/* Main Content Area */}
        {loading ? (
          <div className="[display:flex]! [flex-direction:column] [gap:16px]">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton-card">
                <div className="[width:40px]! [height:40px]! [background:var(--color-ink-100)]! [border-radius:var(--radius-md)]! [flex-shrink:0] [animation:pulse_1.5s_infinite]!" />
                <div className="[flex:1] [display:flex]! [flex-direction:column] [gap:10px]">
                  <div className="skeleton-line w-40" />
                  <div className="skeleton-line w-80" />
                  <div className="skeleton-line w-20" />
                </div>
              </div>
            ))}
          </div>
        ) : auditLogs.length === 0 ? (
          <div className="audit-empty-state">
            <div className="[width:64px]! [height:64px]! [background:var(--color-ink-100)]! [border-radius:50%]! [display:flex]! [align-items:center] [justify-content:center] [margin:0_auto_16px_auto]! [color:var(--color-ink-600)]!">
              <Filter size={32} />
            </div>
            <h3>No audit records found</h3>
            <p>
              {hasActiveFilters
                ? "No activity logs match your current filter and search criteria."
                : "No compliance audit records have been generated yet."}
            </p>
            {hasActiveFilters && (
              <button className="btn-clear-empty" onClick={resetFilters}>
                Clear All Filters
              </button>
            )}
          </div>
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
        getActionConfig={getActionConfig}
        toggleRawData={toggleRawData}
      />
        )}

        {/* Pagination Bar */}
        {totalRecords > 0 && (
          <div className="audit-pagination-bar">
            <div className="[font-size:var(--text-base)]! [color:var(--text-secondary,_var(--color-ink-500))]!">
              Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalRecords} total events)
            </div>

            <div className="pagination-controls">
              <div className="page-size-selector">
                <label>Rows:</label>
                <NativeSelect
                  value={limit}
                  onChange={(e) => {
                    setLimit(Number(e.target.value));
                    setPage(1);
                  }}
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </NativeSelect>
              </div>

              <div className="[display:flex]! [align-items:center] [gap:10px]">
                <button
                  className="btn-page-nav"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  title="Previous Page"
                >
                  <ChevronLeft size={16} />
                  <span>Prev</span>
                </button>

                <span className="[font-size:var(--text-sm)]! [font-weight:600]! [color:var(--color-ink-600)]! [min-width:44px] [text-align:center]!">
                  {page} / {totalPages}
                </span>

                <button
                  className="btn-page-nav"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  title="Next Page"
                >
                  <span>Next</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
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
