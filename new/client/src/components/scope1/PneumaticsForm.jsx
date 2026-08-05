import React from 'react';
import CustomDropdown from '../CustomDropdown';

const PneumaticsForm = ({ data, onChange, sourceType }) => {
    const isEngineering = sourceType === 'specific';

    return (
        <div className="pneumatics-form">
            <h4 style={{ color: 'var(--accent-color)', marginBottom: '15px' }}>
                Pneumatic Devices {isEngineering && '(Engineering Calculation)'}
            </h4>

            {/* Device Type removed as per request */}

            <div className="input-group">
                <label>
                    Count (Number of Devices)
                    <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                </label>
                <input
                    type="number"
                    className="mole-input"
                    value={data.amount || ''}
                    onChange={(e) => onChange('amount', e.target.value)}
                    placeholder="Count"
                    required
                />
            </div>

            {/* Engineering Mode: Additional Inputs */}
            {isEngineering && (
                <>
                    <div className="input-group">
                        <label>
                            Measured Bleed Rate
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: '10px' }}>
                            <input
                                type="number"
                                className="mole-input"
                                value={data.pneu_bleed_rate || ''}
                                onChange={(e) => onChange('pneu_bleed_rate', e.target.value)}
                                placeholder="e.g. 15.4"
                                required
                            />
                            <CustomDropdown
                                options={[
                                    { value: 'scf', label: 'scf/hr' },
                                    { value: 'm3', label: 'm³/hr' }
                                ]}
                                value={data.pneu_bleed_unit || 'scf'}
                                onChange={(val) => onChange('pneu_bleed_unit', val)}
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <label>
                            Gas CH4 Content (%)
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.pneu_ch4_content !== undefined && data.pneu_ch4_content !== null ? data.pneu_ch4_content : ''}
                            onChange={(e) => onChange('pneu_ch4_content', e.target.value)}
                            placeholder="e.g. 85"
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label>
                            Operating Hours (hr/yr)
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.pneu_hours || ''}
                            onChange={(e) => onChange('pneu_hours', e.target.value)}
                            placeholder="e.g. 8760"
                            required
                        />
                    </div>
                </>
            )}


        </div>
    );
};

export default PneumaticsForm;
