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
import api from "../../api";
import { Badge, Banner, Button, Card, EmptyState, Menu, MenuContent, MenuItem, MenuTrigger, NativeSelect, SegmentedControl, Skeleton, StatCard, type BadgeTone } from "../../ui";
import { cn } from "../../ui/cn";
import { t } from "../../i18n";

export interface ActionStyleDef {
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  node: string;
  tone: BadgeTone;
}

/** Timeline marker and badge look for each audit action. */
const STYLES: Record<string, ActionStyleDef> = {
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
const ALIASES: Record<string, string> = { register: "create" };

// eslint-disable-next-line react-refresh/only-export-components -- plain helper shared with the timeline
export const actionStyle = (action?: string): ActionStyleDef => {
  const key = String(action || "").toLowerCase();
  return STYLES[ALIASES[key] || key] || STYLES.other;
};

export interface AuditHeaderProps {
  view: string;
  onView: (view: string) => void;
  refreshing: boolean;
  onRefresh: () => void;
  onExport: (format: "csv" | "json") => void;
}

/** Page title, view switch, refresh and export menu. */
export const AuditHeader: React.FC<AuditHeaderProps> = ({ view, onView, refreshing, onRefresh, onExport }) => (
  <div className="mb-6 flex flex-col items-stretch justify-between gap-5 md:flex-row md:items-start">
    <div className="min-w-0">
      <Badge tone="brand" className="mb-2 gap-1.5 px-2.5 py-1 uppercase tracking-wide">
        <Shield className="size-3.5" aria-hidden="true" />{" "}{t("Tamper-evident log")}
      </Badge>
      <h1 className="m-0 mb-1.5 text-xl font-bold text-text">{t("Audit Trail & System Activity")}</h1>
      <p className="m-0 max-w-3xl text-md leading-normal text-text-secondary">
        {t("Every change to emissions data, sign-ins, calculations and administrative actions. Each entry is sealed into a hash chain when it is written, so a later edit or deletion shows up when the log is verified.")}
      </p>
    </div>

    <div className="flex flex-wrap items-center justify-between gap-3 md:justify-end">
      <SegmentedControl
        label={t("Audit view")}
        value={view}
        onChange={onView}
        options={[
          { value: "table", label: t("Table") },
          { value: "timeline", label: t("Timeline") },
        ]}
      />
      <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>
        <RefreshCw className={cn("size-4", refreshing && "animate-spin")} aria-hidden="true" />{" "}{t("Refresh")}
      </Button>
      <Menu>
        <MenuTrigger asChild>
          <Button>
            <Download className="size-4" aria-hidden="true" />{" "}{t("Export Audit Log")}{" "}<ChevronDown className="size-3.5" aria-hidden="true" />
          </Button>
        </MenuTrigger>
        <MenuContent>
          <MenuItem icon={FileSpreadsheet} onSelect={() => onExport("csv")}>
            <span className="flex flex-col">
              <strong className="text-sm">{t("CSV Spreadsheet")}</strong>
              <span className="text-xs text-text-secondary">{t("Compliant with audit tools & Excel")}</span>
            </span>
          </MenuItem>
          <MenuItem icon={FileText} onSelect={() => onExport("json")}>
            <span className="flex flex-col">
              <strong className="text-sm">{t("JSON Structured Data")}</strong>
              <span className="text-xs text-text-secondary">{t("Full metadata & field diffs")}</span>
            </span>
          </MenuItem>
        </MenuContent>
      </Menu>
    </div>
  </div>
);

export interface AuditStatsProps {
  stats: {
    totalEvents: number;
    totalLogins: number;
    dataMutations: number;
    securityAlerts: number;
  };
}

/** Four headline counters. */
export const AuditStats: React.FC<AuditStatsProps> = ({ stats }) => (
  <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatCard icon={Activity} label={t("Total Events Logged")} valueText={stats.totalEvents.toLocaleString()} />
    <StatCard icon={LogIn} label={t("User Logins")} valueText={stats.totalLogins.toLocaleString()} />
    <StatCard icon={Database} label={t("Data Changes")} valueText={stats.dataMutations.toLocaleString()} />
    <StatCard icon={ShieldAlert} label={t("Security & Alerts")} valueText={stats.securityAlerts.toLocaleString()} />
  </div>
);

export const AuditSkeleton: React.FC = () => (
  <div role="status" aria-label={t("Loading audit events")} className="flex flex-col gap-4">
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

export interface AuditEmptyProps {
  filtered: boolean;
  onReset: () => void;
}

export const AuditEmpty: React.FC<AuditEmptyProps> = ({ filtered, onReset }) => (
  <Card>
    <EmptyState
      icon={Filter}
      title={t("No audit records found")}
      description={filtered ? t("No activity logs match your current filter and search criteria.") : t("No compliance audit records have been generated yet.")}
      action={filtered ? <Button onClick={onReset}>{t("Clear All Filters")}</Button> : undefined}
    />
  </Card>
);

export interface AuditPaginationProps {
  page: number;
  totalPages: number;
  totalRecords: number;
  limit: number;
  onLimit: (limit: number) => void;
  onPage: (page: number) => void;
}

export const AuditPagination: React.FC<AuditPaginationProps> = ({ page, totalPages, totalRecords, limit, onLimit, onPage }) => (
  <Card className="mt-7 flex flex-col items-stretch justify-between gap-4 px-5 py-4 text-center sm:flex-row sm:items-center sm:text-left">
    <p className="m-0 text-base text-text-secondary">
      {t("Page")}{" "}<strong>{page}</strong>{" "}{t("of")}{" "}<strong>{totalPages}</strong> ({totalRecords}{" "}{t("total events)")}
    </p>
    <div className="flex flex-wrap items-center justify-center gap-4">
      <label className="flex items-center gap-2 text-sm text-text-secondary">
        {t("Rows:")}
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
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPage(Math.max(1, page - 1))} title={t("Previous Page")}>
          <ChevronLeft className="size-4" aria-hidden="true" />{" "}{t("Prev")}
        </Button>
        <span className="min-w-11 text-center text-sm font-semibold text-text-secondary">
          {page} / {totalPages}
        </span>
        <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => onPage(Math.min(totalPages, page + 1))} title={t("Next Page")}>
          {t("Next")}{" "}<ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  </Card>
);

interface ChainResult {
  status: "verified" | "tampered";
  total_records: number;
  issue_count: number;
  issues: { id: number; problem: string; detail: string }[];
  chain_head_hash: string;
  checkpoint_hmac: string;
  verified_at: string;
}

/** Runs the hash-chain check of the whole log (GET /audit/verify-chain) and shows the outcome. */
export const AuditIntegrityCheck: React.FC = () => {
  const [result, setResult] = React.useState<ChainResult | null>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const verify = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.get("/audit/verify-chain");
      setResult(res.data);
    } catch (err: any) {
      setResult(null);
      setError(err.response?.data?.error || t("The log could not be verified."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mb-6 flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="secondary" onClick={verify} disabled={busy}>
          <Shield className="size-4" aria-hidden="true" /> {busy ? t("Verifying...") : t("Verify integrity")}
        </Button>
        <span className="text-sm text-text-secondary">{t("Checks every entry against the hash sealed when it was written.")}</span>
      </div>
      {error && <Banner tone="danger">{error}</Banner>}
      {result && result.status === "verified" && (
        <Banner tone="success" title={t("Log intact: {{count}} entries verified", { count: result.total_records.toLocaleString() })}>
          {t("No entry was changed, removed or inserted. To detect a later removal of the newest entries, keep this checkpoint:")}{" "}
          <span className="break-all font-mono text-xs">
            {result.total_records}{" "}{t("entries · head")}{" "}{result.chain_head_hash}{" "}{t("· seal")}{" "}{result.checkpoint_hmac}
          </span>
        </Banner>
      )}
      {result && result.status === "tampered" && (
        <Banner tone="danger" title={result.issue_count === 1 ? t("Log altered: 1 problem in {{total}} entries", { total: result.total_records.toLocaleString() }) : t("Log altered: {{count}} problems in {{total}} entries", { count: result.issue_count, total: result.total_records.toLocaleString() })}>
          <ul className="m-0 mt-1 list-disc pl-5">
            {result.issues.map((i) => (
              <li key={`${i.id}-${i.problem}`}>
                {t("Entry #")}{i.id}: {i.detail}
              </li>
            ))}
          </ul>
        </Banner>
      )}
    </div>
  );
};
