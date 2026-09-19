import React, { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle,
  ShieldAlert,
  Settings2,
  FileText,
  Info,
  Bell,
  Trash2,
  CheckCheck,
  X,
  Zap,
} from "lucide-react";
import api from "../api";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";

// ─── Type → icon + colour map ─────────────────────────────────────────────────
const TYPE_CONFIG = {
  critical: {
    Icon: AlertTriangle,
    color: "#ef4444",
    bg: "rgba(239,68,68,0.12)",
  },
  error: { Icon: AlertTriangle, color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  warning: {
    Icon: AlertTriangle,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
  },
  SECURITY: {
    Icon: ShieldAlert,
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.12)",
  },
  system: { Icon: Settings2, color: "#8b5cf6", bg: "rgba(139,92,246,0.12)" },
  audit: { Icon: FileText, color: "#10b981", bg: "rgba(16,185,129,0.12)" },
  goal: { Icon: Zap, color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
  info: { Icon: Info, color: "#3b82f6", bg: "rgba(59,130,246,0.12)" },
};

const getTypeConfig = (type) =>
  TYPE_CONFIG[type] ?? {
    Icon: Info,
    color: "#3b82f6",
    bg: "rgba(59,130,246,0.12)",
  };

// ─── Relative time helper ─────────────────────────────────────────────────────
const relativeTime = (isoStr) => {
  const diff = (Date.now() - new Date(isoStr)) / 1000;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(isoStr).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
};

// ─── Bell button with numeric badge ──────────────────────────────────────────
const BellButton = ({ count, onClick }) => (
  <button
    onClick={onClick}
    title="Notifications"
    style={{
      position: "relative",
      background: "none",
      border: "none",
      color: "var(--text-secondary)",
      cursor: "pointer",
      padding: 8,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 8,
      transition: "color 0.2s, background 0.2s",
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.background =
        "var(--bg-hover, rgba(255,255,255,0.06))";
      e.currentTarget.style.color = "var(--text-primary)";
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.background = "none";
      e.currentTarget.style.color = "var(--text-secondary)";
    }}
  >
    <Bell size={20} strokeWidth={1.75} />
    {count > 0 && (
      <span
        style={{
          position: "absolute",
          top: 3,
          right: 3,
          minWidth: 16,
          height: 16,
          background: "#ef4444",
          borderRadius: 8,
          border: "1.5px solid var(--bg-card, #ffffff)",
          fontSize: "0.6rem",
          fontWeight: 700,
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 3px",
          lineHeight: 1,
          letterSpacing: "-0.02em",
        }}
      >
        {count > 99 ? "99+" : count}
      </span>
    )}
  </button>
);

// ─── Single notification row ──────────────────────────────────────────────────
const NotifRow = ({ n, onMarkRead, onDelete }) => {
  const { Icon, color, bg } = getTypeConfig(n.type);
  return (
    <div
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border-light, #f1f5f9)",
        background: n.is_read ? "transparent" : "rgba(255, 102, 0, 0.04)",
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        transition: "background 0.15s",
        position: "relative",
      }}
    >
      {/* Type icon */}
      <div
        style={{
          flexShrink: 0,
          width: 32,
          height: 32,
          borderRadius: 8,
          background: bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginTop: 1,
        }}
      >
        <Icon size={15} color={color} strokeWidth={2} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 2,
          }}
        >
          {!n.is_read && (
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#3b82f6",
                flexShrink: 0,
              }}
            />
          )}
          <span
            style={{
              fontWeight: 600,
              fontSize: "0.82rem",
              color: "var(--text-primary, #0f172a)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {n.title}
          </span>
        </div>
        <p
          style={{
            margin: 0,
            fontSize: "0.78rem",
            color: "var(--text-secondary, #475569)",
            lineHeight: 1.45,
            wordBreak: "break-word",
            opacity: n.is_read ? 0.75 : 1,
          }}
        >
          {n.message}
        </p>
        <span
          style={{
            display: "block",
            marginTop: 5,
            fontSize: "0.7rem",
            color: "var(--text-muted, #94a3b8)",
          }}
        >
          {relativeTime(n.time)}
        </span>
      </div>

      {/* Action buttons */}
      <div
        style={{ display: "flex", gap: 2, flexShrink: 0, alignItems: "center" }}
      >
        {!n.is_read && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMarkRead(n.id);
            }}
            title="Mark as read"
            style={iconBtnStyle}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "rgba(59,130,246,0.15)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "transparent")
            }
          >
            <CheckCheck size={13} color="#3b82f6" strokeWidth={2} />
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(n.id);
          }}
          title="Delete"
          style={iconBtnStyle}
          onMouseEnter={(e) =>
            (e.currentTarget.style.background = "rgba(239,68,68,0.12)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.background = "transparent")
          }
        >
          <Trash2 size={13} color="#ef4444" strokeWidth={2} />
        </button>
      </div>
    </div>
  );
};

const iconBtnStyle = {
  background: "transparent",
  border: "none",
  cursor: "pointer",
  padding: 5,
  borderRadius: 6,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  transition: "background 0.15s",
};

// ─── Main component ───────────────────────────────────────────────────────────
const NotificationCenter = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const dropdownRef = useRef(null);
  const panelRef = useRef(null);
  const [panelPos, setPanelPos] = useState({ top: 64, right: 24 });
  const lastIdRef = useRef(0);
  const esRef = useRef(null);
  const retryDelayRef = useRef(1000);
  const toast = useToast();

  // ── Track position for fixed portal ──────────────────────────────────
  const updatePosition = useCallback(() => {
    if (dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      setPanelPos({
        top: Math.round(rect.bottom + 8),
        right: Math.max(16, Math.round(window.innerWidth - rect.right)),
      });
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      updatePosition();
      window.addEventListener("resize", updatePosition);
      window.addEventListener("scroll", updatePosition, true);
      const handleKeyDown = (e) => {
        if (e.key === "Escape") setIsOpen(false);
      };
      document.addEventListener("keydown", handleKeyDown);
      return () => {
        window.removeEventListener("resize", updatePosition);
        window.removeEventListener("scroll", updatePosition, true);
        document.removeEventListener("keydown", handleKeyDown);
      };
    }
  }, [isOpen, updatePosition]);

  // ── Fetch history ─────────────────────────────────────────────────────
  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    try {
      const res = await api.get("/notifications");
      if (res.status === 200) {
        const data = res.data;
        setNotifications(data);
        setUnreadCount(data.filter((n) => !n.is_read).length);
        if (data.length > 0) {
          lastIdRef.current = Math.max(...data.map((n) => n.id));
        }
      }
    } catch (err) {
      console.error("Failed to fetch notifications", err);
    }
  }, [user]);

  // ── SSE connection ────────────────────────────────────────────────────
  const connectSSE = useCallback(() => {
    if (!user) return;
    if (esRef.current) esRef.current.close();

    const base = import.meta.env.VITE_API_URL || "/api";
    const url = `${base}/notifications/stream?last_id=${lastIdRef.current}`;
    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    es.onopen = () => {
      retryDelayRef.current = 1000;
    };

    es.onmessage = (event) => {
      try {
        const notif = JSON.parse(event.data);
        if (notif.id > lastIdRef.current) lastIdRef.current = notif.id;
        setNotifications((prev) => [notif, ...prev]);
        setUnreadCount((prev) => prev + 1);
        toast.info(`${notif.title}: ${notif.message}`);
      } catch (err) {
        console.error("SSE parse error", err);
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      if (!user) return;
      const delay = retryDelayRef.current;
      retryDelayRef.current = Math.min(delay * 2, 30_000);
      setTimeout(() => {
        if (user) connectSSE();
      }, delay);
    };
  }, [user, toast]);

  // ── Mount / unmount ───────────────────────────────────────────────────
  useEffect(() => {
    if (!user) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    fetchNotifications().then(() => connectSSE());
    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [user, fetchNotifications, connectSSE]);

  // ── Click-outside ─────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && dropdownRef.current.contains(e.target)) return;
      if (panelRef.current && panelRef.current.contains(e.target)) return;
      setIsOpen(false);
    };
    if (isOpen) {
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }
  }, [isOpen]);

  // ── Mark single read ──────────────────────────────────────────────────
  const handleMarkRead = async (id) => {
    try {
      await api.put(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark read", err);
    }
  };

  // ── Mark all read ─────────────────────────────────────────────────────
  const handleMarkAllRead = async () => {
    try {
      await api.post("/notifications/dismiss-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast.success("All notifications marked as read");
    } catch (err) {
      console.error("Failed to mark all read", err);
    }
  };

  // ── Delete single ─────────────────────────────────────────────────────
  const handleDelete = async (id) => {
    try {
      await api.delete(`/notifications/${id}`);
      const removed = notifications.find((n) => n.id === id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (removed && !removed.is_read)
        setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to delete notification", err);
      toast.error("Could not delete notification");
    }
  };

  // ── Delete all ────────────────────────────────────────────────────────
  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      await api.delete("/notifications/all");
      setNotifications([]);
      setUnreadCount(0);
      toast.success("All notifications deleted");
    } catch (err) {
      console.error("Failed to delete all notifications", err);
      toast.error("Could not delete notifications");
    } finally {
      setIsDeleting(false);
    }
  };

  const hasUnread = unreadCount > 0;

  // ─── Render ────────────────────────────────────────────────────────────
  const trayPanel = isOpen && (
    <div
      ref={panelRef}
      className="notification-tray-panel"
      style={{
        position: "fixed",
        top: panelPos.top,
        right: panelPos.right,
        width: 380,
        maxWidth: "calc(100vw - 32px)",
        maxHeight: "calc(100vh - 90px)",
        background: "var(--bg-card-elevated, #ffffff)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid var(--border-color, rgba(226, 232, 240, 0.9))",
        borderRadius: 16,
        boxShadow:
          "0 25px 50px -12px rgba(15, 23, 42, 0.25), 0 0 0 1px rgba(15, 23, 42, 0.06)",
        zIndex: 999999,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        animation: "notif-dropdown-in 0.15s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          padding: "14px 18px 12px",
          borderBottom: "1px solid var(--border-color, rgba(226, 232, 240, 0.8))",
          background: "rgba(255, 255, 255, 0.7)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              fontWeight: 700,
              fontSize: "0.92rem",
              color: "var(--text-primary, #0f172a)",
              letterSpacing: "-0.01em",
            }}
          >
            Notifications
          </span>
          {notifications.length > 0 && (
            <span
              style={{
                fontSize: "0.72rem",
                fontWeight: 700,
                color: "var(--text-secondary, #64748b)",
                background: "var(--bg-hover, #f1f5f9)",
                borderRadius: 999,
                padding: "2px 8px",
              }}
            >
              {notifications.length}
            </span>
          )}
          {/* Live indicator */}
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: "0.65rem",
              fontWeight: 700,
              color: "#059669",
              background: "rgba(16,185,129,0.1)",
              border: "1px solid rgba(16,185,129,0.25)",
              borderRadius: 20,
              padding: "2px 8px",
              letterSpacing: "0.03em",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#10b981",
                animation: "pulse-dot 2s ease-in-out infinite",
              }}
            />
            LIVE
          </span>
        </div>

        {/* Header actions */}
        <div style={{ display: "flex", gap: 4 }}>
          {hasUnread && (
            <button
              onClick={handleMarkAllRead}
              title="Mark all as read"
              style={{
                ...headerActionBtn,
                color: "#2563eb",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "rgba(37, 99, 235, 0.08)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <CheckCheck size={13} strokeWidth={2} />
              <span>Mark read</span>
            </button>
          )}
          {notifications.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={isDeleting}
              title="Delete all notifications"
              style={{
                ...headerActionBtn,
                color: "#ef4444",
                opacity: isDeleting ? 0.5 : 1,
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "rgba(239,68,68,0.08)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <Trash2 size={13} strokeWidth={2} />
              <span>Clear all</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Notification list ── */}
      <div style={{ maxHeight: 420, overflowY: "auto" }}>
        {notifications.length === 0 ? (
          <div
            style={{
              padding: "40px 24px",
              textAlign: "center",
              color: "var(--text-secondary, #64748b)",
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                background: "var(--bg-hover, #f8fafc)",
                border: "1px solid var(--border-color, #e2e8f0)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 12px",
              }}
            >
              <Bell
                size={22}
                color="var(--text-muted, #94a3b8)"
                strokeWidth={1.75}
              />
            </div>
            <p style={{ margin: 0, fontSize: "0.88rem", fontWeight: 700, color: "var(--text-primary, #0f172a)" }}>
              No notifications
            </p>
            <p
              style={{
                margin: "4px 0 0",
                fontSize: "0.78rem",
                color: "var(--text-secondary, #64748b)",
              }}
            >
              You're all caught up
            </p>
          </div>
        ) : (
          notifications.map((n) => (
            <NotifRow
              key={n.id}
              n={n}
              onMarkRead={handleMarkRead}
              onDelete={handleDelete}
            />
          ))
        )}
      </div>

      {/* ── Footer ── */}
      {notifications.length > 0 && (
        <div
          style={{
            padding: "9px 18px",
            borderTop: "1px solid var(--border-color, #e2e8f0)",
            background: "var(--bg-hover, #f8fafc)",
            fontSize: "0.74rem",
            color: "var(--text-secondary, #64748b)",
            fontWeight: 500,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontWeight: 600, color: hasUnread ? "#ea580c" : "inherit" }}>
            {unreadCount} unread
          </span>
          <span>Showing {notifications.length} notifications</span>
        </div>
      )}
    </div>
  );

  return (
    <div ref={dropdownRef} style={{ position: "relative" }}>
      <BellButton count={unreadCount} onClick={() => setIsOpen((o) => !o)} />

      {isOpen && typeof document !== "undefined" && createPortal(trayPanel, document.body)}

      <style>{`
        @keyframes notif-dropdown-in {
            from { opacity: 0; transform: translateY(-6px) scale(0.98); }
            to   { opacity: 1; transform: translateY(0)     scale(1);    }
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50%       { opacity: 0.4; transform: scale(0.75); }
        }
      `}</style>
    </div>
  );
};

const headerActionBtn = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  background: "transparent",
  border: "none",
  cursor: "pointer",
  padding: "4px 8px",
  borderRadius: 6,
  fontSize: "0.72rem",
  fontWeight: 600,
  transition: "background 0.15s",
  letterSpacing: "0.01em",
};

export default NotificationCenter;
