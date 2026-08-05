import React from 'react';
import CustomDropdown from '../CustomDropdown';

/**
 * CompletionsForm — Engineering (Tier 3) Calculation Form
 * Rendered only when sourceType === 'specific' (controlled by Scope1Form's outer toggle).
 * The outer toggle handles Tier 1 (default catalog factor) vs Specific (this form).
 */
const CompletionsForm = ({ data, onChange }) => {
    return (
        <div className="completions-form">
            <h4 style={{ color: 'var(--accent-color)', marginBottom: '15px' }}>Completions / Flowback (Engineering Calc)</h4>

            <div className="form-grid-2">
                <div className="input-group">
                    <label>
                        Flowback Duration (hrs)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.comp_duration || ''}
                        onChange={(e) => onChange('comp_duration', e.target.value)}
                        placeholder="e.g. 24"
                        required
                    />
                </div>

                <div className="input-group">
                    {/* BUG-UI-03 FIX: Explicit Mcf/hr label to prevent scf/hr entry (100× error) */}
                    <label>
                        Avg Gas Rate
                        <span style={{ marginLeft: '6px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-color)' }}>
                            (Mcf/hr)
                        </span>
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        <span
                            style={{ marginLeft: '4px', fontSize: '0.7rem', color: '#6b7280', cursor: 'help' }}
                            title="Enter the average flowback rate in Mcf/hr (thousand cubic feet per hour). Do NOT enter in scf/hr — that would give a 1000× error."
                        >ⓘ</span>
                    </label>
                    <input
                        type="number"
                        min="0"
                        className="mole-input"
                        value={data.comp_rate || ''}
                        onChange={(e) => {
                            const val = parseFloat(e.target.value);
                            if (val > 10000) {
                                alert(`Warning: ${val.toLocaleString()} Mcf/hr is an unusually high flowback rate. Did you mean ${val.toLocaleString()} scf/hr? If so, enter ${(val / 1000).toFixed(2)} Mcf/hr instead.`);
                            }
                            onChange('comp_rate', e.target.value);
                        }}
                        placeholder="e.g. 0.5"
                        required
                    />
                </div>

                <div className="input-group">
                    <label>
                        Gas CH4 Content (%)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ''}
                        onChange={(e) => onChange('ch4_content', e.target.value)}
                        placeholder="e.g. 85"
                        required
                    />
                </div>

                <div className="input-group">
                    <label>Gas CO2 Content (%)</label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.co2_content || ''}
                        onChange={(e) => onChange('co2_content', e.target.value)}
                        placeholder="e.g. 2"
                    />
                </div>

                <div className="input-group">
                    <label>Flare Efficiency (%) <small style={{ color: '#6b7280' }}>(0 if vented)</small></label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.comp_flare_eff || ''}
                        onChange={(e) => onChange('comp_flare_eff', e.target.value)}
                        placeholder="e.g. 98"
                    />
                </div>

                <div className="input-group">
                    <label>
                        Number of Events
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.amount || ''}
                        onChange={(e) => onChange('amount', e.target.value)}
                        placeholder="e.g. 1"
                        required
                    />
                </div>
            </div>
        </div>
    );
};

export default CompletionsForm;
