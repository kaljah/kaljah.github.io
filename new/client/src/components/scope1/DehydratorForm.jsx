
import React from 'react';
import CustomDropdown from '../CustomDropdown';

const DehydratorForm = ({ data, onChange, sourceType }) => {
    // Default/Custom: Simple inputs (throughput only)
    // Specific: Full engineering calculation inputs

    const isEngineering = sourceType === 'specific';

    return (
        <div className="dehydrator-form">
            <h4 style={{ color: 'var(--accent-color)', marginBottom: '15px' }}>
                Dehydrator Settings {isEngineering && '(Engineering Calculation)'}
            </h4>

            {/* Simple Mode: Throughput Only */}
            {!isEngineering && (
                <>
                    <div className="input-group">
                        <label>Gas Throughput (MMscf/yr)</label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.dehy_throughput || ''}
                            onChange={(e) => onChange('dehy_throughput', e.target.value)}
                            placeholder="Annual throughput"
                        />
                    </div>

                </>
            )}

            {/* Engineering Mode: Full API 5.3 Inputs */}
            {isEngineering && (
                <>
                    <div className="input-group">
                        <label>
                            Gas Throughput (MMscf/yr)
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.dehy_throughput || ''}
                            onChange={(e) => onChange('dehy_throughput', e.target.value)}
                            placeholder="Volume"
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label>
                            Glycol Pump Rate
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <input
                                type="number"
                                className="mole-input"
                                value={data.dehy_pump_rate || ''}
                                onChange={(e) => onChange('dehy_pump_rate', e.target.value)}
                                placeholder="Rate"
                                style={{ flex: 1 }}
                                required
                            />
                            <div style={{ width: '100px' }}>
                                <CustomDropdown
                                    options={[
                                        { value: 'gph', label: 'gal/hr' },
                                        { value: 'lph', label: 'L/hr' },
                                        { value: 'm3h', label: 'm³/hr' }
                                    ]}
                                    value={data.dehy_pump_unit || 'gph'}
                                    onChange={(val) => onChange('dehy_pump_unit', val)}
                                />
                            </div>
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
                            value={data.dehy_ch4_content !== undefined && data.dehy_ch4_content !== null ? data.dehy_ch4_content : ''}
                            onChange={(e) => onChange('dehy_ch4_content', e.target.value)}
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
                            value={data.dehy_hours || ''}
                            onChange={(e) => onChange('dehy_hours', e.target.value)}
                            placeholder="e.g. 8760"
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label>Control Device</label>
                        <CustomDropdown
                            options={[
                                { value: 'none', label: 'No Controls' },
                                { value: 'flash', label: 'Flash Tank Separator' },
                                { value: 'condenser', label: 'Condenser' }
                            ]}
                            value={data.dehy_control || 'none'}
                            onChange={(val) => onChange('dehy_control', val)}
                        />
                    </div>

                    {data.dehy_control !== 'none' && (
                        <div className="input-group">
                            <label>Control Efficiency (%)</label>
                            <input
                                type="number"
                                className="mole-input"
                                value={data.dehy_eff || ''}
                                onChange={(e) => onChange('dehy_eff', e.target.value)}
                                placeholder="e.g. 60 (flash) or 90 (condenser)"
                            />
                        </div>
                    )}


                </>
            )}
        </div>
    );
};

export default DehydratorForm;
