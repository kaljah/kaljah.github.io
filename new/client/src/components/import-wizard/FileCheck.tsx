import React from "react";
import { Loader } from "lucide-react";
import { Banner, Button } from "../../ui";
import SkipGroupList, { type SkipGroup } from "../SkipGroupList";
import { t } from "../../i18n";

// "Check the file" step of the import wizard: POST /api/emissions/upload/check calculates a sample of rows
// spread over the file exactly as the import would, counts every row and saves nothing.

interface NamedCount {
  name: string;
  rows: number;
  known?: boolean;
  scope2?: boolean;
}

export interface FileCheckPreview {
  rows: number;
  checked: number;
  is_estimate?: boolean;
  estimated_ok: number;
  estimated_skipped: number;
  period?: { from?: string; to?: string; months?: number; unreadable_rows?: number };
  facilities?: NamedCount[];
  processes?: NamedCount[];
  unknown_facility_rows?: number;
  unknown_process_rows?: number;
  scope2_rows?: number;
  example_rows?: number;
  columns?: { total: number; headers?: string[]; matched: string[]; by_name: string[] };
}

export interface FileCheckState {
  loading: boolean;
  error: string;
  stale: boolean;
  data: { preview: FileCheckPreview; skipped_groups?: SkipGroup[] } | null;
}

export const EMPTY_CHECK: FileCheckState = { loading: false, error: "", stale: false, data: null };

const fmt = (n?: number) => Number(n || 0).toLocaleString("en-US");
const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

const Warn: React.FC<{ children: React.ReactNode }> = ({ children }) => <p className="m-0 text-sm text-warning-fg">{children}</p>;

export const FileCheckPanel: React.FC<{ check: FileCheckState; onRecheck: () => void; canRun: boolean; mappedHere?: number }> = ({
  check,
  onRecheck,
  canRun,
  mappedHere,
}) => {
  if (check.loading) {
    return (
      <div role="status" className="flex items-center gap-2 rounded-md border border-border bg-ink-50 px-4 py-3 text-sm text-text-secondary">
        <Loader className="size-4 animate-spin" aria-hidden="true" />{" "}{t("Checking your file… a sample of rows spread over the file is calculated exactly as the import would; nothing is saved.")}
      </div>
    );
  }
  if (check.error) {
    return (
      <Banner tone="danger">
        <strong>{t("The file could not be checked:")}</strong> {check.error}{" "}
        <Button variant="link" size="sm" className="h-auto px-0" onClick={onRecheck}>
          {t("Check again")}
        </Button>
      </Banner>
    );
  }
  if (!check.data) {
    return (
      <p className="m-0 rounded-md border border-border bg-ink-50 px-4 py-3 text-sm text-text-secondary">
        {canRun ? (
          <>
            <Button variant="link" size="sm" className="h-auto px-0" onClick={onRecheck}>
              {t("Check the file")}
            </Button>{" "}
            {t("before importing (nothing is saved).")}
          </>
        ) : (
          t("Map the required fields below; the file is then checked before anything is saved.")
        )}
      </p>
    );
  }
  const p = check.data.preview;
  const groups = check.data.skipped_groups || [];
  const scale = p.checked ? p.rows / p.checked : 1;
  const approx = p.is_estimate ? "≈ " : "";
  const facilities = p.facilities || [];
  const processes = p.processes || [];
  const unknownFac = facilities.filter((f) => !f.known);
  const unknownProc = processes.filter((x) => !x.known && !x.scope2);
  const scope2Proc = processes.filter((x) => x.scope2);
  const list = (items: NamedCount[]) => items.slice(0, 5).map((x) => `${x.name} (${fmt(x.rows)})`).join(", ") + (items.length > 5 ? " …" : "");
  return (
    <section aria-label={t("File check")} className="flex flex-col gap-2 rounded-md border border-border bg-ink-50 p-4">
      {check.stale && (
        <Banner tone="warning">
          {t("Options or mapping changed since this check.")}{" "}
          <Button variant="link" size="sm" className="h-auto px-0" onClick={onRecheck}>
            {t("Check again")}
          </Button>
        </Banner>
      )}
      <p className="m-0 text-base font-semibold text-text">{t("File check")}</p>
      <p className="m-0 text-sm text-text-secondary">
        {fmt(p.rows)}{" "}{t("rows")}
        {p.period?.from && (
          <>
            {" "}
            · {p.period.from}{" "}{t("to")}{" "}{p.period.to} ({p.period.months} {plural(p.period.months || 0, "month", "months")})
          </>
        )}{" "}
        · {fmt(facilities.length)} {plural(facilities.length, "facility", "facilities")} · {fmt(processes.length)}{" "}
        {plural(processes.length, "process type", "process types")}
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        <p className="m-0 rounded-md bg-success-bg px-3 py-2 text-sm text-success-fg">
          <strong className="text-lg tabular-nums">
            {approx}
            {fmt(p.estimated_ok)}
          </strong>{" "}
          {t("rows will be imported")}
        </p>
        <p className={`m-0 rounded-md px-3 py-2 text-sm ${p.estimated_skipped ? "bg-warning-bg text-warning-fg" : "bg-surface text-text-secondary"}`}>
          <strong className="text-lg tabular-nums">
            {approx}
            {fmt(p.estimated_skipped)}
          </strong>{" "}
          {t("rows will be skipped")}
        </p>
      </div>
      {p.is_estimate && <p className="m-0 text-xs text-text-secondary">{t("Estimated from")}{" "}{fmt(p.checked)}{" "}{t("rows spread over the file; the import checks every row.")}</p>}
      {unknownFac.length > 0 && (
        <Warn>
          <strong>{fmt(p.unknown_facility_rows)}{" "}{t("rows name a facility that is not in the platform or not in your regions:")}</strong> {list(unknownFac)}
        </Warn>
      )}
      {unknownProc.length > 0 && (
        <Warn>
          <strong>{fmt(p.unknown_process_rows)}{" "}{t("rows have a process type that is not recognised:")}</strong> {list(unknownProc)}
        </Warn>
      )}
      {scope2Proc.length > 0 && (
        <Warn>
          <strong>{fmt(p.scope2_rows)}{" "}{t("rows are Scope 2 (purchased energy):")}</strong> {list(scope2Proc)}{t(". Import them with the Scope 2 template.")}
        </Warn>
      )}
      {(p.example_rows || 0) > 0 && (
        <Warn>
          <strong>{fmt(p.example_rows)}{" "}{t("example rows from the template")}</strong>{" "}{t("(dated EXAMPLE) will not be imported. Delete them, or replace EXAMPLE with the real month to keep a row.")}
        </Warn>
      )}
      {(p.period?.unreadable_rows || 0) > 0 && (
        <Warn>
          <strong>{fmt(p.period?.unreadable_rows)}{" "}{t("rows have a missing or unreadable date.")}</strong>
        </Warn>
      )}
      {groups.length > 0 && (
        <>
          <p className="m-0 mt-1 text-sm font-semibold text-text">{t("Why rows would be skipped")}{p.is_estimate ? t(" (scaled from the sample)") : ""}</p>
          <SkipGroupList groups={groups} scale={scale} approx={p.is_estimate} limit={6} />
        </>
      )}
      {p.columns && (
        <p className="m-0 text-xs text-text-secondary">
          {p.columns.matched.length}{" "}{t("of")}{" "}{p.columns.total}{" "}{t("columns are matched to fields")}
          {/* the mapping step counts only what it matched; the server also recognises some headers itself (SU-11) */}
          {mappedHere != null && p.columns.matched.length > mappedHere
            ? ` (${mappedHere} mapped above, ${p.columns.matched.length - mappedHere} more recognised by their header)`
            : ""}
          .
          {p.columns.by_name.length > 0 && (
            <>
              {" "}
              {t("The other")}{" "}{p.columns.by_name.length}{" "}{t("are read by their name when a calculation needs them (for example c1, gor, hhv) and ignored otherwise.")}
            </>
          )}
        </p>
      )}
    </section>
  );
};
