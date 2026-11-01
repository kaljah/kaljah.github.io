import React, { useEffect, useRef, useState, useMemo } from "react";
import { NavLink, useLocation } from "react-router-dom";
import * as RadixDialog from "@radix-ui/react-dialog";
import {
  Calculator,
  Database,
  FileText,
  Gauge,
  History,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  ShieldCheck,
  X,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useLayout } from "../../context/LayoutContext";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { Tooltip, cn } from "../../ui";
import { ACCESS } from "../access";
import type { User } from "../../types/auth";
import { t } from "../../i18n";
import api from "../../api";

const STORAGE_KEY = "ct.sidebar.collapsed";

const readCollapsed = (): boolean => {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
};

export interface TopNavItemDef {
  id: string;
  title: string;
  path: string;
  icon: LucideIcon;
  badge?: number;
  badgeTone?: "brand" | "amber";
  isActive: (pathname: string, search: string) => boolean;
  canAccess: (user: User | null) => boolean;
  emphasis?: (user: User | null) => boolean;
}

interface NavItemProps {
  item: TopNavItemDef;
  showLabel: boolean;
  onNavigate?: () => void;
  user: User | null;
}

const NavItem: React.FC<NavItemProps> = ({ item, showLabel, onNavigate, user }) => {
  const Icon = item.icon;
  const location = useLocation();
  const active = item.isActive(location.pathname, location.search);
  const isEmphasized = item.emphasis ? item.emphasis(user) : false;

  const link = (
    <NavLink
      to={item.path}
      onClick={onNavigate}
      aria-label={showLabel ? undefined : item.title}
      className={cn(
        "relative flex h-10 items-center rounded-md text-base font-medium no-underline transition-colors",
        showLabel ? "gap-3 px-3" : "justify-center px-0",
        active
          ? "bg-selected-bg text-selected-fg font-semibold"
          : "text-text-secondary hover:bg-ink-100 hover:text-text",
        isEmphasized && !active && "border-l-2 border-brand-500/70 bg-brand-50/30",
      )}
    >
      {active && (
        <span
          aria-hidden="true"
          className="absolute inset-y-2 left-0 w-[3px] rounded-full bg-brand-600"
        />
      )}
      <Icon
        className={cn(
          "size-[18px] shrink-0",
          active ? "text-brand-600" : isEmphasized ? "text-brand-500" : "text-text-secondary",
        )}
        aria-hidden="true"
      />
      {showLabel && (
        <span className="truncate flex-1 text-left">{item.title}</span>
      )}
      {item.badge != null && item.badge > 0 && (
        <span
          className={cn(
            "rounded-full px-1.5 py-0.2 text-xs font-bold shrink-0",
            item.badgeTone === "amber"
              ? "bg-amber-100 text-amber-800"
              : "bg-brand-100 text-brand-700",
            !showLabel && "absolute top-1.5 right-1.5 size-2 p-0 rounded-full bg-brand-600",
          )}
        >
          {showLabel ? (item.badge > 99 ? "99+" : item.badge) : null}
        </span>
      )}
    </NavLink>
  );

  return showLabel ? link : <Tooltip content={item.title} side="right">{link}</Tooltip>;
};

interface NavListProps {
  user: User | null;
  showLabel: boolean;
  onNavigate?: () => void;
  pendingCount?: number;
}

const NavList: React.FC<NavListProps> = ({ user, showLabel, onNavigate, pendingCount = 0 }) => {
  const isIT = Boolean(user?.role && ["it", "it_admin", "it_manager"].includes(user.role));
  const isAuditor = user?.role === "auditor";
  const isOperator = user?.role === "user";
  const isAdminLike = Boolean(user?.role && ["admin", "superuser"].includes(user.role));

  const items: TopNavItemDef[] = useMemo(() => {
    return [
      {
        id: "home",
        title: t("Home"),
        path: "/",
        icon: LayoutDashboard,
        canAccess: (u) => ACCESS.nonIT(u),
        isActive: (pathname) => pathname === "/" || pathname === "/dashboard",
      },
      {
        id: "performance",
        title: t("Performance"),
        path: "/carbon-intensity",
        icon: Gauge,
        canAccess: (u) => ACCESS.nonIT(u),
        isActive: (pathname) =>
          ["/carbon-intensity", "/methane-intensity", "/sbti", "/methane-explorer"].includes(pathname),
      },
      {
        id: "data-entry",
        title: t("Data Entry"),
        path: "/emissions",
        icon: Calculator,
        canAccess: (u) => ACCESS.nonIT(u),
        isActive: (pathname) => pathname === "/emissions",
        emphasis: () => isOperator,
      },
      {
        id: "manage-data",
        title: t("Data Management"),
        path: "/manage-data",
        icon: Database,
        canAccess: (u) => ACCESS.nonIT(u),
        isActive: (pathname, search) =>
          (pathname === "/manage-data" && !search.includes("tab=pending")) || pathname === "/reference-data",
      },
      {
        id: "review",
        title: t("Review"),
        path: isAdminLike ? "/manage-data?tab=pending" : "/manage-data?tab=pending",
        icon: ShieldCheck,
        badge: pendingCount,
        badgeTone: "amber",
        canAccess: (u) => ACCESS.nonIT(u),
        isActive: (pathname, search) =>
          pathname === "/qa-dashboard" || (pathname === "/manage-data" && search.includes("tab=pending")),
        emphasis: () => isAdminLike || isAuditor,
      },
      {
        id: "reports",
        title: t("Reports"),
        path: "/reports",
        icon: FileText,
        canAccess: (u) => ACCESS.nonIT(u),
        isActive: (pathname) => ["/reports", "/uncertainty"].includes(pathname),
      },
      {
        id: "governance",
        title: t("Governance"),
        path: isIT ? "/user-management" : isAuditor ? "/audit-trail" : "/settings",
        icon: History,
        canAccess: () => true,
        isActive: (pathname) => ["/audit-trail", "/settings", "/user-management"].includes(pathname),
        emphasis: () => isIT || isAuditor,
      },
    ];
  }, [isIT, isAuditor, isOperator, isAdminLike, pendingCount]);

  const visibleItems = items.filter((item) => item.canAccess(user));

  return (
    <nav aria-label={t("Main")} className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-2">
      <ul className="m-0 flex list-none flex-col gap-1 p-0">
        {visibleItems.map((item) => (
          <li key={item.id}>
            <NavItem item={item} showLabel={showLabel} onNavigate={onNavigate} user={user} />
          </li>
        ))}
      </ul>
    </nav>
  );
};

const Brand: React.FC<{ showLabel: boolean }> = ({ showLabel }) => (
  <div className={cn("flex h-16 shrink-0 items-center", showLabel ? "gap-3 px-4" : "justify-center px-0")}>
    <img src={`${import.meta.env.BASE_URL}carbon_tech.svg`} alt="" className="size-8 shrink-0" />
    {showLabel && <span className="truncate text-md font-bold text-text">{t("NeoCarbon")}</span>}
  </div>
);

const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const { isMobileNavOpen, setIsMobileNavOpen, closeMobileNav } = useLayout();
  const isMobile = useMediaQuery("(max-width: 899px)");
  const [collapsed, setCollapsed] = useState<boolean>(readCollapsed);
  const [peek, setPeek] = useState<boolean>(false);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const peekTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Poll or fetch pending queue count for the Review badge
  useEffect(() => {
    if (!user || user.role === "it") return;
    let active = true;
    const fetchPending = async () => {
      try {
        const res = await api.get("/emissions/pending");
        if (active && res.data) {
          setPendingCount(res.data.total_pending || 0);
        }
      } catch {
        // quiet fallback
      }
    };
    fetchPending();
    const interval = setInterval(fetchPending, 45_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [user]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {
      // storage unavailable
    }
  }, [collapsed]);

  // "[" toggles the sidebar (ignored while typing)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      if (e.key !== "[" || e.ctrlKey || e.metaKey || e.altKey) return;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable) return;
      setCollapsed((c) => !c);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => () => {
    if (peekTimer.current) clearTimeout(peekTimer.current);
  }, []);

  if (isMobile) {
    return (
      <RadixDialog.Root open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <RadixDialog.Portal>
          <RadixDialog.Overlay className="fixed inset-0 z-(--z-overlay) bg-ink-900/45" />
          <RadixDialog.Content
            aria-describedby={undefined}
            className="fixed inset-y-0 left-0 z-(--z-modal) flex w-72 max-w-[85vw] flex-col bg-surface shadow-overlay"
          >
            <RadixDialog.Title className="sr-only">{t("Navigation")}</RadixDialog.Title>
            <div className="flex h-16 items-center justify-between border-b border-border/50 px-4">
              <Brand showLabel />
              <RadixDialog.Close
                aria-label={t("Close navigation")}
                className="inline-flex size-10 cursor-pointer items-center justify-center rounded-full border-0 bg-ink-100 text-text-secondary transition-colors hover:bg-ink-200 hover:text-text focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <X className="size-5" aria-hidden="true" />
              </RadixDialog.Close>
            </div>
            <NavList user={user} showLabel onNavigate={closeMobileNav} pendingCount={pendingCount} />
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>
    );
  }

  const open = (value: boolean) => {
    if (peekTimer.current) clearTimeout(peekTimer.current);
    if (!value) return setPeek(false);
    peekTimer.current = setTimeout(() => setPeek(true), 150);
  };
  const expanded = !collapsed || peek;

  return (
    <div className={cn("app-sidebar relative z-(--z-sidebar) shrink-0 transition-[width] duration-200", collapsed ? "w-16" : "w-60")}>
      <aside
        onMouseEnter={() => collapsed && open(true)}
        onMouseLeave={() => open(false)}
        onFocus={() => collapsed && open(true)}
        onBlur={(e) => !e.currentTarget.contains(e.relatedTarget as Node) && open(false)}
        className={cn(
          "absolute inset-y-0 left-0 z-(--z-sidebar) flex flex-col border-r border-border bg-surface transition-[width,box-shadow] duration-200",
          expanded ? "w-60" : "w-16",
          collapsed && peek && "shadow-raised",
        )}
      >
        <Brand showLabel={expanded} />
        <NavList user={user} showLabel={expanded} pendingCount={pendingCount} />
        <div className="border-t border-border px-2 py-2 flex flex-col gap-1">
          <NavLink
            to="/settings"
            aria-label={expanded ? undefined : t("Settings")}
            className={({ isActive }) =>
              cn(
                "relative flex h-10 items-center rounded-md text-base font-medium no-underline transition-colors",
                expanded ? "gap-3 px-3" : "justify-center px-0",
                isActive ? "bg-selected-bg text-selected-fg font-semibold" : "text-text-secondary hover:bg-ink-100 hover:text-text",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Settings className={cn("size-[18px] shrink-0", isActive ? "text-brand-600" : "text-text-secondary")} aria-hidden="true" />
                {expanded && <span className="truncate">{t("Settings")}</span>}
              </>
            )}
          </NavLink>
          <button
            type="button"
            onClick={() => {
              setCollapsed((c) => !c);
              setPeek(false);
            }}
            aria-label={collapsed ? t("Pin sidebar open") : t("Collapse sidebar")}
            aria-keyshortcuts="["
            className={cn(
              "flex h-10 w-full cursor-pointer items-center rounded-md border-0 bg-transparent text-base font-medium text-text-secondary transition-colors hover:bg-ink-100 hover:text-text",
              expanded ? "gap-3 px-3" : "justify-center px-0",
            )}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-[18px] shrink-0" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="size-[18px] shrink-0" aria-hidden="true" />
            )}
            {expanded && <span className="truncate">{collapsed ? t("Pin open") : t("Collapse")}</span>}
          </button>
        </div>
      </aside>
    </div>
  );
};

export default Sidebar;
