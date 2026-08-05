
import React from 'react';
import CustomDropdown from '../CustomDropdown';

const AGRForm = ({ data, onChange, sourceType }) => {
    return (
        <div className="agr-form">
            <h4 style={{ color: 'var(--accent-color)', marginBottom: '15px' }}>Acid Gas Removal</h4>

            <div className="input-group">
                <label>
                    Gas Throughput
                    <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 130px', gap: '10px' }}>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.agr_throughput || ''}
                        onChange={(e) => onChange('agr_throughput', e.target.value)}
                        placeholder="Volume"
                        required
                    />
                    <CustomDropdown
                        options={[
                            { value: 'MMscf/yr', label: 'MMscf/yr' },
                            { value: 'MMscf/day', label: 'MMscfd' },
                            { value: 'Mcf/day', label: 'Mcf/day' },
                            { value: 'm3/yr', label: 'm³/yr' },
                        ]}
                        value={data.agr_unit || 'MMscf/yr'}
                        onChange={(val) => onChange('agr_unit', val)}
                    />
                </div>
            </div>

            {sourceType === 'specific' && (
                <>
                    <div className="input-group">
                        <label>
                            Inlet CO2 (%)
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.agr_co2_in !== undefined && data.agr_co2_in !== null ? data.agr_co2_in : ''}
                            onChange={(e) => onChange('agr_co2_in', e.target.value)}
                            placeholder="e.g. 5.0"
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label>
                            Outlet CO2 (%)
                            <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                        </label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.agr_co2_out !== undefined && data.agr_co2_out !== null ? data.agr_co2_out : ''}
                            onChange={(e) => onChange('agr_co2_out', e.target.value)}
                            placeholder="e.g. 0.05"
                            required
                        />
                    </div>
                </>
            )}
        </div>
    );
};

export default AGRForm;
