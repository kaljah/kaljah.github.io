/**
 * Enhanced Dropdown Option Component for Emission Factors
 * Displays factor name with segment badge and uncertainty information
 */

import React from 'react';
import { getSegmentColor, getSegmentBgColor, formatUncertainty, getFactorUncertainty } from '../utils/emissionFactorsAPI';
import { API_FACTORS } from '../utils/EmissionFactors';

const EmissionFactorOption = ({ factorKey, showSegment = true, showUncertainty = true }) => {
    const factor = API_FACTORS[factorKey];

    if (!factor) return factorKey;

    const segment = factor.segment || factor.stream;
    const uncertainty = factor.uncertainty;

    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                <span>{factorKey}</span>
                {showSegment && segment && (
                    <span
                        style={{
                            padding: '2px 6px',
                            borderRadius: '3px',
                            fontSize: '0.65rem',
                            fontWeight: 600,
                            background: getSegmentBgColor(segment),
                            color: getSegmentColor(segment)
                        }}
                    >
                        {segment}
                    </span>
                )}
            </div>
            {showUncertainty && uncertainty && (
                <span
                    style={{
                        fontSize: '0.7rem',
                        color: '#6b7280',
                        marginLeft: '8px'
                    }}
                    title={`CO₂: ${formatUncertainty(uncertainty.co2)}, CH₄: ${formatUncertainty(uncertainty.ch4)}, N₂O: ${formatUncertainty(uncertainty.n2o)}`}
                >
                    {formatUncertainty(Math.max(uncertainty.co2 || 0, uncertainty.ch4 || 0, uncertainty.n2o || 0))}
                </span>
            )}
        </div>
    );
};

export default EmissionFactorOption;
