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
  Zap,
  type LucideIcon,
} from "lucide-react";
import api from "../api";
import { useToast } from "./Toast";
import { useAuth } from "../context/AuthContext";
import { t } from "../i18n";

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
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
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
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
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

  // ── Mount / unmount ───────────────────────────────────────────────────
  useEffect(() => {
    if (!userId) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    activeRef.current = true;
    lastIdRef.current = 0;
    fetchNotifications();
    const poll = () => {
      if (document.visibilityState === "visible") fetchNotifications({ announce: true });
    };
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    document.addEventListener("visibilitychange", poll);
    return () => {
      activeRef.current = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", poll);
    };
  }, [userId, fetchNotifications]);

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

      {/* ── Notification list ── */}
      <div className={`[max-height:420px]! [overflow-y:auto]!`}>
        {notifications.length === 0 ? (
          <div
            className="p-[40px_24px]! text-center! text-[color:var(--text-secondary,_var(--color-ink-500))]!"
          >
            <div
              className="w-[48px]! h-[48px]! rounded-[14px]! bg-[color:var(--bg-hover,_var(--color-ink-50))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! flex! items-center! justify-center! m-[0_auto_12px]!"
            >
              <Bell
                size={22}
                color="var(--text-muted, var(--color-ink-400))"
                strokeWidth={1.75}
              />
            </div>
            <p className="m-[0px]! text-[length:0.88rem]! font-bold! text-[color:var(--text-primary,_var(--color-ink-900))]!">
              {t("No notifications")}
            </p>
            <p
              className="m-[4px_0_0]! text-[length:0.78rem]! text-[color:var(--text-secondary,_var(--color-ink-500))]!"
            >
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
      {notifications.length > 0 && (
        <div
          className="p-[9px_18px]! [border-top:1px_solid_var(--border-color,_var(--color-ink-200))]! bg-[color:var(--bg-hover,_var(--color-ink-50))]! text-[length:0.74rem]! text-[color:var(--text-secondary,_var(--color-ink-500))]! font-medium! flex! justify-between! items-center!"
        >
          <span className={`[font-weight:600]! ${hasUnread ? "[color:var(--color-legacy-ea580c)]!" : "[color:inherit]!"}`}>
            {unreadCount}{" "}{t("unread")}
          </span>
          <span>{t("Showing")}{" "}{notifications.length}{" "}{t("notifications")}</span>
        </div>
      )}
    </div>
  );

  return (
    <div ref={dropdownRef} className="relative!">
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
