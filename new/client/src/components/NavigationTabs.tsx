import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Gauge,
  Wind,
  Target,
  Map,
  Clock,
  ShieldCheck,
  FileText,
  Sigma,
  History,
  Settings as SettingsIcon,
  Users,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../ui/cn";
import { useAuth } from "../context/AuthContext";
import { t } from "../i18n";

export interface NavTabItem {
  path: string;
  label: string;
  icon?: LucideIcon;
  badge?: React.ReactNode;
  activeMatch?: (pathname: string, search: string) => boolean;
}

interface NavTabsBarProps {
  items: NavTabItem[];
  className?: string;
  ariaLabel?: string;
}

export const NavTabsBar: React.FC<NavTabsBarProps> = ({ items, className, ariaLabel }) => {
  const location = useLocation();

  return (
    <nav
      aria-label={ariaLabel || t("Section navigation")}
      className={cn("flex items-center gap-1 border-b border-border overflow-x-auto bg-surface/50 px-2 pt-2", className)}
    >
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = item.activeMatch
          ? item.activeMatch(location.pathname, location.search)
          : location.pathname === item.path;

        return (
          <NavLink
            key={item.path}
            to={item.path}
            className={cn(
              "-mb-px inline-flex shrink-0 cursor-pointer items-center gap-2 border-b-2 px-4 py-2.5 text-base font-medium transition-colors no-underline",
              isActive
                ? "border-primary text-selected-fg font-semibold bg-brand-50/60 rounded-t-md"
                : "border-transparent text-text-secondary hover:text-text hover:bg-ink-50 rounded-t-md",
            )}
          >
            {Icon && <Icon className={cn("size-4 shrink-0", isActive ? "text-brand-600" : "text-text-secondary")} />}
            <span>{item.label}</span>
            {item.badge != null && (
              <span className="rounded-full bg-brand-100 px-1.5 py-0.5 text-xs font-bold text-brand-700">
                {item.badge}
              </span>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
};

/** Performance section tabs: Carbon Intensity, Methane Intensity, SBTi & Net-Zero, Emissions Map */
export const PerformanceNavTabs: React.FC<{ className?: string }> = ({ className }) => {
  const items: NavTabItem[] = [
    {
      path: "/carbon-intensity",
      label: t("Carbon Intensity"),
      icon: Gauge,
    },
    {
      path: "/methane-intensity",
      label: t("Methane Intensity"),
      icon: Wind,
    },
    {
      path: "/sbti",
      label: t("SBTi Pathway (indicative)"),
      icon: Target,
    },
    {
      path: "/methane-explorer",
      label: t("Emissions Map"),
      icon: Map,
    },
  ];

  return <NavTabsBar items={items} className={className} ariaLabel={t("Performance Navigation")} />;
};

/** Reports section tabs: Reports, Uncertainty */
export const ReportsNavTabs: React.FC<{ className?: string }> = ({ className }) => {
  const items: NavTabItem[] = [
    {
      path: "/reports",
      label: t("Reports"),
      icon: FileText,
    },
    {
      path: "/uncertainty",
      label: t("Uncertainty Assessment"),
      icon: Sigma,
    },
  ];

  return <NavTabsBar items={items} className={className} ariaLabel={t("Reports Navigation")} />;
};

/** Review section tabs: Pending Review, QA/QC & Diagnostics */
export const ReviewNavTabs: React.FC<{ pendingCount?: number; className?: string }> = ({ pendingCount, className }) => {
  const { user } = useAuth();
  const isSuperuser = Boolean(user?.role && ["admin", "superuser"].includes(user.role));

  const items: NavTabItem[] = [
    {
      path: "/manage-data?tab=pending",
      label: t("Pending Review"),
      icon: Clock,
      badge: pendingCount && pendingCount > 0 ? pendingCount : undefined,
      activeMatch: (pathname, search) => pathname === "/manage-data" && search.includes("tab=pending"),
    },
  ];

  if (isSuperuser) {
    items.push({
      path: "/qa-dashboard",
      label: t("QA/QC & Diagnostics"),
      icon: ShieldCheck,
      activeMatch: (pathname) => pathname === "/qa-dashboard",
    });
  }

  return <NavTabsBar items={items} className={className} ariaLabel={t("Review Navigation")} />;
};

/** Governance section tabs: Audit Trail, Settings, User Management */
export const GovernanceNavTabs: React.FC<{ className?: string }> = ({ className }) => {
  const { user } = useAuth();
  const isIT = Boolean(user?.role && ["it", "it_admin", "it_manager"].includes(user.role));
  const isPrivileged = Boolean(user?.role && ["admin", "superuser", "it", "it_admin", "it_manager"].includes(user.role));

  const items: NavTabItem[] = [
    {
      path: "/audit-trail",
      label: t("Audit Trail"),
      icon: History,
      activeMatch: (pathname) => pathname === "/audit-trail",
    },
  ];

  if (!isIT) {
    items.push({
      path: "/settings",
      label: t("Settings"),
      icon: SettingsIcon,
      activeMatch: (pathname) => pathname === "/settings",
    });
  }

  if (isIT || isPrivileged) {
    items.push({
      path: "/user-management",
      label: t("User Management"),
      icon: Users,
      activeMatch: (pathname) => pathname === "/user-management",
    });
  }

  return <NavTabsBar items={items} className={className} ariaLabel={t("Governance Navigation")} />;
};
