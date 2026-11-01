import React, { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ShieldAlert,
  Settings2,
  FileText,
  Info,
  Bell,
  Trash2,
  CheckCheck,
  Zap,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import api from "../api";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { cn } from "../ui/cn";
import { t } from "../i18n";

export interface SystemAlertItem {
  id: string;
  category: "anomalies" | "scope3" | "production" | "discrepancy" | "pending_sla" | "health_drop";
  title: string;
  message: string;
  severity: "critical" | "warning" | "info";
  path: string;
  actionText: string;
}

export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  time: string;
}

interface TypeConfig {
  Icon: LucideIcon;
  color: string;
  bg: string;
}

// ─── Type → icon + colour map ─────────────────────────────────────────────────
const TYPE_CONFIG: Record<string, TypeConfig> = {
  critical: {
    Icon: AlertTriangle,
    color: "var(--color-red-500)",
    bg: "rgba(239,68,68,0.12)",
  },
  error: { Icon: AlertTriangle, color: "var(--color-red-500)", bg: "rgba(239,68,68,0.12)" },
  warning: {
    Icon: AlertTriangle,
    color: "var(--color-amber-500)",
    bg: "rgba(245,158,11,0.12)",
  },
  SECURITY: {
    Icon: ShieldAlert,
    color: "var(--color-amber-500)",
    bg: "rgba(245,158,11,0.12)",
  },
  system: { Icon: Settings2, color: "var(--color-violet-500)", bg: "rgba(139,92,246,0.12)" },
  audit: { Icon: FileText, color: "var(--color-green-500)", bg: "rgba(16,185,129,0.12)" },
  goal: { Icon: Zap, color: "var(--color-blue-500)", bg: "rgba(59,130,246,0.12)" },
  info: { Icon: Info, color: "var(--color-blue-500)", bg: "rgba(59,130,246,0.12)" },
};

const getTypeConfig = (type: string): TypeConfig =>
  TYPE_CONFIG[type] ?? {
    Icon: Info,
    color: "var(--color-blue-500)",
    bg: "rgba(59,130,246,0.12)",
  };

// ─── Relative time helper ─────────────────────────────────────────────────────
const relativeTime = (isoStr: string): string => {
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60) return t("Just now");
  if (diff < 3600) return t("{{count}}m ago", { count: Math.floor(diff / 60) });
  if (diff < 86400) return t("{{count}}h ago", { count: Math.floor(diff / 3600) });
  return new Date(isoStr).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
};

interface BellButtonProps {
  count: number;
  onClick: () => void;
}

// ─── Bell button with numeric badge ──────────────────────────────────────────
const BellButton: React.FC<BellButtonProps> = ({ count, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    title={t("Notifications")}
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
        className="[position:absolute]! [top:3px]! [right:3px]! min-w-[16px]! h-[16px]! bg-[color:var(--color-red-500)]! rounded-[8px]! [border:1.5px_solid_var(--bg-card,_var(--color-white))]! text-[length:0.6rem]! font-bold! text-[color:var(--color-white)]! flex! items-center! justify-center! p-[0_3px]! leading-[1]! [letter-spacing:-0.02em]!"
      >
        {count > 99 ? "99+" : count}
      </span>
    )}
  </button>
);

interface AlertRowProps {
  alert: SystemAlertItem;
  onNavigate: (path: string) => void;
}

const AlertRow: React.FC<AlertRowProps> = ({ alert, onNavigate }) => {
  const isCrit = alert.severity === "critical";
  const isWarn = alert.severity === "warning";
  const iconColor = isCrit ? "var(--color-red-500)" : isWarn ? "var(--color-amber-500)" : "var(--color-blue-500)";
  const iconBg = isCrit ? "rgba(239, 68, 68, 0.12)" : isWarn ? "rgba(245, 158, 11, 0.12)" : "rgba(59, 130, 246, 0.12)";

  return (
    <div
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border-light, var(--color-ink-100))",
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        transition: "background 0.15s",
      }}
    >
      <div
        style={{
          flexShrink: 0,
          width: 32,
          height: 32,
          borderRadius: 8,
          background: iconBg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginTop: 1,
        }}
      >
        <AlertTriangle size={15} color={iconColor} strokeWidth={2} />
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="m-0 text-sm font-semibold text-text">{alert.title}</h4>
        <p className="m-0 mt-1 text-xs text-text-secondary leading-normal">{alert.message}</p>
        <button
          type="button"
          onClick={() => onNavigate(alert.path)}
          className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-ink-100 hover:bg-ink-200 px-2.5 py-1 text-xs font-semibold text-text transition-colors border border-border cursor-pointer"
        >
          <span>{alert.actionText}</span>
          <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
};

interface NotifRowProps {
  n: NotificationItem;
  onMarkRead: (id: number) => void;
  onDelete: (id: number) => void;
}

// ─── Single notification row ──────────────────────────────────────────────────
const NotifRow: React.FC<NotifRowProps> = ({ n, onMarkRead, onDelete }) => {
  const { Icon, color, bg } = getTypeConfig(n.type);
  return (
    <div
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border-light, var(--color-ink-100))",
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
      <div className="flex-1! min-w-0!">
        <div
          className="flex! items-center! gap-[6px]! mb-[2px]!"
        >
          {!n.is_read && (
            <span
              className="w-[6px]! h-[6px]! [border-radius:50%]! bg-[color:var(--color-blue-500)]! shrink-0!"
            />
          )}
          <span
            className="font-semibold! text-[length:0.82rem]! text-[color:var(--text-primary,_var(--color-ink-900))]! whitespace-nowrap! overflow-hidden! [text-overflow:ellipsis]!"
          >
            {n.title}
          </span>
        </div>
        <p
          className={`[margin:0]! [font-size:0.78rem]! [color:var(--text-secondary,_var(--color-ink-600))]! [line-height:1.45]! [word-break:break-word]! ${n.is_read ? "[opacity:0.75]!" : "[opacity:1]!"}`}
        >
          {n.message}
        </p>
        <span
          className="block! mt-[5px]! text-[length:0.7rem]! text-[color:var(--text-muted,_var(--color-ink-400))]!"
        >
          {relativeTime(n.time)}
        </span>
      </div>

      {/* Action buttons */}
      <div
        className="flex! gap-[2px]! shrink-0! items-center!"
      >
        {!n.is_read && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onMarkRead(n.id);
            }}
            title={t("Mark as read")}
            style={iconBtnStyle}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "rgba(59,130,246,0.15)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "transparent")
            }
          >
            <CheckCheck size={13} color="var(--color-blue-500)" strokeWidth={2} />
          </button>
        )}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(n.id);
          }}
          title={t("Delete")}
          style={iconBtnStyle}
          onMouseEnter={(e) =>
            (e.currentTarget.style.background = "rgba(239,68,68,0.12)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.background = "transparent")
          }
        >
          <Trash2 size={13} color="var(--color-red-500)" strokeWidth={2} />
        </button>
      </div>
    </div>
  );
};

const iconBtnStyle: React.CSSProperties = {
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
const TOAST_BURST = 3;
const POLL_INTERVAL_MS = 30_000;

const NotificationCenter: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<SystemAlertItem[]>([]);
  const [activeTab, setActiveTab] = useState<"alerts" | "notifications">("alerts");
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [panelPos, setPanelPos] = useState<{ top: number; right: number }>({ top: 64, right: 24 });
  const lastIdRef = useRef<number>(0);
  const toast = useToast();
  // Polling and the history load depend on WHO is signed in, not on the identity of the
  // user / toast objects: those change on re-renders, and every change re-ran the effect
  // (a new history request several times a second).
  const userId = user?.id ?? null;
  const toastRef = useRef(toast);
  toastRef.current = toast;
  // bursts are coalesced: more than TOAST_BURST notifications within 500 ms give one toast
  const pendingToastsRef = useRef<NotificationItem[]>([]);
  const toastTimerRef = useRef<any>(null);
  const queueToast = useCallback((notif: NotificationItem) => {
    pendingToastsRef.current.push(notif);
    if (toastTimerRef.current) return;
    toastTimerRef.current = setTimeout(() => {
      const batch = pendingToastsRef.current;
      pendingToastsRef.current = [];
      toastTimerRef.current = null;
      if (batch.length > TOAST_BURST) {
        toastRef.current.info(`${batch.length} new notifications`);
      } else {
        batch.forEach((n) => toastRef.current.info(`${n.title}: ${n.message}`));
      }
    }, 500);
  }, []);
  useEffect(() => () => clearTimeout(toastTimerRef.current), []);
  const activeRef = useRef<boolean>(false);

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
      const handleKeyDown = (e: KeyboardEvent) => {
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

  // ── Polling (audit O-02) ──────────────────────────────────────────────
  // Notifications are polled instead of streamed: a Server-Sent Events stream held one server
  // worker thread per open tab, so a handful of open tabs stopped the API answering.
  const fetchNotifications = useCallback(
    async ({ announce = false }: { announce?: boolean } = {}) => {
      if (!userId) return;
      try {
        const res = await api.get<NotificationItem[]>("/notifications");
        if (res.status !== 200 || !activeRef.current) return;
        const data = res.data;
        if (announce) {
          data
            .filter((n) => n.id > lastIdRef.current && !n.is_read)
            .reverse()
            .forEach(queueToast);
        }
        setNotifications(data);
        setUnreadCount(data.filter((n) => !n.is_read).length);
        if (data.length > 0) {
          lastIdRef.current = Math.max(lastIdRef.current, ...data.map((n) => n.id));
        }
      } catch (err) {
        console.error("Failed to fetch notifications", err);
      }
    },
    [userId, queueToast],
  );

  // ── System Alerts aggregation (B6) ──────────────────────────────────
  const fetchSystemAlerts = useCallback(async () => {
    if (!userId) {
      setSystemAlerts([]);
      return;
    }
    const alerts: SystemAlertItem[] = [];
    try {
      // 1. Pending records in review queue
      const pendingRes = await api.get("/emissions/pending").catch(() => null);
      const totalPending = pendingRes?.data?.total_pending || 0;
      if (totalPending > 0) {
        alerts.push({
          id: "pending-items",
          category: "pending_sla",
          title: t("Pending Review Queue ({{count}} records)", { count: totalPending }),
          message: t("Unreviewed records await dual-control maker-checker validation before inclusion in totals."),
          severity: totalPending > 10 ? "critical" : "warning",
          path: "/manage-data?tab=pending",
          actionText: t("Review Queue"),
        });
      }

      // 2. QA/QC Anomalies & Data Health Drop
      if (user?.role && ["admin", "superuser"].includes(user.role)) {
        const qaRes = await api.get("/qa/dashboard").catch(() => null);
        if (qaRes?.data) {
          const flagged = qaRes.data.total_flagged_count || qaRes.data.flagged_records?.length || 0;
          if (flagged > 0) {
            alerts.push({
              id: "qa-flagged",
              category: "anomalies",
              title: t("QA/QC Flagged Anomalies ({{count}})", { count: flagged }),
              message: t("Statistical anomalies or outlier emissions detected requiring review."),
              severity: "critical",
              path: "/qa-dashboard",
              actionText: t("Open QA/QC Queue"),
            });
          }
          const health = qaRes.data.diagnostics?.health_score;
          if (health != null && health < 90) {
            alerts.push({
              id: "health-drop",
              category: "health_drop",
              title: t("Data Health Score Below Target ({{score}}%)", { score: health }),
              message: t("Data completeness or validation coverage has dropped below the 90% assurance threshold."),
              severity: "warning",
              path: "/qa-dashboard",
              actionText: t("Inspect Diagnostics"),
            });
          }
        }
      }

      // 3. OGMP 2.0 Level 4/5 Discrepancies
      const ogmpRes = await api.get("/ogmp/surveys").catch(() => null);
      const surveys = Array.isArray(ogmpRes?.data) ? ogmpRes.data : ogmpRes?.data?.surveys || [];
      const discrepancySurveys = surveys.filter((s: any) =>
        s.reconciliation_status === "discrepancy" ||
        (s.relative_difference_pct != null && Math.abs(s.relative_difference_pct) > 20)
      );
      if (discrepancySurveys.length > 0) {
        alerts.push({
          id: "ogmp-discrepancy",
          category: "discrepancy",
          title: t("OGMP 2.0 Measurement Discrepancies ({{count}})", { count: discrepancySurveys.length }),
          message: t("Top-down site/source measurements show significant discrepancy with bottom-up inventory."),
          severity: "warning",
          path: "/manage-data?tab=ogmp",
          actionText: t("Reconcile Surveys"),
        });
      }

      setSystemAlerts(alerts);
    } catch (err) {
      console.debug("Alerts load skipped", err);
    }
  }, [userId, user?.role]);

  // ── Mount / unmount ───────────────────────────────────────────────────
  useEffect(() => {
    if (!userId) {
      setNotifications([]);
      setSystemAlerts([]);
      setUnreadCount(0);
      return;
    }

    activeRef.current = true;
    lastIdRef.current = 0;
    fetchNotifications();
    fetchSystemAlerts();
    const poll = () => {
      if (document.visibilityState === "visible") {
        fetchNotifications({ announce: true });
        fetchSystemAlerts();
      }
    };
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    document.addEventListener("visibilitychange", poll);
    return () => {
      activeRef.current = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", poll);
    };
  }, [userId, fetchNotifications, fetchSystemAlerts]);

  // ── Click-outside ─────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && dropdownRef.current.contains(e.target as Node)) return;
      if (panelRef.current && panelRef.current.contains(e.target as Node)) return;
      setIsOpen(false);
    };
    if (isOpen) {
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }
  }, [isOpen]);

  // ── Mark single read ──────────────────────────────────────────────────
  const handleMarkRead = async (id: number) => {
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
      toast.success(t("All notifications marked as read"));
    } catch (err) {
      console.error("Failed to mark all read", err);
    }
  };

  // ── Delete single ─────────────────────────────────────────────────────
  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/notifications/${id}`);
      const removed = notifications.find((n) => n.id === id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (removed && !removed.is_read)
        setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to delete notification", err);
      toast.error(t("Could not delete notification"));
    }
  };

  // ── Delete all ────────────────────────────────────────────────────────
  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      await api.delete("/notifications/all");
      setNotifications([]);
      setUnreadCount(0);
      toast.success(t("All notifications deleted"));
    } catch (err) {
      console.error("Failed to delete all notifications", err);
      toast.error(t("Could not delete notifications"));
    } finally {
      setIsDeleting(false);
    }
  };

  const hasUnread = unreadCount > 0;

  // ─── Render ────────────────────────────────────────────────────────────
  const trayPanel = isOpen && (
    <div
      ref={panelRef}
      className="notification-tray-panel z-[999999] pointer-events-auto"
      style={{
        position: "fixed",
        top: panelPos.top,
        right: panelPos.right,
        width: 380,
        maxWidth: "calc(100vw - 32px)",
        maxHeight: "calc(100vh - 90px)",
        background: "var(--bg-card-elevated, var(--color-white))",
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
        className="p-[14px_18px_12px]! [border-bottom:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]! bg-[color:rgba(255,_255,_255,_0.7)]! flex! justify-between! items-center! gap-[8px]!"
      >
        <div className="flex! items-center! gap-[10px]!">
          <span
            className="font-bold! text-[length:0.92rem]! text-[color:var(--text-primary,_var(--color-ink-900))]! [letter-spacing:-0.01em]!"
          >
            {t("Notifications")}
          </span>
          {notifications.length > 0 && (
            <span
              className="text-[length:0.72rem]! font-bold! text-[color:var(--text-secondary,_var(--color-ink-500))]! bg-[color:var(--bg-hover,_var(--color-ink-100))]! rounded-[999px]! p-[2px_8px]!"
            >
              {notifications.length}
            </span>
          )}
          {/* Live indicator */}
          <span
            className="inline-flex! items-center! gap-[4px]! text-[length:0.65rem]! font-bold! text-[color:var(--color-green-600)]! bg-[color:rgba(16,185,129,0.1)]! [border:1px_solid_rgba(16,185,129,0.25)]! rounded-[20px]! p-[2px_8px]! [letter-spacing:0.03em]!"
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--color-green-500)",
                animation: "pulse-dot 2s ease-in-out infinite",
              }}
            />
            LIVE
          </span>
        </div>

        {/* Header actions */}
        <div className="flex! gap-[4px]!">
          {hasUnread && (
            <button
              type="button"
              onClick={handleMarkAllRead}
              title={t("Mark all as read")}
              style={{
                ...headerActionBtn,
                color: "var(--color-blue-600)",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "rgba(37, 99, 235, 0.08)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <CheckCheck size={13} strokeWidth={2} />
              <span>{t("Mark read")}</span>
            </button>
          )}
          {notifications.length > 0 && (
            <button
              type="button"
              onClick={handleDeleteAll}
              disabled={isDeleting}
              title={t("Delete all notifications")}
              style={{
                ...headerActionBtn,
                color: "var(--color-red-700)",
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
              <span>{t("Clear all")}</span>
            </button>
          )}
        </div>
      </div>

      {/* Switcher: System Alerts vs Activity Log (B6) */}
      <div className="flex border-b border-border bg-ink-50/60 p-1.5 gap-1.5">
        <button
          type="button"
          onClick={() => setActiveTab("alerts")}
          className={cn(
            "flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-semibold cursor-pointer border transition-colors",
            activeTab === "alerts"
              ? "bg-surface text-text shadow-xs border-border"
              : "bg-transparent text-text-secondary border-transparent hover:text-text"
          )}
        >
          <AlertTriangle className="size-3.5 text-amber-500" />
          <span>{t("System Alerts")}</span>
          {systemAlerts.length > 0 && (
            <span className="rounded-full bg-amber-100 text-amber-800 px-1.5 py-0.2 text-[0.65rem] font-bold">
              {systemAlerts.length}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("notifications")}
          className={cn(
            "flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-semibold cursor-pointer border transition-colors",
            activeTab === "notifications"
              ? "bg-surface text-text shadow-xs border-border"
              : "bg-transparent text-text-secondary border-transparent hover:text-text"
          )}
        >
          <Bell className="size-3.5 text-blue-500" />
          <span>{t("Activity")}</span>
          {unreadCount > 0 && (
            <span className="rounded-full bg-blue-100 text-blue-800 px-1.5 py-0.2 text-[0.65rem] font-bold">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* ── Content list ── */}
      <div className="max-h-[420px] overflow-y-auto">
        {activeTab === "alerts" ? (
          systemAlerts.length === 0 ? (
            <div className="p-8 text-center text-text-secondary">
              <div className="w-12 h-12 rounded-2xl bg-green-50 border border-green-200 flex items-center justify-center mx-auto mb-3">
                <CheckCheck size={22} className="text-green-600" strokeWidth={2} />
              </div>
              <p className="m-0 text-sm font-bold text-text">
                {t("All systems healthy")}
              </p>
              <p className="m-0 mt-1 text-xs text-text-secondary">
                {t("No anomalies, missing data, or discrepancy surveys requiring review.")}
              </p>
            </div>
          ) : (
            systemAlerts.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                onNavigate={(path) => {
                  navigate(path);
                  setIsOpen(false);
                }}
              />
            ))
          )
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center text-text-secondary">
            <div className="w-12 h-12 rounded-2xl bg-ink-50 border border-border flex items-center justify-center mx-auto mb-3">
              <Bell size={22} className="text-text-muted" strokeWidth={1.75} />
            </div>
            <p className="m-0 text-sm font-bold text-text">
              {t("No notifications")}
            </p>
            <p className="m-0 mt-1 text-xs text-text-secondary">
              {t("You're all caught up")}
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
      <div className="p-2.5 px-4.5 border-t border-border bg-ink-50/60 text-xs text-text-secondary font-medium flex justify-between items-center">
        <span className={cn("font-semibold", (unreadCount > 0 || systemAlerts.length > 0) && "text-brand-700")}>
          {systemAlerts.length} {t("alerts")} · {unreadCount} {t("unread")}
        </span>
        <button
          type="button"
          onClick={() => {
            fetchNotifications({ announce: false });
            fetchSystemAlerts();
            toast.info(t("Refreshed alerts & notifications"));
          }}
          className="text-xs text-brand-600 hover:text-brand-800 bg-transparent border-none cursor-pointer font-medium p-0"
        >
          {t("Refresh")}
        </button>
      </div>
    </div>
  );

  const totalBadgeCount = unreadCount + systemAlerts.length;

  return (
    <div ref={dropdownRef} className="relative!">
      <BellButton count={totalBadgeCount} onClick={() => setIsOpen((o) => !o)} />

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

const headerActionBtn: React.CSSProperties = {
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
