import React from 'react';

const BlowdownForm = ({ data, onChange }) => {
    return (
        <div className="blowdown-form">
            <h4 style={{ color: 'var(--accent-color)', marginBottom: '15px' }}>Blowdown Event (Engineering Calc)</h4>
            
            <div className="form-grid-2">
                <div className="input-group">
                    <label>
                        Physical Volume
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <input 
                            type="number" 
                            className="mole-input" 
                            value={data.blowdown_volume || ''} 
                            onChange={(e) => onChange('blowdown_volume', e.target.value)} 
                            placeholder="Vessel Vol"
                            required
                        />
                        <select 
                            className="mole-input" 
                            style={{ width: '80px' }}
                            value={data.blowdown_unit || 'm3'}
                            onChange={(e) => onChange('blowdown_unit', e.target.value)}
                        >
                            <option value="m3">m³</option>
                            <option value="ft3">ft³</option>
                            <option value="bbl">bbl</option>
                        </select>
                    </div>
                </div>

                <div className="input-group">
                    <label>
                        System Pressure (psig)
                        <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                    </label>
                    <input 
                        type="number" 
                        className="mole-input" 
                        value={data.blowdown_pressure || ''} 
                        onChange={(e) => onChange('blowdown_pressure', e.target.value)} 
                        placeholder="Before blowdown (psig)"
                        required
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
                        value={data.blowdown_events || ''} 
                        onChange={(e) => onChange('blowdown_events', e.target.value)} 
                        placeholder="Count"
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
                        placeholder="e.g. 2.5"
                    />
                </div>

                <div className="input-group">
                    <label>Flare Efficiency (%) <small style={{ color: '#6b7280' }}>(0 if vented)</small></label>
                    <input 
                        type="number" 
                        className="mole-input" 
                        value={data.control_efficiency || ''} 
                        onChange={(e) => onChange('control_efficiency', e.target.value)} 
                        placeholder="0 = Vented, 98 = Flared"
                    />
                </div>
            </div>
            <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#9ca3af' }}>
                * Standard volume is calculated by expanding the physical volume from the system pressure down to standard atmospheric pressure (14.7 psia).
            </div>
        </div>
    );
};

export default BlowdownForm;
