import React from "react";
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Database,
  Download,
  Edit3,
  Eye,
  FileSpreadsheet,
  FileText,
  Filter,
  LogIn,
  Plus,
  RefreshCw,
  Shield,
  ShieldAlert,
  Trash2,
  XCircle,
} from "lucide-react";
import { Badge, Button, Card, EmptyState, Menu, MenuContent, MenuItem, MenuTrigger, NativeSelect, SegmentedControl, Skeleton, StatCard } from "../../ui";
import { cn } from "../../ui/cn";

/** Timeline marker and badge look for each audit action. */
const STYLES = {
  create: { icon: Plus, node: "bg-green-500", tone: "success" },
  update: { icon: Edit3, node: "bg-blue-500", tone: "info" },
  delete: { icon: Trash2, node: "bg-red-500", tone: "danger" },
  login: { icon: LogIn, node: "bg-sky-500", tone: "info" },
  security: { icon: ShieldAlert, node: "bg-amber-500", tone: "warning" },
  export: { icon: Download, node: "bg-violet-500", tone: "brand" },
  view: { icon: Eye, node: "bg-slate-500", tone: "neutral" },
  approve: { icon: CheckCircle2, node: "bg-green-600", tone: "success" },
  reject: { icon: XCircle, node: "bg-red-600", tone: "danger" },
  other: { icon: Activity, node: "bg-slate-500", tone: "neutral" },
};
const ALIASES = { register: "create" };

// eslint-disable-next-line react-refresh/only-export-components -- plain helper shared with the timeline
export const actionStyle = (action) => {
  const key = String(action || "").toLowerCase();
  return STYLES[ALIASES[key] || key] || STYLES.other;
};

/** Page title, view switch, refresh and export menu. */
export const AuditHeader = ({ view, onView, refreshing, onRefresh, onExport }) => (
  <div className="mb-6 flex flex-col items-stretch justify-between gap-5 md:flex-row md:items-start">
    <div className="min-w-0">
      <Badge tone="brand" className="mb-2 gap-1.5 px-2.5 py-1 uppercase tracking-wide">
        <Shield className="size-3.5" aria-hidden="true" /> Immutable Compliance Log
      </Badge>
      <h1 className="m-0 mb-1.5 text-xl font-bold text-text">Audit Trail &amp; System Activity</h1>
      <p className="m-0 max-w-3xl text-md leading-normal text-text-secondary">
        Comprehensive tamper-evident record of all emissions data, authentication, calculations, and administrative actions
      </p>
    </div>

    <div className="flex flex-wrap items-center justify-between gap-3 md:justify-end">
      <SegmentedControl
        label="Audit view"
        value={view}
        onChange={onView}
        options={[
          { value: "table", label: "Table" },
          { value: "timeline", label: "Timeline" },
        ]}
      />
      <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>
        <RefreshCw className={cn("size-4", refreshing && "animate-spin")} aria-hidden="true" /> Refresh
      </Button>
      <Menu>
        <MenuTrigger asChild>
          <Button>
            <Download className="size-4" aria-hidden="true" /> Export Audit Log <ChevronDown className="size-3.5" aria-hidden="true" />
          </Button>
        </MenuTrigger>
        <MenuContent>
          <MenuItem icon={FileSpreadsheet} onSelect={() => onExport("csv")}>
            <span className="flex flex-col">
              <strong className="text-sm">CSV Spreadsheet</strong>
              <span className="text-xs text-text-secondary">Compliant with audit tools &amp; Excel</span>
            </span>
          </MenuItem>
          <MenuItem icon={FileText} onSelect={() => onExport("json")}>
            <span className="flex flex-col">
              <strong className="text-sm">JSON Structured Data</strong>
              <span className="text-xs text-text-secondary">Full metadata &amp; field diffs</span>
            </span>
          </MenuItem>
        </MenuContent>
      </Menu>
    </div>
  </div>
);

/** Four headline counters. */
export const AuditStats = ({ stats }) => (
  <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatCard icon={Activity} label="Total Events Logged" valueText={stats.totalEvents.toLocaleString()} />
    <StatCard icon={LogIn} label="User Logins" valueText={stats.totalLogins.toLocaleString()} />
    <StatCard icon={Database} label="Data Changes" valueText={stats.dataMutations.toLocaleString()} />
    <StatCard icon={ShieldAlert} label="Security & Alerts" valueText={stats.securityAlerts.toLocaleString()} />
  </div>
);

export const AuditSkeleton = () => (
  <div role="status" aria-label="Loading audit events" className="flex flex-col gap-4">
    {[1, 2, 3, 4].map((i) => (
      <Card key={i} className="flex items-center gap-4">
        <Skeleton className="size-10 shrink-0 rounded-md" />
        <div className="flex flex-1 flex-col gap-2.5">
          <Skeleton className="h-3 w-2/5" />
          <Skeleton className="h-3 w-4/5" />
          <Skeleton className="h-3 w-1/5" />
        </div>
      </Card>
    ))}
  </div>
);

export const AuditEmpty = ({ filtered, onReset }) => (
  <Card>
    <EmptyState
      icon={Filter}
      title="No audit records found"
      description={filtered ? "No activity logs match your current filter and search criteria." : "No compliance audit records have been generated yet."}
      action={filtered ? <Button onClick={onReset}>Clear All Filters</Button> : undefined}
    />
  </Card>
);

export const AuditPagination = ({ page, totalPages, totalRecords, limit, onLimit, onPage }) => (
  <Card className="mt-7 flex flex-col items-stretch justify-between gap-4 px-5 py-4 text-center sm:flex-row sm:items-center sm:text-left">
    <p className="m-0 text-base text-text-secondary">
      Page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalRecords} total events)
    </p>
    <div className="flex flex-wrap items-center justify-center gap-4">
      <label className="flex items-center gap-2 text-sm text-text-secondary">
        Rows:
        <NativeSelect
          className="h-8 rounded-md border border-border bg-surface px-2 text-sm text-text"
          value={limit}
          onChange={(e) => onLimit(Number(e.target.value))}
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </NativeSelect>
      </label>
      <div className="flex items-center gap-2.5">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPage(Math.max(1, page - 1))} title="Previous Page">
          <ChevronLeft className="size-4" aria-hidden="true" /> Prev
        </Button>
        <span className="min-w-11 text-center text-sm font-semibold text-text-secondary">
          {page} / {totalPages}
        </span>
        <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => onPage(Math.min(totalPages, page + 1))} title="Next Page">
          Next <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  </Card>
);
