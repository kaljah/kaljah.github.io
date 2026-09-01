import React, { useState, useEffect } from "react";
import api from "../api";
import {
  Plus,
  Edit2,
  Trash2,
  Eye,
  Download,
  Search,
  RefreshCw,
  Shield,
  User as UserIcon,
  History,
  Clock,
  ArrowRight,
  Filter,
  Activity,
  Database,
  FileText,
  Settings as SettingsIcon,
  Globe,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { useLayout } from "../context/LayoutContext";
import "./AuditTrail.css";

const AuditTrail = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();
  const [loading, setLoading] = useState(true);
  const [auditLogs, setAuditLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [filterUser, setFilterUser] = useState("all");
  const [filterAction, setFilterAction] = useState("all");
  const [filterEntity, setFilterEntity] = useState("all");
  const [availableFilters, setAvailableFilters] = useState({
    users: [],
    actions: [],
    entities: [],
  });

  useEffect(() => {
    fetchFilters();
  }, []);

  useEffect(() => {
    fetchAuditLogs();
  }, [filterUser, filterAction, filterEntity]);

  const fetchFilters = async () => {
    try {
      const res = await api.get("/audit/filters");
      setAvailableFilters(res.data);
    } catch (error) {
      console.error("Failed to fetch audit filters:", error);
    }
  };

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterUser !== "all") params.user = filterUser;
      if (filterAction !== "all") params.action = filterAction;
      if (filterEntity !== "all") params.entity = filterEntity;

      const res = await api.get("/audit", { params });
      setAuditLogs(res.data);
      setFilteredLogs(res.data); // Initial set, though effect handles it too
    } catch (error) {
      console.error("Failed to fetch audit logs:", error);
      toast.error("Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    // Client-side filtering as backup or for rapid UX if fetching all
    // But since we fetch filtered from API, we can just use auditLogs
    // However, let's keep client filtering if the API returns all for now
    // to reduce requests if we want, OR just rely on API.
    // Let's rely on API for heavy lifting, but here we just sync.
    setFilteredLogs(auditLogs);
  };

  // Set top bar content
  useEffect(() => {
    setTopBarLeft(
      <div className="breadcrumbs">
        <History size={16} style={{ color: "#64748b" }} />
        <span>Audit History</span>
        <span className="breadcrumb-separator">/</span>
        <span className="breadcrumb-current">System Logs</span>
      </div>,
    );

    setTopBarRight(
      <div className="top-actions">
        <button
          className="btn-refresh"
          onClick={() => {
            fetchAuditLogs();
            fetchFilters();
            toast.info("Refreshed audit logs");
          }}
        >
          <RefreshCw size={14} />
          Refresh Logs
        </button>
        <div className="user-profile-sm">
          <div className="user-avatar-sm">
            <UserIcon size={14} />
          </div>
          <span className="user-name-sm">{user?.fullName || "Admin"}</span>
        </div>
      </div>,
    );

    return () => {
      setTopBarLeft(null);
      setTopBarRight(null);
    };
  }, [user, setTopBarLeft, setTopBarRight, toast]);

  const getActionIcon = (action) => {
    const iconSize = 20;
    const icons = {
      CREATE: <Plus size={iconSize} />,
      UPDATE: <Edit2 size={iconSize} />,
      DELETE: <Trash2 size={iconSize} />,
      VIEW: <Eye size={iconSize} />,
      EXPORT: <Download size={iconSize} />,
    };
    return icons[action] || <Activity size={iconSize} />;
  };

  const getActionColor = (action) => {
    const colors = {
      CREATE: "#10b981",
      UPDATE: "#3b82f6",
      DELETE: "#ef4444",
      VIEW: "#6b7280",
      EXPORT: "#8b5cf6",
    };
    return colors[action] || "#6b7280";
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  // const uniqueUsers = [...new Set(auditLogs.map(log => log.user))];
  // const uniqueActions = [...new Set(auditLogs.map(log => log.action))];
  // const uniqueEntities = [...new Set(auditLogs.map(log => log.entity))];

  if (loading && auditLogs.length === 0) {
    return <LoadingSpinner fullScreen message="Loading audit trail..." />;
  }

  return (
    <div className="audit-trail">
      <div className="audit-container">
        <div
          style={{
            marginBottom: "30px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h2 className="section-title">Audit Log History</h2>
            <p style={{ color: "var(--text-secondary)" }}>
              Detailed record of compliance activity and system changes
            </p>
          </div>
          <button className="btn-refresh" onClick={fetchAuditLogs}>
            <RefreshCw size={16} />
            Refresh Logs
          </button>
        </div>

        {/* Filters */}
        <div className="filters-bar">
          <div className="filter-group">
            <label>User:</label>
            <select
              value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}
            >
              <option value="all">All Users</option>
              {availableFilters.users.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Action:</label>
            <select
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
            >
              <option value="all">All Actions</option>
              {availableFilters.actions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Entity:</label>
            <select
              value={filterEntity}
              onChange={(e) => setFilterEntity(e.target.value)}
            >
              <option value="all">All Entities</option>
              {availableFilters.entities.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-stats">
            Showing {filteredLogs.length} of {auditLogs.length} records
          </div>
        </div>

        {/* Audit Logs Timeline */}
        <div className="audit-timeline">
          {filteredLogs.map((log) => (
            <div key={log.id} className="audit-entry">
              <div
                className="entry-icon"
                style={{ background: getActionColor(log.action) }}
              >
                {getActionIcon(log.action)}
              </div>
              <div className="entry-line" />
              <div className="entry-content">
                <div className="entry-header">
                  <div className="entry-main">
                    <span className="entry-user">
                      <UserIcon
                        size={12}
                        style={{ marginRight: "6px", opacity: 0.5 }}
                      />
                      {log.user}
                    </span>
                    <ArrowRight size={12} style={{ opacity: 0.3 }} />
                    <span
                      className="entry-action"
                      style={{
                        background: `${getActionColor(log.action)}15`,
                        color: getActionColor(log.action),
                        border: `1px solid ${getActionColor(log.action)}30`,
                      }}
                    >
                      {log.action}
                    </span>
                    <span className="entry-entity">{log.entity}</span>
                  </div>
                  <span className="entry-time">
                    <Clock
                      size={12}
                      style={{ marginRight: "6px", opacity: 0.5 }}
                    />
                    {formatTimestamp(log.timestamp)}
                  </span>
                </div>
                <p className="entry-description">{log.description || log.details}</p>
                {/* Field-level Before/After Changes */}
                {(log.old_values || log.new_values) && (
                  <div style={{ marginTop: "10px", marginBottom: "10px", background: "rgba(241,245,249,0.7)", borderRadius: "6px", padding: "8px 12px", border: "1px solid #e2e8f0" }}>
                    <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                      Field Changes:
                    </div>
                    {typeof log.old_values === "object" && typeof log.new_values === "object" ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        {Array.from(new Set([...Object.keys(log.old_values || {}), ...Object.keys(log.new_values || {})])).map((k) => (
                          <div key={k} style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontWeight: "600", color: "#334155" }}>{k}:</span>
                            <span style={{ color: "#ef4444", textDecoration: "line-through" }}>{String(log.old_values?.[k] ?? "—")}</span>
                            <ArrowRight size={10} style={{ color: "#94a3b8" }} />
                            <span style={{ color: "#10b981", fontWeight: "600" }}>{String(log.new_values?.[k] ?? "—")}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        {log.old_values && <div><b>Before:</b> {typeof log.old_values === "string" ? log.old_values : JSON.stringify(log.old_values)}</div>}
                        {log.new_values && <div><b>After:</b> {typeof log.new_values === "string" ? log.new_values : JSON.stringify(log.new_values)}</div>}
                      </div>
                    )}
                  </div>
                )}
                <div className="entry-meta">
                  <span>
                    <Database size={12} />
                    Ref: #{log.entityId}
                  </span>
                  <span>
                    <Globe size={12} />
                    IP: {log.ipAddress}
                  </span>
                  <span>
                    <Clock size={12} />
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredLogs.length === 0 && (
          <div className="empty-state">
            <p>No audit logs match the current filters</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditTrail;
