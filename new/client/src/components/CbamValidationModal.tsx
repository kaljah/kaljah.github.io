import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Copy, Download, FileCode, ShieldCheck, XCircle } from "lucide-react";
import api from "../api";
import { Badge, Button, Dialog, NativeSelect } from "../ui";
import { useToast } from "./Toast";
import { t } from "../i18n";
import type { CbamQuarter, CbamValidationReport } from "../types/reports";

export interface CbamValidationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  year?: string | number;
  quarter: CbamQuarter | string;
  onQuarterChange?: (q: CbamQuarter) => void;
  facilityId?: string | number;
  status?: string;
  initialTab?: "validation" | "xml";
  onExportXml?: (quarterOverride?: CbamQuarter | string) => void;
}

const QUARTER_OPTIONS: { value: CbamQuarter; label: string }[] = [
  { value: "Q1-Q4", label: "Full Year (Q1–Q4)" },
  { value: "Q1", label: "Q1 (Jan–Mar)" },
  { value: "Q2", label: "Q2 (Apr–Jun)" },
  { value: "Q3", label: "Q3 (Jul–Sep)" },
  { value: "Q4", label: "Q4 (Oct–Dec)" },
];

export const CbamValidationModal: React.FC<CbamValidationModalProps> = ({
  open,
  onOpenChange,
  year,
  quarter,
  onQuarterChange,
  facilityId,
  status = "Verified",
  initialTab = "validation",
  onExportXml,
}) => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<"validation" | "xml">(initialTab);
  const [localQuarter, setLocalQuarter] = useState<string>(quarter || "Q1-Q4");
  const [loading, setLoading] = useState(false);
  const [xmlLoading, setXmlLoading] = useState(false);
  const [report, setReport] = useState<CbamValidationReport | null>(null);
  const [xmlPreview, setXmlPreview] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    setLocalQuarter(quarter || "Q1-Q4");
  }, [quarter]);

  useEffect(() => {
    if (open) {
      setActiveTab(initialTab);
    }
  }, [open, initialTab]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const params: Record<string, string> = {
      quarter: localQuarter || "Q1-Q4",
      status,
    };
    if (year && String(year) !== "all") params.year = String(year);
    if (facilityId && String(facilityId) !== "all") params.facility_id = String(facilityId);

    const loadAll = async () => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const res = await api.get("/reports/cbam-validate", { params });
        if (!cancelled && res.data && typeof res.data === "object" && !Array.isArray(res.data)) {
          setReport(res.data as CbamValidationReport);
        }
      } catch (err: any) {
        if (!cancelled) {
          setErrorMsg(err?.response?.data?.error || t("Failed to run CBAM pre-export validation."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    const loadXml = async () => {
      setXmlLoading(true);
      try {
        const res = await api.get("/reports/cbam-export", {
          params: { ...params, format: "xml" },
          responseType: "text",
        });
        if (!cancelled) {
          setXmlPreview(typeof res.data === "string" ? res.data : JSON.stringify(res.data, null, 2));
        }
      } catch {
        if (!cancelled) setXmlPreview("");
      } finally {
        if (!cancelled) setXmlLoading(false);
      }
    };

    loadAll();
    loadXml();
    return () => {
      cancelled = true;
    };
  }, [open, year, localQuarter, facilityId, status]);

  const handleQuarterSelect = (val: string) => {
    setLocalQuarter(val);
    if (onQuarterChange) onQuarterChange(val as CbamQuarter);
  };

  const handleCopyXml = async () => {
    if (!xmlPreview) return;
    try {
      await navigator.clipboard.writeText(xmlPreview);
      toast.success(t("CBAM XML copied to clipboard."));
    } catch {
      toast.error(t("Clipboard copy is unavailable in this browser context."));
    }
  };

  const summary = report?.summary;
  const checks = Array.isArray(report?.checks) ? report.checks : [];
  const errors = Array.isArray(report?.errors) ? report.errors : [];
  const warnings = Array.isArray(report?.warnings) ? report.warnings : [];
  const records = Array.isArray(report?.records) ? report.records : [];

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      maxWidth="62rem"
      title={
        <span className="inline-flex items-center gap-2">
          <ShieldCheck className="size-5 text-brand-600" aria-hidden="true" />
          <span>{t("EU CBAM Transitional Registry Validation & XML Inspector")}</span>
        </span>
      }
      description={t(
        "Implementing Regulation (EU) 2023/1773 completeness checks, Gross/CCS/Net embedded emissions audit, and live XML preview."
      )}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-3 w-full">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            {report?.assurance_level && (
              <span>
                {t("Assurance Level")}: <strong className="text-text">{report.assurance_level}</strong>
              </span>
            )}
            {report?.period_start && report?.period_end && (
              <span>
                • {report.period_start} → {report.period_end}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              {t("Close")}
            </Button>
            {onExportXml && (
              <Button variant="primary" onClick={() => onExportXml(localQuarter)} className="gap-1.5">
                <Download className="size-4" aria-hidden="true" />
                {t("Download CBAM XML")}
              </Button>
            )}
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {/* Top Controls & Status Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-ink-50 p-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <label htmlFor="cbam-modal-quarter" className="text-xs font-semibold text-text-secondary">
              {t("Reporting Quarter")}
            </label>
            <NativeSelect
              id="cbam-modal-quarter"
              value={localQuarter}
              onChange={(e) => handleQuarterSelect(e.target.value)}
              className="h-8 w-44 rounded-md border border-border bg-surface px-2.5 text-sm text-text"
            >
              {QUARTER_OPTIONS.map((q) => (
                <option key={q.value} value={q.value}>
                  {t(q.label)}
                </option>
              ))}
            </NativeSelect>
            {report && (
              <Badge tone={report.ready ? "success" : "danger"} className="px-2.5 py-1 text-xs font-semibold">
                {report.ready ? t("Ready for Submission") : t("Validation Issues Detected")}
              </Badge>
            )}
          </div>

          <div className="inline-flex rounded-md border border-border bg-surface p-0.5">
            <button
              type="button"
              onClick={() => setActiveTab("validation")}
              className={`px-3 py-1 text-xs font-semibold rounded border-0 cursor-pointer transition-colors ${
                activeTab === "validation" ? "bg-brand-600 text-white" : "bg-transparent text-text-secondary hover:text-text"
              }`}
            >
              {t("Validation Checklist")} ({report?.record_count ?? records.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("xml")}
              className={`px-3 py-1 text-xs font-semibold rounded border-0 cursor-pointer transition-colors inline-flex items-center gap-1 ${
                activeTab === "xml" ? "bg-brand-600 text-white" : "bg-transparent text-text-secondary hover:text-text"
              }`}
            >
              <FileCode className="size-3.5" aria-hidden="true" />
              {t("XML Preview")}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="rounded-md border border-danger-300 bg-danger-50 p-3 text-sm text-danger-800">{errorMsg}</div>
        )}

        {loading && !report ? (
          <div className="py-10 text-center text-sm text-text-secondary">{t("Running EU CBAM validation checks...")}</div>
        ) : activeTab === "validation" ? (
          <div className="flex flex-col gap-4">
            {/* Summary Metrics */}
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-md border border-border bg-surface p-3">
                  <div className="text-xs text-text-secondary">{t("Export Volume")}</div>
                  <div className="mt-1 text-lg font-bold font-mono text-text">
                    {Number(summary.total_quantity_tonnes || 0).toLocaleString("en-US")} t
                  </div>
                </div>
                <div className="rounded-md border border-border bg-surface p-3">
                  <div className="text-xs text-text-secondary">{t("Total Embedded CO₂e")}</div>
                  <div className="mt-1 text-lg font-bold font-mono text-brand-700">
                    {Number(summary.total_embedded_emissions_tco2e || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })} t
                  </div>
                </div>
                <div className="rounded-md border border-border bg-surface p-3">
                  <div className="text-xs text-text-secondary">{t("CCS Deducted")}</div>
                  <div className="mt-1 text-lg font-bold font-mono text-emerald-700">
                    -{Number(summary.total_captured_co2_tonnes || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })} t
                  </div>
                </div>
                <div className="rounded-md border border-border bg-surface p-3">
                  <div className="text-xs text-text-secondary">{t("Origin Carbon Price")}</div>
                  <div className="mt-1 text-lg font-bold font-mono text-amber-700">
                    €{Number(summary.total_carbon_price_paid_eur || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            )}

            {/* Compliance Checklist */}
            {checks.length > 0 && (
              <div className="rounded-md border border-border bg-surface">
                <div className="border-b border-border px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-text-secondary">
                  {t("EU 2023/1773 Pre-Export Validation Checks")}
                </div>
                <div className="divide-y divide-border/70">
                  {checks.map((chk) => (
                    <div key={chk.id} className="flex items-start gap-3 px-4 py-2.5 text-sm">
                      {chk.status === "pass" ? (
                        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
                      ) : chk.status === "warning" ? (
                        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden="true" />
                      ) : (
                        <XCircle className="mt-0.5 size-4 shrink-0 text-red-600" aria-hidden="true" />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-text">{chk.label}</div>
                        <div className="text-xs text-text-secondary">{chk.detail}</div>
                      </div>
                      <Badge
                        tone={chk.status === "pass" ? "success" : chk.status === "warning" ? "warning" : "danger"}
                        className="text-[0.65rem]"
                      >
                        {chk.status.toUpperCase()}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Errors & Warnings */}
            {(errors.length > 0 || warnings.length > 0) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {errors.length > 0 && (
                  <div className="rounded-md border border-red-200 bg-red-50/70 p-3">
                    <div className="mb-1.5 text-xs font-bold uppercase text-red-800">
                      {t("Blocking Errors")} ({errors.length})
                    </div>
                    <ul className="m-0 list-disc ps-4 text-xs text-red-900 space-y-1">
                      {errors.map((e, i) => (
                        <li key={i}>
                          <strong>{e.field}</strong>: {e.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {warnings.length > 0 && (
                  <div className="rounded-md border border-amber-200 bg-amber-50/70 p-3">
                    <div className="mb-1.5 text-xs font-bold uppercase text-amber-800">
                      {t("Advisories")} ({warnings.length})
                    </div>
                    <ul className="m-0 list-disc ps-4 text-xs text-amber-900 space-y-1">
                      {warnings.map((w, i) => (
                        <li key={i}>
                          <strong>{w.field}</strong>: {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Gross / CCS / Net / Precursor Table */}
            {records.length > 0 && (
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr className="bg-ink-50 text-start text-text-secondary border-b border-border">
                      <th className="px-3 py-2 font-semibold">{t("Good / CN")}</th>
                      <th className="px-3 py-2 font-semibold">{t("Period")}</th>
                      <th className="px-3 py-2 font-semibold text-end">{t("Gross SEE")}</th>
                      <th className="px-3 py-2 font-semibold text-end">{t("CCS Ded.")}</th>
                      <th className="px-3 py-2 font-semibold text-end">{t("Net Direct")}</th>
                      <th className="px-3 py-2 font-semibold text-end">{t("Indirect")}</th>
                      <th className="px-3 py-2 font-semibold text-end">{t("Precursor")}</th>
                      <th className="px-3 py-2 font-semibold text-end">{t("Total (tCO₂e)")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/70">
                    {records.map((r) => (
                      <tr key={r.id}>
                        <td className="px-3 py-2">
                          <div className="font-semibold text-text">{r.product_name}</div>
                          <div className="font-mono text-[0.7rem] text-text-secondary">
                            {r.cn_code} • {r.facility_name}
                          </div>
                        </td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {r.year} {r.quarter}
                        </td>
                        <td className="px-3 py-2 text-end font-mono">{Number(r.gross_direct_see).toFixed(4)}</td>
                        <td className="px-3 py-2 text-end font-mono text-emerald-700">
                          {r.ccs_reduction_see > 0 ? `-${Number(r.ccs_reduction_see).toFixed(4)}` : "—"}
                        </td>
                        <td className="px-3 py-2 text-end font-mono font-semibold">{Number(r.net_direct_see).toFixed(4)}</td>
                        <td className="px-3 py-2 text-end font-mono">{Number(r.indirect_see).toFixed(4)}</td>
                        <td className="px-3 py-2 text-end font-mono text-blue-700">
                          {r.precursor_see > 0 ? `+${Number(r.precursor_see).toFixed(4)}` : "—"}
                        </td>
                        <td className="px-3 py-2 text-end font-mono font-bold">
                          {Number(r.total_embedded_tco2e).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-text-secondary">
                {t("DG TAXUD CBAM Transitional Registry XML Payload")}
              </span>
              <Button size="sm" variant="secondary" onClick={handleCopyXml} disabled={!xmlPreview} className="gap-1.5">
                <Copy className="size-3.5" aria-hidden="true" />
                {t("Copy XML")}
              </Button>
            </div>
            {xmlLoading ? (
              <div className="py-10 text-center text-sm text-text-secondary">{t("Generating XML preview...")}</div>
            ) : (
              <pre className="m-0 max-h-[420px] overflow-auto rounded-md border border-border bg-ink-900 p-4 font-mono text-xs text-ink-50 leading-relaxed">
                {xmlPreview || t("No XML preview generated for the selected filters.")}
              </pre>
            )}
          </div>
        )}
      </div>
    </Dialog>
  );
};

export default CbamValidationModal;
