import React, { useEffect, useState } from "react";
import axios from "axios";
import Modal from "./Modal";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { t } from "../i18n";
import { Search, FileText, CheckCircle2, ShieldCheck, ArrowRight, Layers, Database } from "lucide-react";

interface TraceModalProps {
  isOpen: boolean;
  onClose: () => void;
  metric: string;
  year?: string | number;
  facilityId?: string | number;
  processType?: string;
}

interface TraceData {
  metric: string;
  metric_label: string;
  total_value: number;
  unit: string;
  record_count: number;
  filter_scope: {
    year: string | number;
    facility_id?: number;
    facility_name: string;
    process_type: string;
  };
  formula: string;
  gwp_standard: {
    standard: string;
    report_name: string;
    ch4_factor: number;
    n2o_factor: number;
    co2_factor: number;
  };
  breakdown_by_category: Array<{
    category: string;
    record_count: number;
    value: number;
    percentage: number;
    unit: string;
  }>;
  factors_applied: Array<{
    source: string;
    version: string;
    ef_co2?: number;
    ef_ch4?: number;
    ef_n2o?: number;
    records_count: number;
  }>;
  data_lineage: {
    statuses: Record<string, number>;
    submitters: string[];
    approvers: string[];
    earliest_entry?: string;
    latest_approval?: string;
  };
  sample_records: Array<{
    record_id: string;
    scope: number;
    facility_name: string;
    process_type: string;
    fuel_or_source: string;
    quantity: number;
    unit: string;
    factor_source: string;
    factor_version: string;
    gwp_version: string;
    co2e_t: number;
    status: string;
    submitter: string;
    approver: string;
    approved_at?: string;
  }>;
}

export const TraceDrilldownModal: React.FC<TraceModalProps> = ({
  isOpen,
  onClose,
  metric,
  year,
  facilityId,
  processType,
}) => {
  // translated via i18n helper
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<TraceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"lineage" | "factors" | "records">("lineage");

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setError(null);

    const params: Record<string, any> = { metric };
    if (year) params.year = year;
    if (facilityId) params.facility_id = facilityId;
    if (processType) params.process_type = processType;

    axios
      .get("/api/traceability/trace", { params })
      .then((res) => {
        setData(res.data);
      })
      .catch((err) => {
        setError(err.response?.data?.error || "Failed to load traceability details");
      })
      .finally(() => setLoading(false));
  }, [isOpen, metric, year, facilityId, processType]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={data ? `Trace Provenance: ${data.metric_label}` : "Trace This Number"}
    >
      <div className="space-y-6 text-sm text-slate-700 dark:text-slate-200">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
            <span className="ml-3 font-medium">Resolving calculation graph & audit trail...</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 rounded-lg border border-rose-200 dark:border-rose-900">
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {/* KPI Summary Card */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Aggregated Value ({data.filter_scope.year} | {data.filter_scope.facility_name})
                </p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-bold font-mono text-slate-900 dark:text-white">
                    {data.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className="text-base font-semibold text-emerald-700 dark:text-emerald-400">
                    {data.unit}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 rounded-full text-xs font-medium border border-emerald-200 dark:border-emerald-800 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  GWP: {data.gwp_standard.standard}
                </span>
                <span className="px-3 py-1 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-300 rounded-full text-xs font-mono">
                  {data.record_count} Records
                </span>
              </div>
            </div>

            {/* Formula Banner */}
            <div className="p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-900/50 flex items-start gap-2.5">
              <Database className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-semibold text-amber-900 dark:text-amber-300">Mathematical Formula: </span>
                <code className="font-mono text-amber-800 dark:text-amber-200">{data.formula}</code>
              </div>
            </div>

            {/* Tab navigation */}
            <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4">
              <button
                type="button"
                onClick={() => setActiveTab("lineage")}
                className={`pb-2.5 text-xs font-semibold uppercase tracking-wider transition-colors border-b-2 ${
                  activeTab === "lineage"
                    ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Lineage & Workflow
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("factors")}
                className={`pb-2.5 text-xs font-semibold uppercase tracking-wider transition-colors border-b-2 ${
                  activeTab === "factors"
                    ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Factor Versions ({data.factors_applied.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("records")}
                className={`pb-2.5 text-xs font-semibold uppercase tracking-wider transition-colors border-b-2 ${
                  activeTab === "records"
                    ? "border-emerald-600 text-emerald-600 dark:text-emerald-400"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                Contributing Records ({data.sample_records.length})
              </button>
            </div>

            {/* Tab: Lineage */}
            {activeTab === "lineage" && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                      Review & Approval State
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(data.data_lineage.statuses).map(([st, cnt]) => (
                        <div key={st} className="flex items-center gap-1.5 text-xs">
                          <StatusBadge status={st} />
                          <span className="font-mono font-medium">({cnt})</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                      Audit Timestamps
                    </h4>
                    <div className="text-xs space-y-1">
                      <div>
                        <span className="text-slate-500">First Entry: </span>
                        <span className="font-mono">{data.data_lineage.earliest_entry || "N/A"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Latest Sign-off: </span>
                        <span className="font-mono">{data.data_lineage.latest_approval || "N/A"}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Category Breakdown */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                    Category Breakdown
                  </h4>
                  <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 dark:bg-slate-800/50 font-semibold border-b border-slate-200 dark:border-slate-800">
                        <tr>
                          <th className="py-2 px-3">Process / Category</th>
                          <th className="py-2 px-3 text-right">Records</th>
                          <th className="py-2 px-3 text-right">Value ({data.unit})</th>
                          <th className="py-2 px-3 text-right">% of Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {data.breakdown_by_category.map((cat, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                            <td className="py-2 px-3 font-medium">{cat.category}</td>
                            <td className="py-2 px-3 text-right font-mono text-slate-500">{cat.record_count}</td>
                            <td className="py-2 px-3 text-right font-mono font-semibold">{cat.value.toLocaleString()}</td>
                            <td className="py-2 px-3 text-right font-mono">{cat.percentage}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Factors Applied */}
            {activeTab === "factors" && (
              <div className="space-y-3">
                <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 font-semibold border-b border-slate-200 dark:border-slate-800">
                      <tr>
                        <th className="py-2.5 px-3">Factor Source Reference</th>
                        <th className="py-2.5 px-3">Version</th>
                        <th className="py-2.5 px-3 text-right">CO₂ EF</th>
                        <th className="py-2.5 px-3 text-right">CH₄ EF</th>
                        <th className="py-2.5 px-3 text-right">N₂O EF</th>
                        <th className="py-2.5 px-3 text-right">Records Using</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {data.factors_applied.map((f, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 font-medium">{f.source}</td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[11px]">
                              {f.version}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono">{f.ef_co2 ?? "-"}</td>
                          <td className="py-2.5 px-3 text-right font-mono">{f.ef_ch4 ?? "-"}</td>
                          <td className="py-2.5 px-3 text-right font-mono">{f.ef_n2o ?? "-"}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-semibold">{f.records_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab: Contributing Records */}
            {activeTab === "records" && (
              <div className="space-y-3">
                <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-x-auto max-h-72">
                  <table className="w-full text-left text-xs whitespace-nowrap">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 font-semibold border-b border-slate-200 dark:border-slate-800 sticky top-0">
                      <tr>
                        <th className="py-2.5 px-3">Record ID</th>
                        <th className="py-2.5 px-3">Facility</th>
                        <th className="py-2.5 px-3">Process</th>
                        <th className="py-2.5 px-3 text-right">Activity</th>
                        <th className="py-2.5 px-3">Factor Version</th>
                        <th className="py-2.5 px-3 text-right">CO₂e (t)</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Approver</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {data.sample_records.map((r, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                          <td className="py-2 px-3 font-mono font-medium text-emerald-700 dark:text-emerald-400">
                            {r.record_id}
                          </td>
                          <td className="py-2 px-3">{r.facility_name}</td>
                          <td className="py-2 px-3">{r.process_type}</td>
                          <td className="py-2 px-3 text-right font-mono">
                            {r.quantity?.toLocaleString()} {r.unit}
                          </td>
                          <td className="py-2 px-3 font-mono text-[11px]">{r.factor_version}</td>
                          <td className="py-2 px-3 text-right font-mono font-semibold">{r.co2e_t.toLocaleString()}</td>
                          <td className="py-2 px-3">
                            <StatusBadge status={r.status} />
                          </td>
                          <td className="py-2 px-3 text-slate-500">{r.approver}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        <div className="flex justify-end pt-4 border-t border-slate-200 dark:border-slate-800">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
};
