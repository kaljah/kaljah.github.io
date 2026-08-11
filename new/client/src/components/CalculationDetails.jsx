import React from "react";
import "./CalculationDetails.css";

const CalculationDetails = ({ calculation, onClose }) => {
  if (!calculation) return null;

  const {
    process_type,
    fuel,
    amount,
    unit,
    emissions,
    factors,
    method,
    steps,
  } = calculation;

  const formatNumber = (num, decimals = 3) => {
    if (num === null || num === undefined) return "0";
    return parseFloat(num).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  return (
    <div className="calc-overlay" onClick={onClose}>
      <div className="calc-modal" onClick={(e) => e.stopPropagation()}>
        <div className="calc-header">
          <h3>Calculation Details</h3>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="calc-body">
          {/* Input Summary */}
          <div className="calc-section">
            <h4>Input Parameters</h4>
            <div className="param-grid">
              <div className="param-item">
                <span className="param-label">Process Type:</span>
                <span className="param-value">{process_type}</span>
              </div>
              {fuel && (
                <div className="param-item">
                  <span className="param-label">Fuel/Source:</span>
                  <span className="param-value">{fuel}</span>
                </div>
              )}
              <div className="param-item">
                <span className="param-label">Quantity:</span>
                <span className="param-value">
                  {formatNumber(amount, 2)} {unit}
                </span>
              </div>
              <div className="param-item">
                <span className="param-label">Calculation Method:</span>
                <span className="param-value">{method || "Default"}</span>
              </div>
            </div>
          </div>

          {/* Emission Factors Used */}
          {factors && (
            <div className="calc-section">
              <h4>Emission Factors Applied</h4>
              <div className="factors-grid">
                {factors.co2 && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge co2">CO₂</span>
                      <span>Carbon Dioxide Factor</span>
                    </div>
                    <div className="factor-value">
                      {formatNumber(factors.co2, 6)} kg/{unit}
                    </div>
                  </div>
                )}
                {factors.ch4 && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge ch4">CH₄</span>
                      <span>Methane Factor</span>
                    </div>
                    <div className="factor-value">
                      {formatNumber(factors.ch4, 6)} kg/{unit}
                    </div>
                  </div>
                )}
                {factors.n2o && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge n2o">N₂O</span>
                      <span>Nitrous Oxide Factor</span>
                    </div>
                    <div className="factor-value">
                      {formatNumber(factors.n2o, 6)} kg/{unit}
                    </div>
                  </div>
                )}
                {factors.gwp_ch4 && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge gwp">GWP</span>
                      <span>CH₄ Global Warming Potential</span>
                    </div>
                    <div className="factor-value">{factors.gwp_ch4}</div>
                  </div>
                )}
                {factors.gwp_n2o && (
                  <div className="factor-item">
                    <div className="factor-label">
                      <span className="gas-badge gwp">GWP</span>
                      <span>N₂O Global Warming Potential</span>
                    </div>
                    <div className="factor-value">{factors.gwp_n2o}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Calculation Steps */}
          {steps && steps.length > 0 && (
            <div className="calc-section">
              <h4>Calculation Steps</h4>
              <div className="steps-container">
                {steps.map((step, idx) => (
                  <div key={idx} className="calc-step">
                    <div className="step-number">{idx + 1}</div>
                    <div className="step-content">
                      <div className="step-label">{step.label}</div>
                      {step.formula && (
                        <div className="step-formula">{step.formula}</div>
                      )}
                      {step.result !== undefined && (
                        <div className="step-result">
                          = {formatNumber(step.result, 6)} {step.unit || "kg"}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final Results */}
          <div className="calc-section">
            <h4>Final Emissions</h4>
            <div className="results-grid">
              <div className="result-card">
                <div className="result-label">CO₂</div>
                <div className="result-value">
                  {formatNumber(emissions?.co2 || 0)} t
                </div>
              </div>
              <div className="result-card">
                <div className="result-label">CH₄</div>
                <div className="result-value">
                  {formatNumber(emissions?.ch4 || 0)} t
                </div>
              </div>
              <div className="result-card">
                <div className="result-label">N₂O</div>
                <div className="result-value">
                  {formatNumber(emissions?.n2o || 0)} t
                </div>
              </div>
              <div className="result-card total">
                <div className="result-label">Total CO₂e</div>
                <div className="result-value">
                  {formatNumber(emissions?.totalCo2e || 0)} t
                </div>
              </div>
            </div>
          </div>

          {/* Reference */}
          <div className="calc-footer">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span>
              Calculations follow API Compendium 2021 and GHG Protocol standards
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalculationDetails;
