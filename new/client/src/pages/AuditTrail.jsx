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
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import { useLayout } from "../context/LayoutContext";
import "./AuditTrail.css";

const AuditTrail = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();

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
    } catch (error) {
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

  // Top Bar configuration
  useEffect(() => {
    setTopBarLeft(
      <div className="breadcrumbs">
        <History size={16} style={{ color: "var(--accent-color, #ff6600)" }} />
        <span>Compliance</span>
        <span className="breadcrumb-separator">/</span>
        <span className="breadcrumb-current">Audit Trail</span>
      </div>,
    );

    setTopBarRight(
      <div className="top-actions">
        <div className="user-profile-sm">
          <div className="user-avatar-sm">
            <UserIcon size={14} />
          </div>
          <span className="user-name-sm">{user?.fullName || "Compliance Officer"}</span>
        </div>
      </div>,
    );

    return () => {
      setTopBarLeft(null);
      setTopBarRight(null);
    };
  }, [user, setTopBarLeft, setTopBarRight]);

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
            <p className="section-subtitle">
              Comprehensive tamper-evident record of all emissions data, authentication, calculations, and administrative actions
            </p>
          </div>

          <div className="audit-header-actions">
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
              <RefreshCw size={15} className={isRefreshing ? "spin-animate" : ""} />
              <span>Refresh</span>
            </button>

            {/* Export Dropdown */}
            <div className="export-dropdown-wrapper" ref={exportMenuRef}>
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
                    <FileSpreadsheet size={15} className="export-icon csv-icon" />
                    <div className="export-text">
                      <strong>CSV Spreadsheet</strong>
                      <span>Compliant with audit tools &amp; Excel</span>
                    </div>
                  </button>
                  <button onClick={() => handleExport("json")}>
                    <FileText size={15} className="export-icon json-icon" />
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
            <div className="stat-content">
              <span className="stat-label">Total Events Logged</span>
              <span className="stat-value">{stats.totalEvents.toLocaleString()}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-box logins">
              <LogIn size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-label">User Logins</span>
              <span className="stat-value">{stats.totalLogins.toLocaleString()}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-box data-changes">
              <Database size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-label">Data Changes</span>
              <span className="stat-value">{stats.dataMutations.toLocaleString()}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-box security-events">
              <ShieldAlert size={20} />
            </div>
            <div className="stat-content">
              <span className="stat-label">Security &amp; Alerts</span>
              <span className="stat-value">{stats.securityAlerts.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Search & Multi-Filter Control Bar */}
        <div className="filters-bar-card">
          <div className="filter-search-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by user, description, record ID, IP address, or entity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="audit-search-input"
            />
            {searchQuery && (
              <button
                className="search-clear-btn"
                onClick={() => setSearchQuery("")}
                title="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>

          <div className="filter-dropdowns-row">
            {/* User Filter */}
            <div className="filter-control">
              <label>User</label>
              <select
                value={filterUser}
                onChange={(e) => {
                  setFilterUser(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Users</option>
                {availableFilters.users.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>

            {/* Action Filter */}
            <div className="filter-control">
              <label>Action</label>
              <select
                value={filterAction}
                onChange={(e) => {
                  setFilterAction(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Actions</option>
                {availableFilters.actions.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>

            {/* Entity Filter */}
            <div className="filter-control">
              <label>Entity</label>
              <select
                value={filterEntity}
                onChange={(e) => {
                  setFilterEntity(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Entities</option>
                {availableFilters.entities.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
            </div>

            {/* Timeframe Preset */}
            <div className="filter-control">
              <label>Timeframe</label>
              <select
                value={timeframe}
                onChange={(e) => {
                  setTimeframe(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="7days">Last 7 Days</option>
                <option value="30days">Last 30 Days</option>
                <option value="custom">Custom Range</option>
              </select>
            </div>

            {/* Custom Date Pickers */}
            {timeframe === "custom" && (
              <div className="custom-dates-group">
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => {
                    setCustomStartDate(e.target.value);
                    setPage(1);
                  }}
                  className="date-input"
                  title="Start Date"
                />
                <span className="date-separator">to</span>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => {
                    setCustomEndDate(e.target.value);
                    setPage(1);
                  }}
                  className="date-input"
                  title="End Date"
                />
              </div>
            )}

            {/* Reset Filters Button */}
            {hasActiveFilters && (
              <button className="btn-reset-filters" onClick={resetFilters} title="Reset all filters">
                <RotateCcw size={13} />
                <span>Reset</span>
              </button>
            )}

            <div className="filter-result-count">
              Showing <strong>{auditLogs.length}</strong> of <strong>{totalRecords}</strong> records
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        {loading ? (
          <div className="audit-loading-skeleton">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton-card">
                <div className="skeleton-icon" />
                <div className="skeleton-text">
                  <div className="skeleton-line w-40" />
                  <div className="skeleton-line w-80" />
                  <div className="skeleton-line w-20" />
                </div>
              </div>
            ))}
          </div>
        ) : auditLogs.length === 0 ? (
          <div className="audit-empty-state">
            <div className="empty-icon-circle">
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
        ) : (
          <div className="audit-timeline">
            {auditLogs.map((log) => {
              const actConfig = getActionConfig(log.action);
              const isRawExpanded = expandedRows.has(log.id);
              const hasDiff = Boolean(log.old_values || log.new_values);

              return (
                <div key={log.id} className="audit-entry-item">
                  {/* Timeline Visual Node */}
                  <div
                    className="timeline-node"
                    style={{
                      backgroundColor: actConfig.color,
                      boxShadow: `0 0 0 4px ${actConfig.bg}`,
                    }}
                  >
                    {actConfig.icon}
                  </div>
                  <div className="timeline-connector" />

                  {/* Card Content */}
                  <div className="audit-card">
                    {/* Header Row */}
                    <div className="card-top-row">
                      <div className="event-primary-info">
                        <div className="user-badge">
                          <UserIcon size={12} className="badge-user-icon" />
                          <span className="user-name-text">{log.user}</span>
                        </div>

                        <ArrowRight size={12} className="flow-arrow" />

                        <span
                          className="action-pill"
                          style={{
                            backgroundColor: actConfig.bg,
                            color: actConfig.color,
                            borderColor: actConfig.border,
                          }}
                        >
                          {log.action}
                        </span>

                        <span className="entity-tag">{log.entity}</span>
                      </div>

                      <div className="event-timestamp" title={formatFullDateTime(log.timestamp)}>
                        <Clock size={12} style={{ opacity: 0.6 }} />
                        <span>{formatTimestamp(log.timestamp)}</span>
                      </div>
                    </div>

                    {/* Main Description */}
                    <p className="card-description">{log.description || log.details || "No details recorded"}</p>

                    {/* Field-level Before/After Diff Block */}
                    {hasDiff && (
                      <div className="field-diff-container">
                        <div className="field-diff-header">
                          <History size={12} />
                          <span>Field-Level Changes:</span>
                        </div>

                        {typeof log.old_values === "object" &&
                        typeof log.new_values === "object" &&
                        (log.old_values !== null || log.new_values !== null) ? (
                          <div className="diff-fields-grid">
                            {Array.from(
                              new Set([
                                ...Object.keys(log.old_values || {}),
                                ...Object.keys(log.new_values || {}),
                              ]),
                            ).map((key) => {
                              const before = log.old_values?.[key];
                              const after = log.new_values?.[key];
                              return (
                                <div key={key} className="diff-field-row">
                                  <span className="diff-key">{key}:</span>
                                  <span className="diff-before" title={formatDiffVal(before)}>
                                    {formatDiffVal(before)}
                                  </span>
                                  <ArrowRight size={11} className="diff-arrow" />
                                  <span className="diff-after" title={formatDiffVal(after)}>
                                    {formatDiffVal(after)}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="diff-text-view">
                            {log.old_values && (
                              <div>
                                <strong>Before:</strong> {formatDiffVal(log.old_values)}
                              </div>
                            )}
                            {log.new_values && (
                              <div>
                                <strong>After:</strong> {formatDiffVal(log.new_values)}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Expandable Technical Raw JSON */}
                    {isRawExpanded && (
                      <div className="raw-json-viewer">
                        <pre>{JSON.stringify(log, null, 2)}</pre>
                      </div>
                    )}

                    {/* Card Footer Meta */}
                    <div className="card-meta-row">
                      <div className="meta-left-group">
                        <span className="meta-item">
                          <Database size={12} />
                          <span>Ref: #{log.entityId || log.recordId || "N/A"}</span>
                        </span>

                        <span className="meta-item">
                          <Globe size={12} />
                          <span>IP: {log.ipAddress || "Local / System"}</span>
                        </span>

                        <span className="meta-item timestamp-full">
                          <Calendar size={12} />
                          <span>{formatFullDateTime(log.timestamp)}</span>
                        </span>
                      </div>

                      <button
                        className="btn-toggle-raw"
                        onClick={() => toggleRawData(log.id)}
                        title="Toggle Technical Audit JSON"
                      >
                        <Code size={12} />
                        <span>{isRawExpanded ? "Hide Raw" : "Raw JSON"}</span>
                        {isRawExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Bar */}
        {totalRecords > 0 && (
          <div className="audit-pagination-bar">
            <div className="pagination-info">
              Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalRecords} total events)
            </div>

            <div className="pagination-controls">
              <div className="page-size-selector">
                <label>Rows:</label>
                <select
                  value={limit}
                  onChange={(e) => {
                    setLimit(Number(e.target.value));
                    setPage(1);
                  }}
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>

              <div className="pagination-buttons">
                <button
                  className="btn-page-nav"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  title="Previous Page"
                >
                  <ChevronLeft size={16} />
                  <span>Prev</span>
                </button>

                <span className="page-indicator">
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
    </div>
  );
};

export default AuditTrail;
