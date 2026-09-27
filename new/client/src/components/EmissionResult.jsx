import React from "react";
import "./EmissionResult.css";
import { UNCERTAINTY_COVERAGE_K as COVERAGE_FACTOR_95 } from "../constants";

const EmissionResult = ({ result, onClose, onEdit, onDelete }) => {
  if (!result) return null;

  const { emissions, record, calculation_method } = result;

  // BUG-098: significant-figure formatting so small CH4 / N2O masses are not shown as 0.00 t
  const formatNumber = (num) => {
    if (num === null || num === undefined || !isFinite(Number(num))) return "0";
    const n = Number(num);
    if (n === 0) return "0";
    if (Math.abs(n) >= 1) {
      return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 3 });
    }
    return n.toLocaleString("en-US", { maximumSignificantDigits: 3 });
  };

  // BUG-062: stored uncertainties are 1-sigma; the displayed band is the 95 % interval (k = 2)
  const K95 = COVERAGE_FACTOR_95;
  const formatUncertainty = (value, uncertainty) => {
    if (!uncertainty || uncertainty === 0) return null;
    return `±${formatNumber(value * uncertainty * K95)}`;
  };

  const getConfidenceInterval = (value, uncertainty) => {
    if (!uncertainty || uncertainty === 0) return null;
    const margin = value * uncertainty * K95;
    return { lower: Math.max(0, value - margin), upper: value + margin };
  };

  return (
    <div className="result-overlay" onClick={onClose}>
      <div className="result-panel" onClick={(e) => e.stopPropagation()}>
        <div className="result-header">
          <h3>Emission Calculation Result</h3>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="result-body">
          {/* Summary Card */}
          <div className="result-summary-card">
            <div className="summary-main">
              <div className="summary-total">
                <span className="total-label">Total CO₂e</span>
                <span className="total-value">
                  {formatNumber(emissions.totalCo2e)}
                </span>
                <span className="total-unit">tonnes</span>
              </div>
              <div className="calc-method">
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
                Method: {calculation_method || "Default"}
              </div>
            </div>
          </div>

          <h4>Emissions Breakdown</h4>
          <div className="breakdown-grid">
            <div className="breakdown-item co2">
              <div className="breakdown-icon">CO₂</div>
              <div className="breakdown-details">
                <span className="breakdown-label">Carbon Dioxide</span>
                <div className="breakdown-value-container">
                  <span className="breakdown-value">
                    {formatNumber(emissions.co2)} tonnes
                  </span>
                  {/* BUG-UI-10 FIX: Compute CI once, only render tooltip when CI is valid */}
                  {(() => {
                    const ci = emissions.uncertainty?.co2
                      ? getConfidenceInterval(
                          emissions.co2,
                          emissions.uncertainty.co2,
                        )
                      : null;
                    return ci ? (
                      <span
                        className="breakdown-uncertainty"
                        title={`95% confidence interval (k=2): ${formatNumber(ci.lower)} - ${formatNumber(ci.upper)} tonnes`}
                      >
                        {formatUncertainty(
                          emissions.co2,
                          emissions.uncertainty.co2,
                        )}
                      </span>
                    ) : null;
                  })()}
                </div>
              </div>
            </div>

            <div className="breakdown-item ch4">
              <div className="breakdown-icon">CH₄</div>
              <div className="breakdown-details">
                <span className="breakdown-label">Methane</span>
                <div className="breakdown-value-container">
                  <span className="breakdown-value">
                    {formatNumber(emissions.ch4)} tonnes
                  </span>
                  {(() => {
                    const ci = emissions.uncertainty?.ch4
                      ? getConfidenceInterval(
                          emissions.ch4,
                          emissions.uncertainty.ch4,
                        )
                      : null;
                    return ci ? (
                      <span
                        className="breakdown-uncertainty"
                        title={`95% confidence interval (k=2): ${formatNumber(ci.lower)} - ${formatNumber(ci.upper)} tonnes`}
                      >
                        {formatUncertainty(
                          emissions.ch4,
                          emissions.uncertainty.ch4,
                        )}
                      </span>
                    ) : null;
                  })()}
                </div>
              </div>
            </div>

            <div className="breakdown-item n2o">
              <div className="breakdown-icon">N₂O</div>
              <div className="breakdown-details">
                <span className="breakdown-label">Nitrous Oxide</span>
                <div className="breakdown-value-container">
                  <span className="breakdown-value">
                    {formatNumber(emissions.n2o)} tonnes
                  </span>
                  {(() => {
                    const ci = emissions.uncertainty?.n2o
                      ? getConfidenceInterval(
                          emissions.n2o,
                          emissions.uncertainty.n2o,
                        )
                      : null;
                    return ci ? (
                      <span
                        className="breakdown-uncertainty"
                        title={`95% confidence interval (k=2): ${formatNumber(ci.lower)} - ${formatNumber(ci.upper)} tonnes`}
                      >
                        {formatUncertainty(
                          emissions.n2o,
                          emissions.uncertainty.n2o,
                        )}
                      </span>
                    ) : null;
                  })()}
                </div>
              </div>
            </div>

            {emissions.co !== undefined && emissions.co > 0 && (
              <div className="breakdown-item co">
                <div className="breakdown-icon">CO</div>
                <div className="breakdown-details">
                  <span className="breakdown-label">Carbon Monoxide</span>
                  <span className="breakdown-value">
                    {formatNumber(emissions.co)} tonnes
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Record Details */}
        {record && (
          <div className="result-details">
            <h4>Activity Details</h4>
            <div className="details-grid">
              <div className="detail-item">
                <span className="detail-label">Process Type:</span>
                <span className="detail-value">{record.process_type}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Facility:</span>
                <span className="detail-value">
                  {record.facility_name || "N/A"}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Period:</span>
                <span className="detail-value">
                  {record.month}/{record.year}
                </span>
              </div>
              {record.fuel && (
                <div className="detail-item">
                  <span className="detail-label">Fuel/Source:</span>
                  <span className="detail-value">{record.fuel}</span>
                </div>
              )}
              {record.amount && (
                <div className="detail-item">
                  <span className="detail-label">Quantity:</span>
                  <span className="detail-value">
                    {formatNumber(record.amount)} {record.unit}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="result-actions">
          <button className="action-btn-secondary" onClick={onClose}>
            Close
          </button>
          {onEdit && (
            <button className="action-btn-secondary" onClick={onEdit}>
              Edit Record
            </button>
          )}
          {onDelete && (
            <button className="action-btn-danger" onClick={onDelete}>
              Delete Record
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmissionResult;
