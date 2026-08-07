
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
                        <label>Solvent Type</label>
                        <CustomDropdown
                            options={[
                                { value: 'MEA', label: 'Monoethanolamine (MEA)' },
                                { value: 'DEA', label: 'Diethanolamine (DEA)' },
                                { value: 'MDEA', label: 'Methyldiethanolamine (MDEA)' },
                                { value: 'DGA', label: 'Diglycolamine (DGA)' },
                                { value: 'Sulfinol', label: 'Sulfinol' }
                            ]}
                            value={data.solvent_type || 'MDEA'}
                            onChange={(val) => onChange('solvent_type', val)}
                        />
                    </div>

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

                    <div className="input-group">
                        <label>Gas CH4 Content (%)</label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.ch4_mole_pct !== undefined && data.ch4_mole_pct !== null ? data.ch4_mole_pct : ''}
                            onChange={(e) => onChange('ch4_mole_pct', e.target.value)}
                            placeholder="e.g. 85.0"
                        />
                    </div>

                    <div className="input-group">
                        <label>Methane Slip Factor (mol/mol CO2)</label>
                        <input
                            type="number"
                            className="mole-input"
                            value={data.methane_slip_factor !== undefined && data.methane_slip_factor !== null ? data.methane_slip_factor : ''}
                            onChange={(e) => onChange('methane_slip_factor', e.target.value)}
                            placeholder="e.g. 0.00040 (API Table 6-5)"
                            step="0.00001"
                        />
                        <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px' }}>
                            Default: MEA=0.00035, DEA=0.00030, MDEA=0.00040, DGA=0.00035, Sulfinol=0.00095
                        </div>
                    </div>

                    <div className="checkbox-group" style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '12px' }}>
                        <input
                            type="checkbox"
                            checked={data.flash_gas_recycled || false}
                            onChange={(e) => onChange('flash_gas_recycled', e.target.checked)}
                            id="flash_gas_recycled"
                        />
                        <label htmlFor="flash_gas_recycled" style={{ margin: 0, fontWeight: 'normal' }}>
                            Flash Gas Recycled / Recovered
                        </label>
                    </div>

                    <div className="checkbox-group" style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '8px' }}>
                        <input
                            type="checkbox"
                            checked={data.offgas_to_flare || false}
                            onChange={(e) => onChange('offgas_to_flare', e.target.checked)}
                            id="offgas_to_flare"
                        />
                        <label htmlFor="offgas_to_flare" style={{ margin: 0, fontWeight: 'normal' }}>
                            Acid Gas / Offgas Routed to Flare
                        </label>
                    </div>
                </>
            )}
        </div>
    );
};

export default AGRForm;
