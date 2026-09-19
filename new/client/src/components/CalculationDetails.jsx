import React from "react";
import { Calculator, X, Info, ShieldCheck, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import "./CalculationDetails.css";

const CalculationDetails = ({ calculation, onClose }) => {
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
    steps,
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
          <div className="calc-header-info">
            <div className="calc-header-icon">
              <Calculator size={22} />
            </div>
            <div>
              <h3>Calculation Details & Provenance</h3>
              <p className="calc-header-subtitle">
                {process_type || "Scope 1 Emission Record"}
              </p>
            </div>
          </div>
          <button className="calc-close-btn" onClick={onClose} title="Close (Esc)">
            <X size={18} />
          </button>
        </div>

        <div className="calc-body">
          {/* Input Summary */}
          <div className="calc-section">
            <h4 className="calc-section-title">
              <Info size={16} /> Operational Context & Input Parameters
            </h4>
            <div className="param-grid">
              {facility && (
                <div className="param-item">
                  <span className="param-label">Facility / Asset</span>
                  <span className="param-value">{facility}</span>
                </div>
              )}
              {year && (
                <div className="param-item">
                  <span className="param-label">Reporting Period</span>
                  <span className="param-value">
                    {year}
                    {month ? ` - M${String(month).padStart(2, "0")}` : ""}
                  </span>
                </div>
              )}
              <div className="param-item">
                <span className="param-label">Process Type</span>
                <span className="param-value">{process_type || "Direct Combustion"}</span>
              </div>
              {fuel && (
                <div className="param-item">
                  <span className="param-label">Fuel / Source Stream</span>
                  <span className="param-value">{fuel}</span>
                </div>
              )}
              <div className="param-item">
                <span className="param-label">Activity Quantity</span>
                <span className="param-value">
                  {formatNumber(amount, 2)} {unit || "units"}
                </span>
              </div>
              <div className="param-item">
                <span className="param-label">Calculation Method</span>
                <span className="param-value">{method || factor_source || "API Compendium / Tier 1"}</span>
              </div>
              {equipment_id && equipment_id !== "-" && (
                <div className="param-item">
                  <span className="param-label">Equipment Tag</span>
                  <span className="param-value">{equipment_id}</span>
                </div>
              )}
              <div className="param-item">
                <span className="param-label">Inventory Status</span>
                <div className="param-value">
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
            <div className="calc-section">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} /> Emission Factors & GWP Metrics Applied
              </h4>
              <div className="factors-grid">
                {factors.co2 != null && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge co2">CO₂</span>
                      <span>Carbon Dioxide Factor</span>
                    </div>
                    <div className="factor-value">
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
                    <div className="factor-value">
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
                    <div className="factor-value">
                      {formatNumber(factors.n2o, 6)} kg/{unit || "unit"}
                    </div>
                  </div>
                )}
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="gas-badge gwp">GWP</span>
                    <span>CH₄ Global Warming Potential</span>
                  </div>
                  <div className="factor-value">{factors.gwp_ch4 || 28.0} (AR5)</div>
                </div>
                <div className="factor-item">
                  <div className="factor-label">
                    <span className="gas-badge gwp">GWP</span>
                    <span>N₂O Global Warming Potential</span>
                  </div>
                  <div className="factor-value">{factors.gwp_n2o || 265.0} (AR5)</div>
                </div>
              </div>
            </div>
          )}

          {/* Calculation Steps */}
          {steps && steps.length > 0 && (
            <div className="calc-section">
              <h4 className="calc-section-title">
                <Calculator size={16} /> Calculation Methodology & Stepper
              </h4>
              <div className="steps-container">
                {steps.map((step, idx) => (
                  <div key={idx} className="calc-step">
                    <div className="step-number">{idx + 1}</div>
                    <div className="step-content">
                      <div className="step-label">
                        {step.label || step.name || `Step ${idx + 1}`}
                      </div>
                      {(step.desc || step.description) && (
                        <div className="step-desc">
                          {step.desc || step.description}
                        </div>
                      )}
                      {step.formula && (
                        <div className="step-formula">{step.formula}</div>
                      )}
                      {step.result !== undefined && step.result !== null && (
                        <div className="step-result">
                          = {formatNumber(step.result, 4)} {step.unit || "tCO₂e"}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Uncertainty & ISO 14064 Compliance */}
          {uncertainty && (uncertainty.co2 != null || uncertainty.ch4 != null || uncertainty.n2o != null) && (
            <div className="calc-section">
              <h4 className="calc-section-title">
                <ShieldCheck size={16} /> Uncertainty Assessment (ISO/IEC Guide 98-3 GUM)
              </h4>
              <div className="uncertainty-grid">
                {uncertainty.co2 != null && (
                  <div className="uncertainty-card">
                    <span className="unc-label">
                      <span className="gas-badge co2">CO₂</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value" style={{ color: "#dc2626" }}>
                      ±{(Number(uncertainty.co2) * 100).toFixed(1)}%
                    </span>
                    <span className="param-label">
                      95% CI (k=2): ±{(Number(uncertainty.co2) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.ch4 != null && (
                  <div className="uncertainty-card">
                    <span className="unc-label">
                      <span className="gas-badge ch4">CH₄</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value" style={{ color: "#0284c7" }}>
                      ±{(Number(uncertainty.ch4) * 100).toFixed(1)}%
                    </span>
                    <span className="param-label">
                      95% CI (k=2): ±{(Number(uncertainty.ch4) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
                {uncertainty.n2o != null && (
                  <div className="uncertainty-card">
                    <span className="unc-label">
                      <span className="gas-badge n2o">N₂O</span> 1σ Uncertainty
                    </span>
                    <span className="unc-value" style={{ color: "#9333ea" }}>
                      ±{(Number(uncertainty.n2o) * 100).toFixed(1)}%
                    </span>
                    <span className="param-label">
                      95% CI (k=2): ±{(Number(uncertainty.n2o) * 200).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Final Results */}
          <div className="calc-section">
            <h4 className="calc-section-title">
              <CheckCircle2 size={16} /> Computed Greenhouse Gas Inventory
            </h4>
            <div className="results-grid">
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
            Calculations strictly adhere to API Compendium 2021, GHG Protocol Corporate Standard, and IPCC AR5/AR6 GWP metrics.
          </span>
        </div>
      </div>
    </div>
  );
};

export default CalculationDetails;
