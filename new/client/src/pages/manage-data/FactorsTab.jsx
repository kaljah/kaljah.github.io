import React from 'react';
import { Button, Input, Textarea } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { Database, Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const FactorsTab = ({ ITEMS_PER_PAGE, currentPage, editingFactorId, factorForm, filteredFactors, handleArchiveFactor, handleDeleteFactor, handleEditFactor, handleFactorChange, handleSaveFactor, setCurrentPage, setEditingFactorId, setFactorForm, setImportModal, setWorkbench, workbench }) => (
<div className="manage-card glass-panel">
                                <div className="flex! justify-between! items-start! mb-[32px]!">
                                    <div>
                                        <h2 className="mb-[8px]! font-bold!">Custom Emission Factors</h2>
                                        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Define custom factors for specialized equipment.</p>
                                    </div>
                                    <button 
                                        className="action-btn" 
                                        onClick={() => setImportModal({ isOpen: true, type: 'custom_factors' })}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}
                                    >
                                        <Upload size={16} /> Bulk Import (CSV)
                                    </button>
                                </div>
                                {/* Create/Edit Form */}
                                <div className="grid-forms">
                                    <div className="input-group">
                                        <label>Factor Name</label>
                                        <Input
                                            type="text"
                                            name="factor_name"
                                            value={factorForm.factor_name}
                                            onChange={handleFactorChange}
                                           
                                            placeholder="e.g. Flare High Efficiency"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>Parent Fuel (Internal Reference)</label>
                                        <NativeSelect
                                            name="parent_fuel"
                                            value={factorForm.parent_fuel}
                                            onChange={(e) => setFactorForm({ ...factorForm, parent_fuel: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="">Searchable Reference...</option>
                                            <option value="Natural Gas">Natural Gas (Standard)</option>
                                            <option value="Diesel">Diesel (Generic)</option>
                                            <option value="Gasoline">Gasoline (Generic)</option>
                                            <option value="Propane">Propane (Generic)</option>
                                            <option value="Crude Oil">Crude Oil (Heavy)</option>
                                            <option value="Fuel Oil">Fuel Oil (No. 4/6)</option>
                                        </NativeSelect>
                                    </div>

                                    <div className="input-group">
                                        <label>Unit</label>
                                        <NativeSelect
                                            name="unit"
                                            value={factorForm.unit}
                                            onChange={handleFactorChange}
                                            className="component-select"
                                        >
                                            <option value="scf">scf</option>
                                            <option value="m³">m³</option>
                                            <option value="gal">gal</option>
                                            <option value="bbl">bbl</option>
                                            <option value="kg">kg</option>
                                            <option value="tonne">tonne</option>
                                        </NativeSelect>
                                    </div>
                                    <div className="input-group">
                                        <label>CO₂ Factor (kg/unit)</label>
                                        <Input
                                            type="number"
                                            name="co2_factor"
                                            value={factorForm.co2_factor}
                                            onChange={handleFactorChange}
                                           
                                            placeholder="0.0"
                                            step="0.001"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>CH₄ Factor (kg/unit)</label>
                                        <Input
                                            type="number"
                                            name="ch4_factor"
                                            value={factorForm.ch4_factor}
                                            onChange={handleFactorChange}
                                           
                                            placeholder="0.0"
                                            step="0.001"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>N₂O Factor (kg/unit)</label>
                                        <Input
                                            type="number"
                                            name="n2o_factor"
                                            value={factorForm.n2o_factor}
                                            onChange={handleFactorChange}
                                           
                                            placeholder="0.0"
                                            step="0.001"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>CO₂ Uncertainty (±%)</label>
                                        <Input type="number" name="co2_uncertainty" value={factorForm.co2_uncertainty} onChange={handleFactorChange} placeholder="e.g. 5.0" step="0.1" />
                                    </div>
                                    <div className="input-group">
                                        <label>CH₄ Uncertainty (±%)</label>
                                        <Input type="number" name="ch4_uncertainty" value={factorForm.ch4_uncertainty} onChange={handleFactorChange} placeholder="e.g. 50.0" step="0.1" />
                                    </div>
                                    <div className="input-group">
                                        <label>N₂O Uncertainty (±%)</label>
                                        <Input type="number" name="n2o_uncertainty" value={factorForm.n2o_uncertainty} onChange={handleFactorChange} placeholder="e.g. 150.0" step="0.1" />
                                    </div>
                                    <div className="input-group" style={{ gridColumn: 'span 2' }}>
                                        <label>Lab Certification / Source Reference</label>
                                        <Input
                                            type="text"
                                            name="source"
                                            value={factorForm.source || ''}
                                            onChange={handleFactorChange}
                                           
                                            placeholder="e.g. Lab GC Report #2026-ARZ-01 / ISO 17025 / EPD Ref"
                                        />
                                    </div>
                                    <div className="input-group" style={{ gridColumn: 'span 3' }}>
                                        <label>Description & Technical Justification</label>
                                        <Textarea
                                            name="description"
                                            value={factorForm.description || ''}
                                            onChange={handleFactorChange}
                                           
                                            rows="2"
                                            placeholder="Engineering justification, gas chromatography sampling conditions, or manufacturer test certificate details..."
                                            style={{ resize: 'vertical' }}
                                        />
                                    </div>
                                </div>

                                {/* EF Uncertainty Workbench */}
                                <div style={{ marginTop: '20px', padding: '20px', background: 'rgba(30, 41, 59, 0.03)', borderRadius: '12px', border: '1px solid rgba(0,0,0,0.05)' }}>
                                    <h4 style={{ margin: '0 0 15px 0', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <Database size={16} /> EF Uncertainty Workbench (ISO 14064-1 compliant)
                                    </h4>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
                                        <div className="input-group">
                                            <label style={{ fontSize: '0.8rem' }}>Meter Precision (±%)</label>
                                            <Input type="number" step="0.1" value={workbench.meter_precision} onChange={(e) => setWorkbench({ ...workbench, meter_precision: parseFloat(e.target.value) || 0 })} style={{ padding: '8px' }} />
                                        </div>
                                        <div className="input-group">
                                            <label style={{ fontSize: '0.8rem' }}>Lab Analysis (±%)</label>
                                            <Input type="number" step="0.1" value={workbench.lab_precision} onChange={(e) => setWorkbench({ ...workbench, lab_precision: parseFloat(e.target.value) || 0 })} style={{ padding: '8px' }} />
                                        </div>
                                        <div className="input-group">
                                            <label style={{ fontSize: '0.8rem' }}>GWP Standard Selection</label>
                                            <NativeSelect
                                                className="component-select"
                                                style={{ padding: '8px', fontSize: '0.85rem' }}
                                                value={workbench.gwp_uncertainty}
                                                onChange={(e) => setWorkbench({ ...workbench, gwp_uncertainty: parseFloat(e.target.value) || 0 })}
                                            >
                                                <option value="20.0">IPCC AR4 (±20.0%)</option>
                                                <option value="15.0">IPCC AR5 (±15.0%)</option>
                                                <option value="11.0">IPCC AR6 (±11.0%)</option>
                                            </NativeSelect>
                                        </div>
                                    </div>
                                    <Button
                                        variant="ghost" type="submit"
                                        style={{ marginTop: '15px', color: '#3b82f6', fontWeight: 600, fontSize: '0.85rem' }}
                                        onClick={() => {
                                            const co2_u = Math.sqrt(
                                                Math.pow(workbench.meter_precision, 2) +
                                                Math.pow(workbench.lab_precision, 2)
                                            );
                                            // IPCC typically suggests ±50% for CH4 and ±150% for N2O technology uncertainty
                                            const ch4_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(50.0, 2));
                                            const n2o_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(150.0, 2));
                                            
                                            setFactorForm({ 
                                                ...factorForm, 
                                                co2_uncertainty: co2_u.toFixed(2),
                                                ch4_uncertainty: ch4_u.toFixed(2),
                                                n2o_uncertainty: n2o_u.toFixed(2)
                                            });
                                        }}
                                    >
                                        Calculate Combined Uncertainty (SRSS)
                                    </Button>
                                </div>

                                <div className="flex! gap-[10px]! mt-[20px]!">
                                    <button className="action-btn" onClick={handleSaveFactor}>
                                        {editingFactorId ? 'Update Factor' : 'Save Factor'}
                                    </button>
                                    {editingFactorId && (
                                        <button
                                            className="action-btn"
                                            onClick={() => {
                                                setEditingFactorId(null);
                                                setFactorForm({
                                                    factor_name: '', parent_fuel: '', unit: 'scf',
                                                    co2_factor: '', ch4_factor: '', n2o_factor: '', co_factor: '', co2_uncertainty: '', ch4_uncertainty: '', n2o_uncertainty: '',
                                                    source: '', description: ''
                                                });
                                            }}
                                        >
                                            Cancel Edit
                                        </button>
                                    )}
                                </div>
                                <div className="table-container mt-[40px]!">
                                    <div className="flex! justify-between! items-center! mb-[16px]!">
                                        <h3 style={{ margin: 0 }}>Custom Factors</h3>
                                    </div>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Factor Name</th>
                                                <th>Unit</th>
                                                <th>CO2</th>
                                                <th>CH4</th>
                                                <th>N2O</th>
                                                <th>Certification / Description</th>
                                                <th>CO₂ Unc.</th>
                                                <th>CH₄ Unc.</th>
                                                <th>N₂O Unc.</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredFactors.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(f => (
                                                <tr key={f.id}>
                                                    <td><strong>{f.factor_name || f.name}</strong></td>
                                                    <td>{f.unit}</td>
                                                    <td>{f.co2_factor}</td>
                                                    <td>{f.ch4_factor}</td>
                                                    <td>{f.n2o_factor}</td>
                                                    <td style={{ maxWidth: '240px' }}>
                                                        {f.source && <span style={{ display: 'inline-block', fontSize: '0.75rem', background: '#dbeafe', color: '#1d4ed8', padding: '1px 6px', borderRadius: '4px', fontWeight: 600, marginBottom: '2px' }}>{f.source}</span>}
                                                        {f.description && <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={f.description}>{f.description}</div>}
                                                        {!f.source && !f.description && <span style={{ color: 'var(--text-secondary)' }}>—</span>}
                                                    </td>
                                                    <td style={{ color: f.co2_uncertainty ? '#10b981' : 'inherit' }}>{f.co2_uncertainty ? `±${f.co2_uncertainty}%` : '—'}</td>
                                                    <td style={{ color: f.ch4_uncertainty ? '#3b82f6' : 'inherit' }}>{f.ch4_uncertainty ? `±${f.ch4_uncertainty}%` : '—'}</td>
                                                    <td style={{ color: f.n2o_uncertainty ? '#8b5cf6' : 'inherit' }}>{f.n2o_uncertainty ? `±${f.n2o_uncertainty}%` : '—'}</td>
                                                    <td>
                                                        <button onClick={() => handleEditFactor(f)}>Edit</button>
                                                        <button onClick={() => handleArchiveFactor(f.id)} title="Hide from new entries; records that use it keep it">Archive</button>
                                                        <button onClick={() => handleDeleteFactor(f.id)}>Delete</button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {filteredFactors.length === 0 && (
                                                <tr>
                                                    <td colSpan="10" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                                                        No custom emission factors found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredFactors.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default FactorsTab;
