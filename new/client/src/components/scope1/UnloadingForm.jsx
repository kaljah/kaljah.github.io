import React from 'react';

/**
 * UnloadingForm — Engineering (Tier 3) Calculation Form
 * Rendered only when sourceType === 'specific' (controlled by Scope1Form's outer toggle).
 * The outer toggle handles Tier 1 (default catalog factor: Plunger Lift / Non-Plunger) vs
 * Specific (this engineering form using well geometry).
 */
const UnloadingForm = ({ data, onChange }) => {
    return (
        <div className="unloading-form">
            <h4 style={{ color: 'var(--accent-color)', marginBottom: '15px' }}>Liquids Unloading (Engineering Calc)</h4>

            <div className="form-grid-2">
                <div className="input-group">
                    <label>
                        Frequency (events/yr)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.unload_freq || ''}
                        onChange={(e) => onChange('unload_freq', e.target.value)}
                        placeholder="e.g. 12"
                        required
                    />
                </div>

                <div className="input-group">
                    <label>
                        Casing Diameter (in)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.unload_diam || ''}
                        onChange={(e) => onChange('unload_diam', e.target.value)}
                        placeholder="e.g. 2.375"
                        required
                    />
                </div>

                <div className="input-group">
                    <label>
                        Well Depth (ft)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.unload_depth || ''}
                        onChange={(e) => onChange('unload_depth', e.target.value)}
                        placeholder="e.g. 5000"
                        required
                    />
                </div>

                <div className="input-group">
                    <label>
                        Surface Pressure (psig)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.unload_press || ''}
                        onChange={(e) => onChange('unload_press', e.target.value)}
                        placeholder="e.g. 150"
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
                        value={data.unload_flare_eff || ''}
                        onChange={(e) => onChange('unload_flare_eff', e.target.value)}
                        placeholder="e.g. 98"
                    />
                </div>
            </div>
        </div>
    );
};

export default UnloadingForm;
