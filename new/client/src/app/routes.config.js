import React from "react";
import {
  Calculator,
  Database,
  FileText,
  Gauge,
  History,
  LayoutDashboard,
  Library,
  Map,
  Settings,
  ShieldCheck,
  Sigma,
  Target,
  Users,
  Wind,
} from "lucide-react";

// Single source of truth for routes, navigation, breadcrumbs, titles and the command palette.
// Paths are unchanged from the old App.jsx (bookmarks and e2e depend on them).
const page = (loader) => React.lazy(loader);

export const NAV_GROUPS = ["Overview", "Data", "Assurance & Reporting", "Administration"];

export const ROUTES = [
  { path: "/", filters: true, index: true, title: "Dashboard", group: "Overview", icon: LayoutDashboard, access: "nonIT", Component: page(() => import("../pages/DashboardEnhanced")) },
  { path: "/carbon-intensity", filters: true, title: "Carbon Intensity", group: "Overview", icon: Gauge, access: "nonIT", Component: page(() => import("../pages/CarbonIntensity")) },
  { path: "/methane-intensity", filters: true, title: "Methane Intensity", group: "Overview", icon: Wind, access: "nonIT", Component: page(() => import("../pages/MethaneIntensity")) },
  { path: "/sbti", title: "SBTi & Net-Zero", group: "Overview", icon: Target, access: "nonIT", Component: page(() => import("../pages/SbtiDashboard")) },
  { path: "/methane-explorer", title: "Emissions Map", group: "Overview", icon: Map, access: "nonIT", Component: page(() => import("../pages/MethaneExplorer")) },
  { path: "/emissions", title: "Calculations", group: "Data", icon: Calculator, access: "nonIT", Component: page(() => import("../pages/Emissions")) },
  { path: "/manage-data", title: "Manage Data", group: "Data", icon: Database, access: "nonIT", Component: page(() => import("../pages/ManageData")) },
  { path: "/reference-data", title: "Reference Data", group: "Data", icon: Library, access: "nonIT", Component: page(() => import("../pages/ReferenceData")) },
  { path: "/reports", title: "Reports", group: "Assurance & Reporting", icon: FileText, access: "nonIT", Component: page(() => import("../pages/Reports")) },
  { path: "/uncertainty", title: "Uncertainty", group: "Assurance & Reporting", icon: Sigma, access: "nonIT", Component: page(() => import("../pages/UncertaintyAssessment")) },
  { path: "/qa-dashboard", title: "QA/QC & Diagnostics", group: "Assurance & Reporting", icon: ShieldCheck, access: "superuser", Component: page(() => import("../pages/QADashboard")) },
  { path: "/audit-trail", title: "Audit Trail", group: "Assurance & Reporting", icon: History, access: "audit", Component: page(() => import("../pages/AuditTrail")) },
  { path: "/user-management", title: "User Management", group: "Administration", icon: Users, access: "it", Component: page(() => import("../pages/UserManagement")) },
  // Pinned to the bottom of the sidebar instead of a group
  { path: "/settings", title: "Settings", group: null, icon: Settings, access: "nonIT", Component: page(() => import("../pages/Settings")) },
];

// Extra path that renders the dashboard (the old app served both / and /dashboard)
export const ALIASES = [{ path: "/dashboard", to: "/" }];

export const findRoute = (pathname) => {
  const clean = pathname.replace(/\/+$/, "") || "/";
  const norm = clean === "/dashboard" ? "/" : clean;
  return ROUTES.find((r) => r.path === norm);
};
