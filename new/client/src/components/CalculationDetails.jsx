import React, { useEffect } from "react";
import { Calculator, X, Info, ShieldCheck, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import "./CalculationDetails.css";
import { useGwpStandard } from "../hooks/useGwpStandard";

// no API Compendium / table / equation references in the emission UI
const stripApi = (t) =>
  t
    ? String(t)
        .replace(/\s*\([^()]*(?:API|Compendium|Table|Eq\.|§)[^()]*\)/g, "")
        .replace(/API(?:\s+GHG)?\s+Compendium(?:\s+2021)?[^,;]*[,;]?\s*/g, "")
        .replace(/\bTables?\s+[\d\-.,\s]+/g, "")
        .trim()
    : t;
const CalculationDetails = ({ calculation, onClose }) => {
  // the organisation's active GWP set: the labels were hard-coded "28 / 265 (AR5)" whatever the standard
  const { standard: gwpStd, gwp: gwpSet } = useGwpStandard();
  // Escape closes the dialog, as its close button advertises
  useEffect(() => {
    const onKey = (e) => {
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

  const formatNumber = (num, decimals = 3) => {
    if (num === null || num === undefined || isNaN(num)) return "0";
    return parseFloat(num).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const normStatus = (status || "Verified").toLowerCase();

  return (
    <div className="calc-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="calc-modal" onClick={(e) => e.stopPropagation()}>
        <div className="calc-header">
          <div className="[display:flex]! [align-items:center] [gap:12px]">
            <div className="[width:40px]! [height:40px]! [border-radius:var(--radius-md)]! [background:var(--color-green-50)]! [color:var(--color-green-700)]! [border:1px_solid_#a7f3d0]! [display:flex]! [align-items:center] [justify-content:center] [flex-shrink:0]">
              <Calculator size={22} />
            </div>
            <div>
              <h3>Calculation Details & Provenance</h3>
              <p className="[margin:2px_0_0_0]! [font-size:var(--text-sm)]! [color:var(--color-ink-500)]! [font-weight:500]!">
                {process_type || "Scope 1 Emission Record"}
              </p>
            </div>
          </div>
          <button className="calc-close-btn" onClick={onClose} title="Close (Esc)">
            <X size={18} />
          </button>
        </div>

        <div className="[padding:24px]! [overflow-y:auto]! [flex:1] [display:flex]! [flex-direction:column] [gap:24px]">
          {/* Input Summary */}
          <div className="[display:flex]! [flex-direction:column] [gap:12px]">
            <h4 className="calc-section-title">
              <Info size={16} /> Operational Context & Input Parameters
            </h4>
            <div className="[display:grid]! [grid-template-columns:repeat(auto-fill,_minmax(180px,_1fr))] [gap:12px]">
              {facility && (
                <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                  <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Facility / Asset</span>
                  <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">{facility}</span>
                </div>
              )}
              {year && (
                <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                  <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Reporting Period</span>
                  <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">
                    {year}
                    {month ? ` - M${String(month).padStart(2, "0")}` : ""}
                  </span>
                </div>
              )}
              <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Process Type</span>
                <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">{process_type || "Direct Combustion"}</span>
              </div>
              {fuel && (
                <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                  <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Fuel / Source Stream</span>
                  <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">{fuel}</span>
                </div>
              )}
              <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Activity Quantity</span>
                <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">
                  {formatNumber(amount, 2)} {unit || "units"}
                </span>
              </div>
              <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Calculation Method</span>
                <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">{stripApi(method || factor_source) || "—"}</span>
              </div>
              {equipment_id && equipment_id !== "-" && (
                <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                  <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Equipment Tag</span>
                  <span className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">{equipment_id}</span>
                </div>
              )}
              <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_14px]! [display:flex]! [flex-direction:column] [gap:4px] [transition:border-color_0.2s_ease,_box-shadow_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[box-shadow:var(--shadow-xs)]!">
                <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">Inventory Status</span>
                <div className="[font-size:var(--text-md)]! [color:var(--color-ink-900)]! [font-weight:600]! [word-break:break-word]">
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
            <div className="[display:flex]! [flex-direction:column] [gap:12px]">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} /> Emission Factors & GWP Metrics Applied
              </h4>
              <div className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(220px,_1fr))] [gap:12px]">
                {factors.co2 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge co2">CO₂</span>
                      <span>Carbon Dioxide Factor</span>
                    </div>
                    <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [font-weight:700]!">
                      {formatNumber(factors.co2, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                {factors.ch4 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge ch4">CH₄</span>
                      <span>Methane Factor</span>
                    </div>
                    <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [font-weight:700]!">
                      {formatNumber(factors.ch4, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                {factors.n2o != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge n2o">N₂O</span>
                      <span>Nitrous Oxide Factor</span>
                    </div>
                    <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [font-weight:700]!">
                      {formatNumber(factors.n2o, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="gas-badge gwp">GWP</span>
                    <span>CH₄ Global Warming Potential</span>
                  </div>
                  <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [font-weight:700]!">{factors.gwp_ch4 ?? gwpSet?.CH4 ?? "—"}{gwpStd ? ` (${gwpStd})` : ""}</div>
                </div>
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="gas-badge gwp">GWP</span>
                    <span>N₂O Global Warming Potential</span>
                  </div>
                  <div className="[font-family:ui-monospace,_SFMono-Regular,_Menlo,_Monaco,_Consolas,_monospace]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [font-weight:700]!">{factors.gwp_n2o ?? gwpSet?.N2O ?? "—"}{gwpStd ? ` (${gwpStd})` : ""}</div>
                </div>
              </div>
            </div>
          )}

          {/* Calculation Steps */}
          {/* Uncertainty & ISO 14064 Compliance */}
          {uncertainty && (uncertainty.co2 != null || uncertainty.ch4 != null || uncertainty.n2o != null) && (
            <div className="[display:flex]! [flex-direction:column] [gap:12px]">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} /> Uncertainty Assessment (ISO/IEC Guide 98-3 GUM)
              </h4>
              <div className="uncertainty-grid">
                {uncertainty.co2 != null && (
                  <div className="uncertainty-card">
                    <span className="unc-label">
                      <span className="gas-badge co2">CO₂</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value text-[color:#dc2626]!">
                      ±{(Number(uncertainty.co2) * 100).toFixed(1)}%
                    </span>
                    <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">
                      95% CI (k=2): ±{(Number(uncertainty.co2) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.ch4 != null && (
                  <div className="uncertainty-card">
                    <span className="unc-label">
                      <span className="gas-badge ch4">CH₄</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value text-[color:#0369a1]!">
                      ±{(Number(uncertainty.ch4) * 100).toFixed(1)}%
                    </span>
                    <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">
                      95% CI (k=2): ±{(Number(uncertainty.ch4) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.n2o != null && (
                  <div className="uncertainty-card">
                    <span className="unc-label">
                      <span className="gas-badge n2o">N₂O</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value text-[color:#9333ea]!">
                      ±{(Number(uncertainty.n2o) * 100).toFixed(1)}%
                    </span>
                    <span className="[font-size:var(--text-xs)]! [font-weight:600]! [color:var(--color-ink-500)]! [text-transform:uppercase]! [letter-spacing:0.04em]">
                      95% CI (k=2): ±{(Number(uncertainty.n2o) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Final Results */}
          <div className="[display:flex]! [flex-direction:column] [gap:12px]">
            <h4 className="calc-section-title">
              <CheckCircle2 size={16} /> Computed Greenhouse Gas Inventory
            </h4>
            <div className="[display:grid]! [grid-template-columns:repeat(4,_1fr)] [gap:12px] max-[640px]:[grid-template-columns:repeat(2,_1fr)]">
              <div className="result-card">
                <div className="result-label">CO₂ Mass</div>
                <div className="result-value">
                  {formatNumber(emissions?.co2 || 0)}
                </div>
                <div className="result-unit">tonnes CO₂</div>
              </div>
              <div className="result-card">
                <div className="result-label">CH₄ Mass</div>
                <div className="result-value">
                  {formatNumber(emissions?.ch4 || 0, 4)}
                </div>
                <div className="result-unit">tonnes CH₄</div>
              </div>
              <div className="result-card">
                <div className="result-label">N₂O Mass</div>
                <div className="result-value">
                  {formatNumber(emissions?.n2o || 0, 4)}
                </div>
                <div className="result-unit">tonnes N₂O</div>
              </div>
              <div className="result-card total">
                <div className="result-label">Total GWP Equiv.</div>
                <div className="result-value">
                  {formatNumber(emissions?.totalCo2e || emissions?.co2e_total || 0)}
                </div>
                <div className="result-unit">tonnes CO₂e</div>
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
