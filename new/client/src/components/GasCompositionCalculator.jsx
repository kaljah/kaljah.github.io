import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';
import Modal from './Modal';
import './GasCompositionCalculator.css';

const COMPONENT_DATA = {
    'CH4': { mw: 16.04, c: 1, hhv: 55.5, lhv: 50.0, name: 'Methane (C1)' },
    'C2H6': { mw: 30.07, c: 2, hhv: 51.9, lhv: 47.5, name: 'Ethane (C2)' },
    'C3H8': { mw: 44.10, c: 3, hhv: 50.35, lhv: 46.35, name: 'Propane (C3)' },
    'iC4H10': { mw: 58.12, c: 4, hhv: 49.4, lhv: 45.6, name: 'Isobutane (iC4)' },
    'nC4H10': { mw: 58.12, c: 4, hhv: 49.5, lhv: 45.75, name: 'n-Butane (nC4)' },
    'iC5H12': { mw: 72.15, c: 5, hhv: 48.95, lhv: 45.3, name: 'Isopentane (iC5)' },
    'nC5H12': { mw: 72.15, c: 5, hhv: 49.0, lhv: 45.4, name: 'n-Pentane (nC5)' },
    'C6H14': { mw: 86.18, c: 6, hhv: 48.3, lhv: 44.7, name: 'Hexanes+ (C6+)' },
    'CO2': { mw: 44.01, c: 1, hhv: 0, lhv: 0, name: 'Carbon Dioxide (CO2)' },
    'N2O': { mw: 44.013, c: 0, hhv: 0, lhv: 0, name: 'Nitrous Oxide (N2O)' },
    'N2': { mw: 28.01, c: 0, hhv: 0, lhv: 0, name: 'Nitrogen (N2)' }
};

const GasCompositionCalculator = ({ isOpen, onClose, onApply, processType: initialProcessType = 'combustion' }) => {
    const [activeProcessType, setActiveProcessType] = useState(initialProcessType);
    const [composition, setComposition] = useState({
        CH4: '', C2H6: '', C3H8: '', iC4H10: '', nC4H10: '',
        iC5H12: '', nC5H12: '', C6H14: '', CO2: '', N2O: '', N2: ''
    });

    useEffect(() => {
        setActiveProcessType(initialProcessType);
    }, [initialProcessType]);

    const [params, setParams] = useState({
        molarVolume: 23.685,
        oxidationFactor: 1.0,
        specificCO: ''
    });
    const [results, setResults] = useState(null);
    const [saveName, setSaveName] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const handleModeChange = (mode) => {
        setActiveProcessType(mode);
        setResults(null);
        setSaveName('');

        // Update Oxidation Factor default based on mode
        setParams(prev => ({
            ...prev,
            oxidationFactor: mode === 'flaring' ? 0.98 : 1.0
        }));
    };

    const toast = useToast();

    const totalMolePct = Object.values(composition).reduce((sum, val) => sum + (parseFloat(val) || 0), 0);

    const handleCompChange = (e) => {
        const { name, value } = e.target;
        setComposition(prev => ({ ...prev, [name]: value }));
    };

    const handleParamChange = (e) => {
        const { name, value } = e.target;
        setParams(prev => ({ ...prev, [name]: value }));
    };


    const calculate = () => {
        let totalMass = 0, totalCarbonMass = 0, totalHHV = 0, totalCH4Mass = 0;

        Object.entries(composition).forEach(([key, val]) => {
            const molePct = parseFloat(val) || 0;
            if (molePct > 0) {
                const data = COMPONENT_DATA[key];
                const moles = molePct / 100;
                const mass = moles * data.mw;
                const carbonMass = moles * (data.c * 12.011);

                totalMass += mass;
                totalCarbonMass += carbonMass;
                totalHHV += mass * (data.hhv || 0);

                // Track CH4 specifically for flaring/venting
                if (key === 'CH4') {
                    totalCH4Mass += mass;
                }
            }
        });

        if (totalMass === 0) return;

        const totalMoles = totalMolePct / 100;
        const mixtureMW = totalMass / totalMoles;
        // Calculate CO2 Mass and Carbon from CO2
        const co2MolePct = parseFloat(composition.CO2) || 0;
        const co2Mass = (co2MolePct > 0) ? (co2MolePct / 100 * COMPONENT_DATA.CO2.mw) : 0;
        const co2CarbonMass = (co2MolePct > 0) ? (co2MolePct / 100 * COMPONENT_DATA.CO2.c * 12.011) : 0;

        // Hydrocarbon Carbon = Total Carbon - Carbon from CO2
        const hydrocarbonCarbonMass = totalCarbonMass - co2CarbonMass;

        const carbonMassFraction = (totalCarbonMass / totalMass) * 100;
        const hcCarbonMassFraction = (hydrocarbonCarbonMass / totalMass) * 100;

        const ch4MassFraction = (totalCH4Mass / totalMass) * 100;
        const mixtureHHV = totalHHV / totalMass;
        const density = mixtureMW / params.molarVolume;

        // Process-Specific Emission Factor Calculations
        let efCO2Mass = 0, efCH4Mass = 0, efN2OMass = 0;

        if (activeProcessType === 'combustion' || activeProcessType === 'mobile') {
            // Stationary Combustion: Complete oxidation of carbon
            // Note: Total Carbon includes CO2 carbon, which "burns" to CO2 (identity), so this is correct for total exhaust CO2
            efCO2Mass = (carbonMassFraction / 100) * params.oxidationFactor * (44.01 / 12.011);
            // Methane slip (incomplete combustion): ~0.01% of CH4 content
            efCH4Mass = (ch4MassFraction / 100) * 0.0001;
            // N2O from high-temp combustion: ~0.1 g/GJ (API default)
            efN2OMass = (mixtureHHV * 0.0001) / 1000;

        } else if (activeProcessType === 'flaring') {
            // API Compendium 2021 Section 5.1: Flaring
            const combustionEff = params.oxidationFactor || 0.98;
            const destructionEff = 0.98;

            // CO2 from combustion of hydrocarbons ONLY
            // We use hcCarbonMassFraction here to avoid double counting the CO2 component
            efCO2Mass = (hcCarbonMassFraction / 100) * combustionEff * (44.01 / 12.011);

            // CO2 already present in flare gas (Equation 5-3 second term)
            const co2MassFraction = (co2Mass / totalMass);
            efCO2Mass += co2MassFraction;

            // Unburnt CH4
            efCH4Mass = (ch4MassFraction / 100) * (1 - destructionEff);

            // N2O from high-temperature flaring
            efN2OMass = (mixtureHHV * 0.00005) / 1000;

        } else if (activeProcessType === 'venting') {
            efCO2Mass = 0;
            efCH4Mass = ch4MassFraction / 100;
            efN2OMass = 0;
        } else {
            efCO2Mass = (carbonMassFraction / 100) * params.oxidationFactor * (44.01 / 12.011);
            efCH4Mass = (ch4MassFraction / 100) * 0.0001;
            efN2OMass = (mixtureHHV * 0.0001) / 1000;
        }

        // Convert to volumetric (kg/m3)
        const efCO2Vol = density * efCO2Mass;
        const efCH4Vol = density * efCH4Mass;
        const efN2OVol = density * efN2OMass;

        setResults({
            mw: mixtureMW,
            carbonPct: carbonMassFraction,
            ch4Pct: ch4MassFraction,
            density: density,
            hhv: mixtureHHV,
            efCO2Mass: efCO2Mass,
            efCO2Vol: efCO2Vol,
            efCH4Mass: efCH4Mass,
            efCH4Vol: efCH4Vol,
            efN2OMass: efN2OMass,
            efN2OVol: efN2OVol
        });
    };

    const getStatusText = () => {
        if (totalMolePct > 100.1) return '⚠️ Over 100%';
        if (Math.abs(totalMolePct - 100) < 0.1) return '✓ Perfect 100%';
        if (totalMolePct >= 99.5 && totalMolePct <= 100.5) return '✓ Valid (~100%)';
        return `Need ${(100 - totalMolePct).toFixed(2)}%`;
    };

    const handleApply = (unit) => {
        if (!results) return;

        // Convert emission factors to requested unit
        let co2Value = 0, ch4Value = 0, n2oValue = 0;

        if (unit === 'kg/m3') {
            co2Value = results.efCO2Vol;
            ch4Value = results.efCH4Vol;
            n2oValue = results.efN2OVol;
        } else if (unit === 'kg/kg') {
            co2Value = results.efCO2Mass;
            ch4Value = results.efCH4Mass;
            n2oValue = results.efN2OMass;
        } else if (unit === 'kg/scf') {
            co2Value = results.efCO2Vol * 0.0283168;
            ch4Value = results.efCH4Vol * 0.0283168;
            n2oValue = results.efN2OVol * 0.0283168;
        } else if (unit === 'kg/gal') {
            co2Value = results.efCO2Vol * 0.00378541;
            ch4Value = results.efCH4Vol * 0.00378541;
            n2oValue = results.efN2OVol * 0.00378541;
        }

        onApply({
            co2: co2Value.toFixed(6),
            ch4: ch4Value.toFixed(6),
            n2o: n2oValue.toFixed(6),
            unit: unit,
            raw_composition: composition
        });
    };

    const handleSave = async () => {
        if (!results || !saveName.trim()) {
            toast.warning('Please calculate results and enter a name');
            return;
        }

        setIsSaving(true);
        try {
            await api.post('/custom-factors', {
                factor_name: saveName,
                co2_factor: results.efCO2Vol, // kg/m3
                ch4_factor: results.efCH4Vol, // kg/m3
                n2o_factor: results.efN2OVol, // kg/m3
                unit: 'kg/m3',
                parent_fuel: 'Natural Gas (Analysis)',
                source: 'Gas Analysis Tool',
                usage: activeProcessType // Use actual process type
            });
            toast.success('Saved to Managed Data!');
            setSaveName('');
        } catch (error) {
            console.error('Failed to save factor:', error);
            toast.error('Failed to save factor');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Gas Composition Calculator" maxWidth="1400px">
            <div className="comp-calc-container">
                <div className="comp-calc-grid">
                    {/* Left: Inputs */}
                    <div className="comp-inputs">
                        <div className="calculation-mode-selector">
                            <label>Calculation Mode:</label>
                            <div className="mode-tabs">
                                <button
                                    className={activeProcessType === 'combustion' ? 'active' : ''}
                                    onClick={() => handleModeChange('combustion')}
                                >
                                    Combustion
                                </button>
                                <button
                                    className={activeProcessType === 'flaring' ? 'active' : ''}
                                    onClick={() => handleModeChange('flaring')}
                                >
                                    Flaring
                                </button>
                            </div>
                        </div>

                        <div className="total-display-card">

                            <div className="total-info">
                                <span className="label">Total Composition:</span>
                                <span className={`value ${Math.abs(totalMolePct - 100) < 0.5 ? 'valid' : 'invalid'}`}>
                                    {totalMolePct.toFixed(2)}%
                                </span>
                            </div>
                            <span className="status-badge">{getStatusText()}</span>
                        </div>

                        <div className="component-inputs-grid">
                            {Object.entries(COMPONENT_DATA).map(([key, data]) => (
                                <div key={key} className="input-group">
                                    <label>{data.name}</label>
                                    <input
                                        type="number"
                                        name={key}
                                        value={composition[key]}
                                        onChange={handleCompChange}
                                        placeholder="0.00"
                                        step="0.01"
                                    />
                                </div>
                            ))}
                        </div>

                        <div className="params-section">
                            <h4>Operating Parameters</h4>
                            <div className="params-grid">
                                <div className="input-group">
                                    <label>Molar Volume (L/mol)</label>
                                    <input type="number" name="molarVolume" value={params.molarVolume} onChange={handleParamChange} step="0.001" />
                                </div>
                                <div className="input-group">
                                    <label>Oxidation Factor</label>
                                    <input type="number" name="oxidationFactor" value={params.oxidationFactor} onChange={handleParamChange} step="0.1" min="0" max="1" />
                                </div>
                            </div>
                        </div>

                        <button className="calc-btn" onClick={calculate} disabled={totalMolePct === 0}>
                            Calculate Results
                        </button>
                    </div>

                    {/* Right: Results */}
                    <div className="comp-results">
                        {results ? (
                            <div className="results-wrapper">
                                <div className="result-card main">
                                    <h4>Emission Factors - {activeProcessType.charAt(0).toUpperCase() + activeProcessType.slice(1)}</h4>
                                    <div className="result-row">
                                        <span>CO₂ (Mass):</span>
                                        <strong>{results.efCO2Mass.toFixed(6)} <small>kg/kg</small></strong>
                                    </div>
                                    <div className="result-row">
                                        <span>CO₂ (Volume):</span>
                                        <strong>{results.efCO2Vol.toFixed(6)} <small>kg/m³</small></strong>
                                    </div>
                                    <div className="result-row">
                                        <span>CH₄ (Mass):</span>
                                        <strong>{results.efCH4Mass.toFixed(6)} <small>kg/kg</small></strong>
                                    </div>
                                    <div className="result-row">
                                        <span>CH₄ (Volume):</span>
                                        <strong>{results.efCH4Vol.toFixed(6)} <small>kg/m³</small></strong>
                                    </div>
                                    <div className="result-row">
                                        <span>N₂O (Mass):</span>
                                        <strong>{results.efN2OMass.toFixed(6)} <small>kg/kg</small></strong>
                                    </div>
                                    <div className="result-row">
                                        <span>N₂O (Volume):</span>
                                        <strong>{results.efN2OVol.toFixed(6)} <small>kg/m³</small></strong>
                                    </div>
                                </div>

                                <div className="result-card secondary">
                                    <h4>Physical Properties</h4>
                                    <div className="result-row">
                                        <span>Mol Weight:</span>
                                        <span>{results.mw.toFixed(2)} g/mol</span>
                                    </div>
                                    <div className="result-row">
                                        <span>Carbon %:</span>
                                        <span>{results.carbonPct.toFixed(2)} wt%</span>
                                    </div>
                                    <div className="result-row">
                                        <span>CH₄ %:</span>
                                        <span>{results.ch4Pct.toFixed(2)} wt%</span>
                                    </div>
                                    <div className="result-row">
                                        <span>Density:</span>
                                        <span>{results.density.toFixed(4)} kg/m³</span>
                                    </div>
                                    <div className="result-row">
                                        <span>HHV:</span>
                                        <span>{results.hhv.toFixed(2)} MJ/kg</span>
                                    </div>
                                </div>

                                <div className="apply-actions">
                                    <h4>Apply to Form</h4>
                                    <div className="apply-buttons">
                                        <button onClick={() => handleApply('kg/m3')}>Apply as kg/m³</button>
                                        <button onClick={() => handleApply('kg/scf')}>Apply as kg/scf</button>
                                        <button onClick={() => handleApply('kg/kg')}>Apply as kg/kg</button>
                                    </div>
                                </div>

                                <div className="result-card save-section">
                                    <h4>Save to Manage Data</h4>
                                    <div className="save-input-group">
                                        <input
                                            type="text"
                                            className="mole-input"
                                            placeholder="Factor Name (e.g. Field A Gas)"
                                            value={saveName}
                                            onChange={(e) => setSaveName(e.target.value)}
                                        />
                                        <button
                                            className="btn-primary"
                                            onClick={handleSave}
                                            disabled={isSaving || !saveName}
                                            style={{ marginTop: '10px', width: '100%' }}
                                        >
                                            {isSaving ? 'Saving...' : 'Save Factor'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="no-results">
                                <span className="icon">📊</span>
                                <p>Enter composition to view results</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Modal>
    );
};

export default GasCompositionCalculator;
