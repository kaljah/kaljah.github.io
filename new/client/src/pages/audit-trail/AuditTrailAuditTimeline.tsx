import React from "react";
import { ArrowRight, Calendar, ChevronDown, ChevronUp, Clock, Code, Database, Globe, History, User as UserIcon } from "lucide-react";
import { Badge, Button, Card } from "../../ui";
import { cn } from "../../ui/cn";
import type { ActionStyleDef } from "./AuditTrailChrome";
import { t } from "../../i18n";

const mono = "font-mono text-sm";

const Meta: React.FC<{ icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>; children: React.ReactNode }> = ({ icon: Icon, children }) => (
  <span className="inline-flex items-center gap-1.5">
    <Icon className="size-3" aria-hidden="true" />
    {children}
  </span>
);

interface DiffProps {
  log: AuditLogItem;
  formatDiffVal: (val: any) => string;
}

/** Before/after values of the fields an event changed. */
const Diff: React.FC<DiffProps> = ({ log, formatDiffVal }) => {
  const structured = typeof log.old_values === "object" && typeof log.new_values === "object" && (log.old_values !== null || log.new_values !== null);
  const keys = structured ? Array.from(new Set([...Object.keys(log.old_values || {}), ...Object.keys(log.new_values || {})])) : [];
  return (
    <div className="mb-3 rounded-md border border-border bg-ink-50 px-3.5 py-2.5">
      <p className="m-0 mb-2 flex items-center gap-1.5 text-sm font-bold uppercase tracking-wide text-text-secondary">
        <History className="size-3" aria-hidden="true" />{" "}{t("Field-level changes")}
      </p>
      {structured ? (
        <div className="flex flex-col gap-1.5">
          {keys.map((key) => {
            const before = formatDiffVal(log.old_values?.[key]);
            const after = formatDiffVal(log.new_values?.[key]);
            return (
              <div key={key} className={cn("flex items-center gap-2", mono)}>
                <span className="min-w-[90px] font-bold text-ink-700">{key}:</span>
                <span className="max-w-[280px] truncate rounded-sm bg-danger-bg px-1.5 py-0.5 text-danger-fg line-through" title={before}>
                  {before}
                </span>
                <ArrowRight className="size-3 shrink-0 text-ink-400" aria-hidden="true" />
                <span className="max-w-[280px] truncate rounded-sm bg-success-bg px-1.5 py-0.5 font-semibold text-success-fg" title={after}>
                  {after}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col gap-1 text-sm text-text-secondary">
          {log.old_values && (
            <div>
              <strong>{t("Before:")}</strong> {formatDiffVal(log.old_values)}
            </div>
          )}
          {log.new_values && (
            <div>
              <strong>{t("After:")}</strong> {formatDiffVal(log.new_values)}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export interface AuditLogItem {
  id: number | string;
  user?: string;
  action?: string;
  entity?: string;
  entityId?: string | number;
  recordId?: string | number;
  ipAddress?: string;
  timestamp?: string;
  description?: string;
  details?: string;
  old_values?: any;
  new_values?: any;
  [key: string]: any;
}

export interface AuditTrailAuditTimelineProps {
  auditLogs: AuditLogItem[];
  expandedRows: Set<number | string>;
  formatDiffVal: (val: any) => string;
  formatFullDateTime: (ts?: string) => string;
  formatTimestamp: (ts?: string) => string;
  actionStyle: (action?: string) => ActionStyleDef;
  toggleRawData: (id: number | string) => void;
}

/** Vertical timeline: one card per audit event with its diff, metadata and optional raw JSON. */
const AuditTrailAuditTimeline: React.FC<AuditTrailAuditTimelineProps> = ({
  auditLogs,
  expandedRows,
  formatDiffVal,
  formatFullDateTime,
  formatTimestamp,
  actionStyle,
  toggleRawData,
}) => (
  <ol className="m-0 flex list-none flex-col gap-5 p-0">
    {auditLogs.map((log) => {
      const style = actionStyle(log.action);
      const Icon = style.icon;
      const raw = expandedRows.has(log.id);
      return (
        <li key={log.id} className="group relative flex gap-4 sm:gap-6">
          <span className={cn("z-10 flex size-9 shrink-0 items-center justify-center rounded-md text-white sm:size-10", style.node)}>
            <Icon className="size-[18px]" aria-hidden="true" />
          </span>
          <span className="absolute bottom-[-20px] left-[17px] top-10 w-0.5 bg-ink-200 group-last:hidden sm:left-[19px]" aria-hidden="true" />

          <Card className="min-w-0 flex-1 px-5 py-4 transition-shadow hover:shadow-md">
            <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-ink-50 px-2 py-0.5 text-base font-bold text-ink-800">
                  <UserIcon className="size-3 text-ink-500" aria-hidden="true" /> {log.user}
                </span>
                <ArrowRight className="size-3 text-ink-400" aria-hidden="true" />
                <Badge tone={style.tone} className="font-extrabold uppercase tracking-wide">
                  {log.action}
                </Badge>
                <Badge>{log.entity}</Badge>
              </div>
              <span className="flex items-center gap-1.5 text-sm font-medium text-text-secondary" title={formatFullDateTime(log.timestamp)}>
                <Clock className="size-3 opacity-60" aria-hidden="true" /> {formatTimestamp(log.timestamp)}
              </span>
            </div>

            <p className="m-0 mb-3 text-md leading-relaxed text-ink-700">{log.description || log.details || t("No details recorded")}</p>

            {Boolean(log.old_values || log.new_values) && <Diff log={log} formatDiffVal={formatDiffVal} />}

            {raw && <pre className="mb-3 overflow-x-auto rounded-md bg-ink-900 px-4 py-3 font-mono text-sm leading-snug text-ink-50">{JSON.stringify(log, null, 2)}</pre>}

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-ink-100 pt-2.5 text-sm text-text-secondary">
              <div className="flex flex-wrap items-center gap-4">
                <Meta icon={Database}>{t("Ref: #")}{log.entityId || log.recordId || "N/A"}</Meta>
                <Meta icon={Globe}>{t("IP:")}{" "}{log.ipAddress || t("Local / System")}</Meta>
                <Meta icon={Calendar}>{formatFullDateTime(log.timestamp)}</Meta>
              </div>
              <Button variant="ghost" size="sm" aria-expanded={raw} onClick={() => toggleRawData(log.id)} title={t("Toggle technical audit JSON")}>
                <Code className="size-3" aria-hidden="true" /> {raw ? t("Hide raw") : t("Raw JSON")}
                {raw ? <ChevronUp className="size-3" aria-hidden="true" /> : <ChevronDown className="size-3" aria-hidden="true" />}
              </Button>
            </div>
          </Card>
        </li>
      );
    })}
  </ol>
);

export default AuditTrailAuditTimeline;
