
import React from 'react';
import CustomDropdown from '../CustomDropdown';

// Process types that require HHV input per API Compendium 2021 Section 5
const HHV_REQUIRED_PROCESSES = ['combustion', 'stationary_combustion', 'flaring'];

const CombustionForm = ({ data, onChange, sourceType }) => {
    const isFlaring = data.process_type === 'flaring';
    const isCombustion = ['combustion', 'stationary_combustion'].includes(data.process_type);
    const needsHHV = HHV_REQUIRED_PROCESSES.includes(data.process_type);

    return (
        <div className="combustion-form">
            <div className="form-grid-2">
                <div className="input-group">
                    <label>
                        {isFlaring ? 'Gas Volume Flared' :
                            data.process_type === 'loading' ? 'Volume Loaded' :
                                data.process_type === 'separation' ? 'Volume Treated (Wastewater)' :
                                    'Fuel / Activity Quantity'}
                    </label>
                    <input
                        type="number"
                        className="mole-input"
                        value={data.amount || ''}
                        onChange={(e) => onChange('amount', e.target.value)}
                        placeholder="0.00"
                    />
                </div>

                <div className="input-group">
                    <label>Unit</label>
                    <CustomDropdown
                        options={[
                            { value: 'm3', label: 'm³' },
                            { value: 'scf', label: 'scf' },
                            { value: 'Mcf', label: 'Mcf' },
                            { value: 'MMscf', label: 'MMscf' },
                            { value: 'gal', label: 'gal' },
                            { value: 'bbl', label: 'bbl' },
                            { value: 'L', label: 'L' },
                            { value: 'kg', label: 'kg' },
                            { value: 'ton', label: 'ton (short)' },
                            { value: 'tonne', label: 'tonne (metric)' },
                        ]}
                        value={data.unit}
                        onChange={(val) => onChange('unit', val)}
                    />
                </div>
            </div>

            {/* HHV field — only required in Specific factor mode per API Compendium 2021 Section 5 */}
            {needsHHV && sourceType === 'specific' && (
                <div style={{
                    marginTop: '14px',
                    padding: '12px 14px',
                    background: 'linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%)',
                    borderRadius: '8px',
                    border: '1px solid #bfdbfe'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
                        </svg>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#1d4ed8', letterSpacing: '0.04em' }}>
                            FUEL HEATING VALUE (API Compendium 2021 §5)
                        </span>
                    </div>
                    <div className="form-grid-2" style={{ gap: '10px' }}>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: '0.75rem' }}>
                                HHV — Higher Heating Value
                                <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                            </label>
                            <input
                                id="hhv-input"
                                type="number"
                                className="mole-input"
                                value={data.hhv || ''}
                                onChange={(e) => onChange('hhv', e.target.value)}
                                placeholder={isFlaring ? 'e.g. 983 (natural gas)' : 'e.g. 1020 (BTU/scf)'}
                                style={{ borderColor: !data.hhv ? '#fbbf24' : '#d1fae5' }}
                            />
                            {!data.hhv && (
                                <span style={{ fontSize: '0.68rem', color: '#d97706', marginTop: '3px', display: 'block' }}>
                                    Required — must be fuel-specific (OGMP 2.0 / ISO 14064-1)
                                </span>
                            )}
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: '0.75rem' }}>HHV Unit</label>
                            <select
                                className="component-select"
                                value={data.hhv_unit || 'BTU/scf'}
                                onChange={(e) => onChange('hhv_unit', e.target.value)}
                            >
                                <option value="BTU/scf">BTU/scf</option>
                                <option value="BTU/ft3">BTU/ft³</option>
                                <option value="MJ/m3">MJ/m³</option>
                                <option value="MJ/kg">MJ/kg</option>
                                <option value="BTU/gal">BTU/gal</option>
                                <option value="BTU/lb">BTU/lb</option>
                                <option value="kcal/m3">kcal/m³</option>
                            </select>
                        </div>
                    </div>

                    {/* Combustion efficiency — required for stationary combustion */}
                    {isCombustion && (
                        <div className="input-group" style={{ marginTop: '10px', marginBottom: 0 }}>
                            <label style={{ fontSize: '0.75rem' }}>
                                Combustion Efficiency (η<sub>c</sub>)
                                <span style={{ color: '#ef4444', marginLeft: '3px' }}>*</span>
                            </label>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <input
                                    id="combustion-efficiency-input"
                                    type="number"
                                    className="mole-input"
                                    min="0"
                                    max="100"
                                    step="0.1"
                                    value={data.combustion_efficiency != null ? data.combustion_efficiency : ''}
                                    onChange={(e) => onChange('combustion_efficiency', e.target.value)}
                                    placeholder="e.g. 99.5"
                                    style={{
                                        flex: 1,
                                        borderColor: data.combustion_efficiency == null ? '#fbbf24' : '#d1fae5'
                                    }}
                                />
                                <span style={{ fontSize: '0.8rem', color: '#6b7280', whiteSpace: 'nowrap' }}>%</span>
                            </div>
                            {data.combustion_efficiency == null && (
                                <span style={{ fontSize: '0.68rem', color: '#d97706', marginTop: '3px', display: 'block' }}>
                                    Required — typical values: 99.5% (boiler), 98% (heater), 95% (engine)
                                </span>
                            )}
                        </div>
                    )}

                    {/* Flare type for flaring */}
                    {isFlaring && (
                        <div className="input-group" style={{ marginTop: '10px', marginBottom: 0 }}>
                            <label style={{ fontSize: '0.75rem' }}>Flare Type</label>
                            <select
                                className="component-select"
                                value={data.flare_type || 'elevated'}
                                onChange={(e) => onChange('flare_type', e.target.value)}
                            >
                                <option value="elevated">Elevated Flare (η_d=98%)</option>
                                <option value="enclosed_ground">Enclosed Ground Flare (η_d=99.5%)</option>
                                <option value="pit">Pit / Open Burn (η_d=95%)</option>
                            </select>
                        </div>
                    )}

                    {/* Operating conditions for Gas standard volume normalization */}
                    <div className="form-grid-2" style={{ gap: '10px', marginTop: '10px' }}>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: '0.75rem' }}>Operating Temp (°F)</label>
                            <input
                                type="number"
                                className="mole-input"
                                value={data.operating_temperature !== undefined ? data.operating_temperature : ''}
                                onChange={(e) => onChange('operating_temperature', e.target.value)}
                                placeholder="Def: 60°F"
                            />
                        </div>
                        <div className="input-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: '0.75rem' }}>Operating Pres. (psia)</label>
                            <input
                                type="number"
                                className="mole-input"
                                value={data.operating_pressure !== undefined ? data.operating_pressure : ''}
                                onChange={(e) => onChange('operating_pressure', e.target.value)}
                                placeholder="Def: 14.696"
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CombustionForm;
