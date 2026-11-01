import React, { useEffect } from "react";
import { Calculator, X, Info, ShieldCheck, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import "./CalculationDetails.css";
import { useGwpStandard } from "../hooks/useGwpStandard";
import { t as tr } from "../i18n";

export interface CalculationRecord {
  process_type?: string;
  fuel?: string;
  amount?: number;
  unit?: string;
  facility?: string;
  year?: number;
  month?: number;
  equipment_id?: string;
  status?: string;
  factor_source?: string;
  method?: string;
  emissions?: {
    co2?: number;
    ch4?: number;
    n2o?: number;
    totalCo2e?: number;
    co2e_total?: number;
  };
  factors?: {
    co2?: number;
    ch4?: number;
    n2o?: number;
    gwp_ch4?: number;
    gwp_n2o?: number;
  };
  uncertainty?: {
    co2?: number;
    ch4?: number;
    n2o?: number;
  };
  steps?: Array<{
    name: string;
    desc: string;
  }>;
  [key: string]: any;
}

export interface CalculationDetailsProps {
  calculation: CalculationRecord | null;
  onClose?: () => void;
}

// no API Compendium / table / equation references in the emission UI
const stripApi = (t?: string): string | undefined =>
  t
    ? String(t)
        .replace(/\s*\([^()]*(?:API|Compendium|Table|Eq\.|§)[^()]*\)/g, "")
        .replace(/API(?:\s+GHG)?\s+Compendium(?:\s+2021)?[^,;]*[,;]?\s*/g, "")
        .replace(/\bTables?\s+[\d\-.,\s]+/g, "")
        .trim()
    : t;

const CalculationDetails: React.FC<CalculationDetailsProps> = ({ calculation, onClose }) => {
  // the organisation's active GWP set: the labels were hard-coded "28 / 265 (AR5)" whatever the standard
  const { standard: gwpStd, gwp: gwpSet } = useGwpStandard();
  // Escape closes the dialog, as its close button advertises
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!calculation) return null;

  const {
    process_type,
    fuel,
    amount,
    unit,
    facility,
    year,
    month,
    equipment_id,
    status,
    factor_source,
    method,
    emissions,
    factors,
    uncertainty,
  } = calculation;

  const formatNumber = (num: any, decimals = 3): string => {
    if (num === null || num === undefined || isNaN(num)) return "0";
    return parseFloat(num).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const normStatus = (status || "Verified").toLowerCase();

  return (
    <div className="calc-overlay fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-[9999] p-4" onClick={onClose} role="dialog" aria-modal="true">
      <div role="presentation" className="calc-modal bg-surface border border-border rounded-lg max-w-[860px] w-full max-h-[90vh] flex flex-col shadow-overlay overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="calc-header">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-md bg-green-50 text-green-700 border border-green-200 flex items-center justify-center shrink-0">
              <Calculator size={22} />
            </div>
            <div>
              <h3>{tr("Calculation Details & Provenance")}</h3>
              <p className="m-0 mt-0.5 text-sm text-text-secondary font-medium">
                {process_type || tr("Scope 1 Emission Record")}
              </p>
            </div>
          </div>
          <button className="calc-close-btn" onClick={onClose} title={tr("Close (Esc)")}>
            <X size={18} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 flex flex-col gap-6">
          {/* Input Summary */}
          <div className="flex flex-col gap-3">
            <h4 className="calc-section-title">
              <Info size={16} />{" "}{tr("Operational Context & Input Parameters")}
            </h4>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-3">
              {facility && (
                <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                  <span className="text-xs font-medium text-text-secondary">{tr("Facility / Asset")}</span>
                  <span className="text-sm text-text font-semibold break-words">{facility}</span>
                </div>
              )}
              {year && (
                <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                  <span className="text-xs font-medium text-text-secondary">{tr("Reporting Period")}</span>
                  <span className="text-sm text-text font-semibold break-words">
                    {year}
                    {month ? ` - M${String(month).padStart(2, "0")}` : ""}
                  </span>
                </div>
              )}
              <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                <span className="text-xs font-medium text-text-secondary">{tr("Process Type")}</span>
                <span className="text-sm text-text font-semibold break-words">{process_type || tr("Direct Combustion")}</span>
              </div>
              {fuel && (
                <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                  <span className="text-xs font-medium text-text-secondary">{tr("Fuel / Source Stream")}</span>
                  <span className="text-sm text-text font-semibold break-words">{fuel}</span>
                </div>
              )}
              <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                <span className="text-xs font-medium text-text-secondary">{tr("Activity Quantity")}</span>
                <span className="text-sm text-text font-semibold tabular-nums break-words">
                  {formatNumber(amount, 2)} {unit || tr("units")}
                </span>
              </div>
              <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                <span className="text-xs font-medium text-text-secondary">{tr("Calculation Method")}</span>
                <span className="text-sm text-text font-semibold break-words">{stripApi(method || factor_source) || "—"}</span>
              </div>
              {equipment_id && equipment_id !== "-" && (
                <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                  <span className="text-xs font-medium text-text-secondary">{tr("Equipment Tag")}</span>
                  <span className="text-sm text-text font-semibold font-mono break-words">{equipment_id}</span>
                </div>
              )}
              <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1 transition-colors hover:border-ink-300">
                <span className="text-xs font-medium text-text-secondary">{tr("Inventory Status")}</span>
                <div className="text-sm text-text font-semibold break-words">
                  <span
                    className={`status-pill ${
                      normStatus.includes("verif") || normStatus.includes("appr")
                        ? "verified"
                        : normStatus.includes("draft")
                        ? "draft"
                        : "pending"
                    }`}
                  >
                    {normStatus.includes("verif") || normStatus.includes("appr") ? (
                      <CheckCircle2 size={12} />
                    ) : normStatus.includes("draft") ? (
                      <AlertCircle size={12} />
                    ) : (
                      <Clock size={12} />
                    )}
                    {status || tr("Verified")}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Emission Factors Used */}
          {factors && (
            <div className="flex flex-col gap-3">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} />{" "}{tr("Emission Factors & GWP Metrics Applied")}
              </h4>
              <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3">
                {factors.co2 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">{tr("CO₂")}</span>
                      <span>{tr("Carbon Dioxide Factor")}</span>
                    </div>
                    <div className="font-mono text-sm text-text font-bold tabular-nums">
                      {formatNumber(factors.co2, 6)} kg/{unit || tr("unit")}
                    </div>
                  </div>
                )}
                {factors.ch4 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">{tr("CH₄")}</span>
                      <span>{tr("Methane Factor")}</span>
                    </div>
                    <div className="font-mono text-sm text-text font-bold tabular-nums">
                      {formatNumber(factors.ch4, 6)} kg/{unit || tr("unit")}
                    </div>
                  </div>
                )}
                {factors.n2o != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="px-2 py-0.5 rounded text-xs font-bold bg-purple-50 text-purple-700 border border-purple-200">N₂O</span>
                      <span>{tr("Nitrous Oxide Factor")}</span>
                    </div>
                    <div className="font-mono text-sm text-text font-bold tabular-nums">
                      {formatNumber(factors.n2o, 6)} kg/{unit || tr("unit")}
                    </div>
                  </div>
                )}
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">GWP</span>
                    <span>{tr("CH₄ Global Warming Potential")}</span>
                  </div>
                  <div className="font-mono text-sm text-text font-bold tabular-nums">{factors.gwp_ch4 ?? gwpSet?.CH4 ?? "—"}{gwpStd ? ` (${gwpStd})` : ""}</div>
                </div>
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">GWP</span>
                    <span>{tr("N₂O Global Warming Potential")}</span>
                  </div>
                  <div className="font-mono text-sm text-text font-bold tabular-nums">{factors.gwp_n2o ?? gwpSet?.N2O ?? "—"}{gwpStd ? ` (${gwpStd})` : ""}</div>
                </div>
              </div>
            </div>
          )}

          {/* Uncertainty & ISO 14064 Compliance */}
          {uncertainty && (uncertainty.co2 != null || uncertainty.ch4 != null || uncertainty.n2o != null) && (
            <div className="flex flex-col gap-3">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} />{" "}{tr("Uncertainty Assessment (ISO/IEC Guide 98-3 GUM)")}
              </h4>
              <div className="uncertainty-grid">
                {uncertainty.co2 != null && (
                  <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1">
                    <span className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">{tr("CO₂")}</span>{" "}{tr("1σ Uncertainty")}
                    </span>
                    <span className="text-sm font-bold text-rose-700 font-mono tabular-nums">
                      ±{(Number(uncertainty.co2) * 100).toFixed(1)}%
                    </span>
                    <span className="text-xs text-text-secondary font-medium">
                      {tr("95% CI (k=2): ±")}{(Number(uncertainty.co2) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.ch4 != null && (
                  <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1">
                    <span className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">{tr("CH₄")}</span>{" "}{tr("1σ Uncertainty")}
                    </span>
                    <span className="text-sm font-bold text-blue-700 font-mono tabular-nums">
                      ±{(Number(uncertainty.ch4) * 100).toFixed(1)}%
                    </span>
                    <span className="text-xs text-text-secondary font-medium">
                      {tr("95% CI (k=2): ±")}{(Number(uncertainty.ch4) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.n2o != null && (
                  <div className="bg-ink-50 border border-border rounded-md p-3 flex flex-col gap-1">
                    <span className="flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">N₂O</span>{" "}{tr("1σ Uncertainty")}
                    </span>
                    <span className="text-sm font-bold text-purple-700 font-mono tabular-nums">
                      ±{(Number(uncertainty.n2o) * 100).toFixed(1)}%
                    </span>
                    <span className="text-xs text-text-secondary font-medium">
                      {tr("95% CI (k=2): ±")}{(Number(uncertainty.n2o) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Final Results */}
          <div className="flex flex-col gap-3">
            <h4 className="calc-section-title">
              <CheckCircle2 size={16} />{" "}{tr("Computed Greenhouse Gas Inventory")}
            </h4>
            <div className="results-grid">
              <div className="result-card">
                <div className="result-label text-xs font-medium text-text-secondary">{tr("CO₂ Mass")}</div>
                <div className="result-value text-xl font-bold tabular-nums text-text">
                  {formatNumber(emissions?.co2 || 0)}
                </div>
                <div className="result-unit text-xs text-text-secondary">{tr("tonnes CO₂")}</div>
              </div>
              <div className="result-card">
                <div className="result-label text-xs font-medium text-text-secondary">{tr("CH₄ Mass")}</div>
                <div className="result-value text-xl font-bold tabular-nums text-text">
                  {formatNumber(emissions?.ch4 || 0, 4)}
                </div>
                <div className="result-unit text-xs text-text-secondary">{tr("tonnes CH₄")}</div>
              </div>
              <div className="result-card">
                <div className="result-label text-xs font-medium text-text-secondary">{tr("N₂O Mass")}</div>
                <div className="result-value text-xl font-bold tabular-nums text-text">
                  {formatNumber(emissions?.n2o || 0, 4)}
                </div>
                <div className="result-unit text-xs text-text-secondary">{tr("tonnes N₂O")}</div>
              </div>
              <div className="result-card total">
                <div className="result-label text-xs font-semibold text-emerald-800">{tr("Total GWP Equiv.")}</div>
                <div className="result-value text-xl font-bold tabular-nums text-emerald-900">
                  {formatNumber(emissions?.totalCo2e || emissions?.co2e_total || 0)}
                </div>
                <div className="result-unit text-xs font-medium text-emerald-700">{tr("tonnes CO₂e")}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Reference */}
        <div className="calc-footer">
          <Info size={16} />
          <span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default CalculationDetails;
