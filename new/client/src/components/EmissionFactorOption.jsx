/**
 * Enhanced Dropdown Option Component for Emission Factors
 * Displays factor name with segment badge and uncertainty information
 */

import React from "react";
import {
  getSegmentColor,
  getSegmentBgColor,
  formatUncertainty,
} from "../utils/emissionFactorsAPI";
import { API_FACTORS } from "../utils/EmissionFactors";

const EmissionFactorOption = ({
  factorKey,
  showSegment = true,
  showUncertainty = true,
}) => {
  const factor = API_FACTORS[factorKey];

  if (!factor) return factorKey;

  const segment = factor.segment || factor.stream;
  const uncertainty = factor.uncertainty;

  return (
    <div
      className="flex! items-center! justify-between! w-full!"
    >
      <div
        className="flex! items-center! gap-[8px]! flex-1!"
      >
        <span>{factorKey}</span>
        {showSegment && segment && (
          <span
            style={{
              padding: "2px 6px",
              borderRadius: "3px",
              fontSize: "0.65rem",
              fontWeight: 600,
              background: getSegmentBgColor(segment),
              color: getSegmentColor(segment),
            }}
          >
            {segment}
          </span>
        )}
      </div>
      {showUncertainty && uncertainty && (
        <span
          className="text-[length:0.7rem]! text-[color:#6b7280]! ml-[8px]!"
          title={`CO₂: ${formatUncertainty(uncertainty.co2)}, CH₄: ${formatUncertainty(uncertainty.ch4)}, N₂O: ${formatUncertainty(uncertainty.n2o)}`}
        >
          {formatUncertainty(
            Math.max(
              uncertainty.co2 || 0,
              uncertainty.ch4 || 0,
              uncertainty.n2o || 0,
            ),
          )}
        </span>
      )}
    </div>
  );
};

export default EmissionFactorOption;
