import React, { useEffect } from "react";
import { Calculator, X, Info, ShieldCheck, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import "./CalculationDetails.css";
import { useGwpStandard } from "../hooks/useGwpStandard";

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
    <div className="calc-overlay [position:fixed] [top:0] [left:0] [right:0] [bottom:0] [background:rgba(15,_23,_42,_0.65)] [backdrop-filter:blur(4px)] [-webkit-backdrop-filter:blur(4px)] [display:flex] [align-items:center] [justify-content:center] [z-index:9999] [padding:16px] [animation:calcFadeIn_0.2s_cubic-bezier(0.16,_1,_0.3,_1)]" onClick={onClose} role="dialog" aria-modal="true">
      <div role="presentation" className="calc-modal [background:var(--color-white)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-lg)] [max-width:860px] [width:100%] [max-height:90vh] [display:flex] [flex-direction:column] [box-shadow:var(--shadow-overlay)] [animation:calcSlideUp_0.25s_cubic-bezier(0.16,_1,_0.3,_1)] [overflow:hidden] [&_::-webkit-scrollbar]:[width:6px] [&_::-webkit-scrollbar]:[height:6px] [&_::-webkit-scrollbar-track]:[background:var(--color-ink-100)] [&&]:[&_::-webkit-scrollbar-thumb]:[background:var(--color-ink-300)] [&_::-webkit-scrollbar-thumb]:[border-radius:999px] [&&]:[&&]:[&_::-webkit-scrollbar-thumb:hover]:[background:var(--color-ink-400)]" onClick={(e) => e.stopPropagation()}>
        <div className="calc-header">
          <div className="[display:flex] [align-items:center] [gap:12px]">
            <div className="[width:40px] [height:40px] [border-radius:var(--radius-md)] [background:var(--color-green-50)] [color:var(--color-green-700)] [border:1px_solid_#a7f3d0] [display:flex] [align-items:center] [justify-content:center] [flex-shrink:0]">
              <Calculator size={22} />
            </div>
            <div>
              <h3>Calculation Details & Provenance</h3>
              <p className="[margin:2px_0_0_0] [font-size:var(--text-sm)] [color:var(--color-ink-500)] [font-weight:500]">
                {process_type || "Scope 1 Emission Record"}
              </p>
            </div>
          </div>
          <button className="calc-close-btn" onClick={onClose} title="Close (Esc)">
            <X size={18} />
          </button>
        </div>

        <div className="[padding:24px] [overflow-y:auto] [flex:1] [display:flex] [&&]:[flex-direction:column] [gap:24px]">
          {/* Input Summary */}
          <div className="[display:flex] [flex-direction:column] [gap:12px]">
            <h4 className="calc-section-title">
              <Info size={16} /> Operational Context & Input Parameters
            </h4>
            <div className="[display:grid] [grid-template-columns:repeat(auto-fill,_minmax(180px,_1fr))] [gap:12px]">
              {facility && (
                <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                  <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Facility / Asset</span>
                  <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">{facility}</span>
                </div>
              )}
              {year && (
                <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                  <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Reporting Period</span>
                  <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">
                    {year}
                    {month ? ` - M${String(month).padStart(2, "0")}` : ""}
                  </span>
                </div>
              )}
              <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Process Type</span>
                <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">{process_type || "Direct Combustion"}</span>
              </div>
              {fuel && (
                <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                  <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Fuel / Source Stream</span>
                  <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">{fuel}</span>
                </div>
              )}
              <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Activity Quantity</span>
                <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">
                  {formatNumber(amount, 2)} {unit || "units"}
                </span>
              </div>
              <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Calculation Method</span>
                <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">{stripApi(method || factor_source) || "—"}</span>
              </div>
              {equipment_id && equipment_id !== "-" && (
                <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                  <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Equipment Tag</span>
                  <span className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">{equipment_id}</span>
                </div>
              )}
              <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease] hover:[border-color:var(--color-ink-300)] hover:[box-shadow:var(--shadow-xs)]">
                <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">Inventory Status</span>
                <div className="[font-size:var(--text-md)] [color:var(--color-ink-900)] [font-weight:600] [word-break:break-word]">
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
                    {status || "Verified"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Emission Factors Used */}
          {factors && (
            <div className="[display:flex] [flex-direction:column] [gap:12px]">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} /> Emission Factors & GWP Metrics Applied
              </h4>
              <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(220px,_1fr))] [gap:12px]">
                {factors.co2 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] co2">CO₂</span>
                      <span>Carbon Dioxide Factor</span>
                    </div>
                    <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace] [font-size:var(--text-base)] [color:var(--color-ink-900)] [font-weight:700]">
                      {formatNumber(factors.co2, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                {factors.ch4 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] ch4">CH₄</span>
                      <span>Methane Factor</span>
                    </div>
                    <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace] [font-size:var(--text-base)] [color:var(--color-ink-900)] [font-weight:700]">
                      {formatNumber(factors.ch4, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                {factors.n2o != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] n2o">N₂O</span>
                      <span>Nitrous Oxide Factor</span>
                    </div>
                    <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace] [font-size:var(--text-base)] [color:var(--color-ink-900)] [font-weight:700]">
                      {formatNumber(factors.n2o, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] gwp">GWP</span>
                    <span>CH₄ Global Warming Potential</span>
                  </div>
                  <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace] [font-size:var(--text-base)] [color:var(--color-ink-900)] [font-weight:700]">{factors.gwp_ch4 ?? gwpSet?.CH4 ?? "—"}{gwpStd ? ` (${gwpStd})` : ""}</div>
                </div>
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] gwp">GWP</span>
                    <span>N₂O Global Warming Potential</span>
                  </div>
                  <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace] [font-size:var(--text-base)] [color:var(--color-ink-900)] [font-weight:700]">{factors.gwp_n2o ?? gwpSet?.N2O ?? "—"}{gwpStd ? ` (${gwpStd})` : ""}</div>
                </div>
              </div>
            </div>
          )}

          {/* Uncertainty & ISO 14064 Compliance */}
          {uncertainty && (uncertainty.co2 != null || uncertainty.ch4 != null || uncertainty.n2o != null) && (
            <div className="[display:flex] [flex-direction:column] [gap:12px]">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} /> Uncertainty Assessment (ISO/IEC Guide 98-3 GUM)
              </h4>
              <div className="uncertainty-grid">
                {uncertainty.co2 != null && (
                  <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [&_.unc-label]:[font-size:var(--text-sm)]! [&_.unc-label]:[font-weight:600]! [&_.unc-label]:[color:var(--color-ink-500)]! [&_.unc-label]:[display:flex] [&_.unc-label]:[align-items:center] [&_.unc-label]:[gap:6px] [&&]:[&&]:[&_.unc-value]:[font-size:var(--text-md)]! [&&]:[&&]:[&_.unc-value]:[font-weight:700]! [&&]:[&&]:[&_.unc-value]:[font-family:ui-monospace,_monospace]!">
                    <span className="unc-label">
                      <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] co2">CO₂</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value text-[color:#dc2626]!">
                      ±{(Number(uncertainty.co2) * 100).toFixed(1)}%
                    </span>
                    <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">
                      95% CI (k=2): ±{(Number(uncertainty.co2) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.ch4 != null && (
                  <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [&_.unc-label]:[font-size:var(--text-sm)]! [&_.unc-label]:[font-weight:600]! [&_.unc-label]:[color:var(--color-ink-500)]! [&_.unc-label]:[display:flex] [&_.unc-label]:[align-items:center] [&_.unc-label]:[gap:6px] [&&]:[&&]:[&_.unc-value]:[font-size:var(--text-md)]! [&&]:[&&]:[&_.unc-value]:[font-weight:700]! [&&]:[&&]:[&_.unc-value]:[font-family:ui-monospace,_monospace]!">
                    <span className="unc-label">
                      <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] ch4">CH₄</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value text-[color:#0369a1]!">
                      ±{(Number(uncertainty.ch4) * 100).toFixed(1)}%
                    </span>
                    <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">
                      95% CI (k=2): ±{(Number(uncertainty.ch4) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.n2o != null && (
                  <div className="[background:var(--color-ink-50)] [border:1px_solid_var(--color-ink-200)] [&&]:[border-radius:var(--radius-md)] [padding:12px_14px] [display:flex] [flex-direction:column] [gap:4px] [&_.unc-label]:[font-size:var(--text-sm)]! [&_.unc-label]:[font-weight:600]! [&_.unc-label]:[color:var(--color-ink-500)]! [&_.unc-label]:[display:flex] [&_.unc-label]:[align-items:center] [&_.unc-label]:[gap:6px] [&&]:[&&]:[&_.unc-value]:[font-size:var(--text-md)]! [&&]:[&&]:[&_.unc-value]:[font-weight:700]! [&&]:[&&]:[&_.unc-value]:[font-family:ui-monospace,_monospace]!">
                    <span className="unc-label">
                      <span className="[padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [&.co2]:[background:#fee2e2] [&.co2]:[color:var(--color-red-700)]! [&.co2]:[border:1px_solid_#fecaca] [&&]:[&.ch4]:[background:#e0f2fe] [&&]:[&.ch4]:[color:var(--color-blue-700)]! [&&]:[&.ch4]:[border:1px_solid_#bae6fd] [&&]:[&&]:[&.n2o]:[background:#f3e8ff] [&&]:[&&]:[&.n2o]:[color:#9333ea]! [&&]:[&&]:[&.n2o]:[border:1px_solid_#e9d5ff] [&&]:[&&]:[&&]:[&.gwp]:[background:#dcfce7] [&&]:[&&]:[&&]:[&.gwp]:[color:var(--color-green-700)]! [&&]:[&&]:[&&]:[&.gwp]:[border:1px_solid_#bbf7d0] n2o">N₂O</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value text-[color:#9333ea]!">
                      ±{(Number(uncertainty.n2o) * 100).toFixed(1)}%
                    </span>
                    <span className="[font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.04em]">
                      95% CI (k=2): ±{(Number(uncertainty.n2o) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Final Results */}
          <div className="[display:flex] [flex-direction:column] [gap:12px]">
            <h4 className="calc-section-title">
              <CheckCircle2 size={16} /> Computed Greenhouse Gas Inventory
            </h4>
            <div className="results-grid">
              <div className="result-card">
                <div className="result-label [font-size:var(--text-sm)] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.05em] [font-weight:700]">CO₂ Mass</div>
                <div className="result-value [font-size:var(--text-xl)] [font-weight:800] [color:var(--color-ink-900)]">
                  {formatNumber(emissions?.co2 || 0)}
                </div>
                <div className="result-unit [font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)]">tonnes CO₂</div>
              </div>
              <div className="result-card">
                <div className="result-label [font-size:var(--text-sm)] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.05em] [font-weight:700]">CH₄ Mass</div>
                <div className="result-value [font-size:var(--text-xl)] [font-weight:800] [color:var(--color-ink-900)]">
                  {formatNumber(emissions?.ch4 || 0, 4)}
                </div>
                <div className="result-unit [font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)]">tonnes CH₄</div>
              </div>
              <div className="result-card">
                <div className="result-label [font-size:var(--text-sm)] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.05em] [font-weight:700]">N₂O Mass</div>
                <div className="result-value [font-size:var(--text-xl)] [font-weight:800] [color:var(--color-ink-900)]">
                  {formatNumber(emissions?.n2o || 0, 4)}
                </div>
                <div className="result-unit [font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)]">tonnes N₂O</div>
              </div>
              <div className="result-card total">
                <div className="result-label [font-size:var(--text-sm)] [color:var(--color-ink-500)] [text-transform:uppercase] [letter-spacing:0.05em] [font-weight:700]">Total GWP Equiv.</div>
                <div className="result-value [font-size:var(--text-xl)] [font-weight:800] [color:var(--color-ink-900)]">
                  {formatNumber(emissions?.totalCo2e || emissions?.co2e_total || 0)}
                </div>
                <div className="result-unit [font-size:var(--text-xs)] [font-weight:600] [color:var(--color-ink-500)]">tonnes CO₂e</div>
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
