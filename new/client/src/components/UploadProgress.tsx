import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, CircleAlert, CircleCheck, ChevronRight, Download, Loader, TriangleAlert, XCircle, type LucideIcon } from "lucide-react";
import { Badge, Banner, Button, Card, type BadgeProps } from "../ui";
import { cn } from "../ui/cn";
import { useAuth } from "../context/AuthContext";
import api from "../api";
import { useToast } from "./Toast";
import SkipGroupList, { type SkipGroup } from "./SkipGroupList";
import { t } from "../i18n";

export interface SkippedRow {
  row?: number;
  reason?: string;
  year?: number | string;
  month?: number | string;
  date?: string;
  facility?: string;
  process?: string;
  fuel?: string;
  quantity?: number | string;
}

export interface AnomalyItem {
  row?: number;
  facility_id?: string;
  value?: number;
  z_score?: number;
  expected_range?: [number, number];
  message?: string;
}

export interface UploadProgressProps {
  jobId: string | number;
  onComplete?: () => void;
  onCancel?: () => void;
  reviewable?: boolean;
}

interface CategoryRule {
  test: (r: string) => boolean;
  label: string;
  tone: NonNullable<BadgeProps["tone"]>;
}

/* Skipped-row reasons are bucketed into categories so a long list can be filtered. */
const CATEGORIES: CategoryRule[] = [
  { test: (r) => r.includes("duplicate"), label: t("Duplicate"), tone: "warning" },
  { test: (r) => r.includes("access denied") || r.includes("permission"), label: t("Access Denied"), tone: "danger" },
  { test: (r) => r.includes("facility") || r.includes("region"), label: t("Region"), tone: "info" },
  { test: (r) => r.includes("date") || r.includes("year"), label: t("Date"), tone: "info" },
  { test: (r) => r.includes("factor"), label: t("Factor"), tone: "brand" },
  { test: (r) => r.includes("quantity"), label: t("Quantity"), tone: "neutral" },
  { test: (r) => r.includes("process"), label: t("Process"), tone: "neutral" },
  { test: (r) => r.includes("calculation"), label: t("Calculation"), tone: "brand" },
];

function categoryFromReason(reason = ""): { label: string; tone: NonNullable<BadgeProps["tone"]> } {
  const r = reason.toLowerCase();
  return CATEGORIES.find((c) => c.test(r)) ?? { label: t("Other"), tone: "neutral" };
}

function formatEta(sec: number): string {
  if (sec < 60) return `${Math.max(1, Math.round(sec))} s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min ${s.toString().padStart(2, "0")} s`;
}

const th = "sticky top-0 whitespace-nowrap border-b border-border bg-ink-50 px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-text-secondary";
const td = "max-w-[120px] truncate border-b border-ink-100 px-3 py-2 text-text-secondary";
const mono = "text-center font-mono font-semibold text-ink-700";

interface TableProps {
  head: string[];
  children: React.ReactNode;
}

const Table: React.FC<TableProps> = ({ head, children }) => (
  <div className="max-h-[400px] overflow-auto">
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr>
          {head.map((h) => (
            <th key={h} scope="col" className={th}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  </div>
);

interface StatProps {
  icon: LucideIcon;
  value: number;
  label: string;
  tone?: "success" | "warning";
}

const Stat: React.FC<StatProps> = ({ icon: Icon, value, label, tone }) => (
  <div className="flex items-center gap-4 rounded-md border border-border bg-ink-50 p-5">
    <span className={cn("flex size-12 shrink-0 items-center justify-center rounded-md bg-ink-100 text-text-secondary", tone === "success" && "bg-success-bg text-success-fg", tone === "warning" && "bg-warning-bg text-warning-fg")}>
      <Icon className="size-6" aria-hidden="true" />
    </span>
    <div>
      <p className="m-0 text-xl font-bold leading-none tabular-nums text-text">{value.toLocaleString()}</p>
      <p className="m-0 mt-0.5 text-base font-medium text-text-secondary">{label}</p>
    </div>
  </div>
);

interface DisclosureProps {
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  className?: string;
}

const Disclosure: React.FC<DisclosureProps> = ({ open, onToggle, children, className }) => (
  <button
    type="button"
    aria-expanded={open}
    onClick={onToggle}
    className={cn("flex flex-1 cursor-pointer items-center gap-2 border-0 bg-transparent px-4 py-3 text-left text-base font-semibold hover:bg-ink-100", className)}
  >
    <ChevronRight className={cn("size-4 shrink-0 transition-transform", open && "rotate-90")} aria-hidden="true" />
    {children}
  </button>
);

interface SkippedRowsProps {
  skippedCount: number;
  skippedPreview: SkippedRow[];
  hasErrorCsv: boolean;
  onDownload: () => void;
}

const SkippedRows: React.FC<SkippedRowsProps> = ({ skippedCount, skippedPreview, hasErrorCsv, onDownload }) => {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("all");
  const labels = ["all", ...new Set(skippedPreview.map((r) => categoryFromReason(r.reason).label))];
  const rows = filter === "all" ? skippedPreview : skippedPreview.filter((r) => categoryFromReason(r.reason).label === filter);

  return (
    <div className="mb-6 overflow-hidden rounded-md border border-border">
      <div className="flex w-full items-center bg-ink-50">
        <Disclosure open={open} onToggle={() => setOpen((v) => !v)} className="text-text">
          <span>{t("Row details")}{skippedCount > 100 ? t(" (first 100)") : ""}</span>
        </Disclosure>
        {hasErrorCsv && (
          <Button variant="secondary" size="sm" className="mr-3" onClick={onDownload}>
            <Download className="size-4" aria-hidden="true" />{" "}{t("Download all")}{" "}{skippedCount.toLocaleString("en-US")}{" "}{t("skipped rows (CSV)")}
          </Button>
        )}
      </div>
      {open && (
        <div className="bg-surface">
          {labels.length > 2 && (
            <div className="flex flex-wrap gap-2 border-b border-border bg-ink-50 px-5 py-4">
              {labels.map((label) => (
                <Button key={label} size="sm" variant={filter === label ? "primary" : "secondary"} aria-pressed={filter === label} onClick={() => setFilter(label)}>
                  {label === "all" ? t("All ({{count}})", { count: skippedPreview.length }) : label}
                </Button>
              ))}
            </div>
          )}
          <Table head={[t("Row #"), t("Category"), t("Reason"), t("Year"), t("Month"), t("Facility"), t("Process"), t("Fuel"), t("Quantity")]}>
            {rows.map((row, i) => {
              const cat = categoryFromReason(row.reason);
              return (
                <tr key={i} className="hover:bg-ink-50">
                  <td className={cn(td, "w-[60px] font-mono")}>{row.row}</td>
                  <td className={td}>
                    <Badge tone={cat.tone}>{cat.label}</Badge>
                  </td>
                  <td className={cn(td, "max-w-[250px] whitespace-normal font-medium leading-snug text-danger-fg")}>{row.reason}</td>
                  <td className={cn(td, mono)}>{row.year || (row.date ? row.date.split("-")[0] : "—")}</td>
                  <td className={cn(td, mono)}>{row.month || (row.date ? row.date.split("-")[1] : "—")}</td>
                  <td className={td}>{row.facility || "—"}</td>
                  <td className={td}>{row.process || "—"}</td>
                  <td className={td}>{row.fuel || "—"}</td>
                  <td className={td}>{row.quantity || "—"}</td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="p-8 text-center text-text-secondary">
                  {t("No rows match this filter.")}
                </td>
              </tr>
            )}
          </Table>
        </div>
      )}
    </div>
  );
};

interface AnomaliesProps {
  anomalies: AnomalyItem[];
  count: number;
}

const Anomalies: React.FC<AnomaliesProps> = ({ anomalies, count }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-6 overflow-hidden rounded-md border border-amber-500/30 bg-warning-bg">
      <Disclosure open={open} onToggle={() => setOpen((v) => !v)} className="w-full text-warning-fg hover:bg-amber-100/60">
        <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
        <span className="flex-1">
          {Number(count).toLocaleString("en-US")}{" "}{t("statistical")}{" "}{count !== 1 ? t("anomalies") : t("anomaly")}{" "}{t("detected — click to review")}
        </span>
      </Disclosure>
      {open && (
        <div className="border-t border-amber-500/30 p-4">
          <p className="m-0 mb-3 text-base leading-snug text-warning-fg">
            {t("These rows were imported but differ strongly from the same source (equipment, else fuel) at this facility over the previous 12 months. Check them before approving.")}
          </p>
          <Table head={[t("Row #"), t("Facility"), t("Value (tCO2e)"), t("Z-Score"), t("Expected Range"), t("Details")]}>
            {anomalies.map((a, i) => (
              <tr key={i} className="bg-surface/60">
                <td className={cn(td, "w-[60px] font-mono")}>{a.row}</td>
                <td className={td}>{a.facility_id || "—"}</td>
                <td className={cn(td, "font-semibold text-warning-fg")}>{typeof a.value === "number" ? a.value.toFixed(2) : a.value}</td>
                <td className={td}>{a.z_score != null ? `±${Math.abs(a.z_score).toFixed(1)}σ` : "—"}</td>
                <td className={td}>{a.expected_range ? `${a.expected_range[0].toFixed(1)} – ${a.expected_range[1].toFixed(1)}` : "—"}</td>
                <td className={cn(td, "max-w-[250px] whitespace-normal text-xs font-medium leading-snug text-danger-fg")}>{a.message || t("Statistical outlier")}</td>
              </tr>
            ))}
          </Table>
        </div>
      )}
    </div>
  );
};

// reviewable: the import creates emission records that wait for approval (Scope 1 / 2 / 3)
const UploadProgress: React.FC<UploadProgressProps> = ({ jobId, onComplete, onCancel, reviewable = true }) => {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const isReviewer = ["admin", "superuser"].includes(user?.role || "");

  const [status, setStatus] = useState<string>("processing");
  const [progress, setProgress] = useState<number>(0);
  const [processed, setProcessed] = useState<number>(0);
  const [total, setTotal] = useState<number>(0);
  const [errors, setErrors] = useState<string[]>([]);
  const [skippedCount, setSkippedCount] = useState<number>(0);
  const [skippedPreview, setSkippedPreview] = useState<SkippedRow[]>([]);
  const [hasErrorCsv, setHasErrorCsv] = useState<boolean>(false);
  const [anomalyCount, setAnomalyCount] = useState<number>(0);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [skipGroups, setSkipGroups] = useState<SkipGroup[]>([]);
  // rate measured from the first progress sample this screen saw (the job may have started earlier)
  const rateStart = useRef<{ t: number; n: number } | null>(null);
  const [eta, setEta] = useState<number | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.get<{
          status: string;
          progress?: number;
          processed?: number;
          total?: number;
          errors?: string[];
          skipped_count?: number;
          skipped_preview?: SkippedRow[];
          has_error_csv?: boolean;
          error_csv_path?: string;
          anomaly_count?: number;
          anomalies?: AnomalyItem[];
          skipped_groups?: SkipGroup[];
        }>(`/emissions/upload/status/${jobId}`);
        const data = res.data;
        setStatus(data.status);
        setProgress(data.progress || 0);
        setProcessed(data.processed || 0);
        setTotal(data.total || 0);
        setErrors(data.errors || []);
        setSkippedCount(data.skipped_count || 0);
        setSkippedPreview(data.skipped_preview || []);
        setHasErrorCsv(!!(data.has_error_csv ?? data.error_csv_path));
        setAnomalyCount(data.anomaly_count || 0);
        setAnomalies(data.anomalies || []);
        setSkipGroups(data.skipped_groups || []);
        const now = Date.now();
        if (!rateStart.current) rateStart.current = { t: now, n: data.processed || 0 };
        const doneRows = (data.processed || 0) - rateStart.current.n;
        const secs = (now - rateStart.current.t) / 1000;
        if ((data.total || 0) > 0 && doneRows > 0 && secs >= 3) {
          setEta(Math.max(0, (((data.total || 0) - (data.processed || 0)) * secs) / doneRows));
        }
        if (data.status === "completed" || data.status === "error") clearInterval(interval);
      } catch (err) {
        console.error("Upload status poll failed", err);
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [jobId]);

  const downloadErrors = async () => {
    try {
      const res = await api.get(`/emissions/upload/errors/${jobId}`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `skipped_rows_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      toast.error(t("Failed to download error CSV."));
    }
  };

  const done = () => onComplete?.();

  return (
    <div className="mx-auto w-full max-w-[900px] text-text">
      {status === "processing" && (
        <Card>
          <div className="mb-6 flex items-center gap-4">
            <Loader className="size-8 shrink-0 animate-spin text-brand-700" aria-hidden="true" />
            <div>
              <p className="m-0 mb-1 text-md font-semibold text-text">{t("Importing your file…")}</p>
              <p className="m-0 text-base text-text-secondary">
                {t("You can close this window: the import keeps running on the server. The file is saved in one go when every row is done, so its records appear together at the end.")}
              </p>
            </div>
          </div>
          <div role="progressbar" aria-label={t("Import progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} className="mb-3 h-2 w-full overflow-hidden rounded-sm bg-ink-100">
            <div className="h-full rounded-sm bg-brand-500 transition-[width] duration-300 ease-out" style={{ width: `${progress}%` }} />
          </div>
          <div className="flex justify-between text-base font-medium text-text-secondary">
            <span className="font-semibold text-brand-700">{progress}%</span>
            <span>
              {processed.toLocaleString("en-US")}
              {total > 0 ? ` of ${total.toLocaleString("en-US")}` : ""}{" "}{t("rows")}
              {eta != null && progress < 99 ? ` · about ${formatEta(eta)} left` : ""}
              {progress >= 99 && processed >= total && total > 0 ? t(" · saving…") : ""}
            </span>
          </div>
          {skippedCount > 0 && (
            <Banner tone="warning" className="mt-4">
              {skippedCount.toLocaleString()}{" "}{t("rows skipped so far")}
            </Banner>
          )}
        </Card>
      )}

      {status === "completed" && (
        <Card>
          <div className="mb-6 grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
            <Stat icon={CircleCheck} tone="success" value={processed - skippedCount} label={t("Rows Imported")} />
            <Stat icon={TriangleAlert} tone={skippedCount > 0 ? "warning" : undefined} value={skippedCount} label={t("Rows Skipped")} />
            <Stat icon={CircleCheck} value={processed} label={t("Total Processed")} />
          </div>

          {skippedCount > 0 && skipGroups.length > 0 && (
            <div className="mb-4 rounded-md border border-border bg-ink-50 p-4">
              <p className="m-0 mb-1 text-base font-semibold text-text">
                {skippedCount === 1 ? t("Why 1 row was skipped") : t("Why {{count}} rows were skipped", { count: skippedCount.toLocaleString("en-US") })}
              </p>
              <p className="m-0 mb-3 text-sm text-text-secondary">
                {t("Fix these in your file and upload only the skipped rows again: the downloadable CSV holds them with their original columns (its first column, the reason, is ignored on upload).")}
              </p>
              <SkipGroupList groups={skipGroups} limit={10} />
            </div>
          )}
          {skippedCount > 0 && <SkippedRows skippedCount={skippedCount} skippedPreview={skippedPreview} hasErrorCsv={hasErrorCsv} onDownload={downloadErrors} />}
          {anomalyCount > 0 && <Anomalies anomalies={anomalies} count={anomalyCount} />}

          {reviewable && processed - skippedCount > 0 && (
            <Banner tone="info" className="mb-2">
              <strong>{t("What happens next:")}</strong>{" "}
              {processed - skippedCount === 1 ? t("the imported record is") : t("the {{count}} imported records are", { count: (processed - skippedCount).toLocaleString("en-US") })}{" "}
              <em>{t("Pending")}</em>.{" "}
              {isReviewer ? t("Review and approve them in Manage Data › Pending Review.") : t("An admin or superuser reviews and approves them.")}{" "}{t("Pending records do not count in dashboards and reports until they are approved.")}
            </Banner>
          )}

          <div className="mt-6 flex items-center justify-end gap-3">
            {isReviewer ? (
              <>
                <Button variant="secondary" onClick={done}>
                  {t("Close")}
                </Button>
                {reviewable && (
                  <Button
                    onClick={() => {
                      done();
                      navigate("/manage-data", { state: { tab: "pending" } });
                    }}
                  >
                    {t("Review Pending Records")}{" "}<ArrowRight className="size-4" aria-hidden="true" />
                  </Button>
                )}
              </>
            ) : (
              <Button onClick={done}>{t("Close & View Inventory")}</Button>
            )}
          </div>
        </Card>
      )}

      {status === "error" && (
        <Card>
          <div className="mb-5 flex items-start gap-4">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-danger-bg text-danger-fg">
              <XCircle className="size-6" aria-hidden="true" />
            </span>
            <div>
              <p className="m-0 mb-1 text-md font-semibold text-danger-fg">{t("Upload Failed")}</p>
              <p className="m-0 text-base text-text-secondary">{t("A fatal error occurred while processing the file.")}</p>
            </div>
          </div>
          <div role="alert" className="mb-6 max-h-[200px] overflow-y-auto rounded-md border border-border bg-ink-50 p-4 font-mono text-sm text-ink-700">
            {errors.map((e, i) => (
              <div key={i} className="mb-2 flex items-start gap-2 leading-snug last:mb-0">
                <CircleAlert className="mt-0.5 size-3.5 shrink-0 text-danger-fg" aria-hidden="true" />
                {e}
              </div>
            ))}
          </div>
          <Button variant="secondary" onClick={onCancel}>
            {t("Go Back")}
          </Button>
        </Card>
      )}
    </div>
  );
};

export default UploadProgress;
