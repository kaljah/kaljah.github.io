import React from 'react';
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from '../../components/CustomDropdown';
import { Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const ProductionTab = ({ ACTIVITY_LABELS, ITEMS_PER_PAGE, currentPage, exportToCSV, facilities, filteredProduction, getAvailableActivities, getAvailableDivisions, handleDeleteProduction, handleSaveProduction, isPrivileged, openGasConverter, openOilConverter, prodForm, productionData, setCurrentPage, setImportModal, setProdForm }) => (
<div className="[border-radius:var(--radius-lg)]! [padding:32px]! [animation:fadeIn_0.3s_ease-out]! [@media(max-width:768px)]:[padding:18px_14px]! [@media(max-width:768px)]:[border-radius:var(--radius-lg)]! glass-panel">
                                <div className="flex! justify-between! items-start! mb-[32px]!">
                                    <div>
                                        <h2 className="mb-[8px]! font-bold!">Annual Production Records</h2>
                                        <p className="text-[color:var(--text-secondary)]! m-[0px]!">Manage annual production data for emission intensity reporting.</p>
                                    </div>
                                    <button 
                                        className="action-btn" 
                                        onClick={() => setImportModal({ isOpen: true, type: 'production' })}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}
                                    >
                                        <Upload size={16} /> Bulk Import (CSV)
                                    </button>
                                </div>

                                <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                    <Field className="input-group" label={<>Activity
                                            {!isPrivileged && getAvailableActivities().length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}</>}>
<NativeSelect
                                            value={prodForm.activity}
                                            onChange={(e) => setProdForm({ ...prodForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={!isPrivileged && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </NativeSelect>
</Field>
                                    <Field className="input-group" label={<>Division
                                            {!isPrivileged && getAvailableDivisions(prodForm.activity).length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}</>}>
<NativeSelect
                                            value={prodForm.division}
                                            onChange={(e) => setProdForm({ ...prodForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!prodForm.activity || (!isPrivileged && getAvailableDivisions(prodForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(prodForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </NativeSelect>
</Field>

                                    <div className="input-group">
                                        <label className="flex! items-center! gap-[6px]!">
                                            Region
                                            {!isPrivileged && facilities.filter(f => f.activity === prodForm.activity && f.division === prodForm.division).length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}
                                        </label>
                                        <CustomDropdown
                                            options={[
                                                { value: '', label: 'Select Region' },
                                                ...facilities
                                                    .filter(f => f.activity === prodForm.activity && f.division === prodForm.division)
                                                    .map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
                                            ]}
                                            value={prodForm.facility_id}
                                            onChange={(val) => setProdForm({ ...prodForm, facility_id: val })}
                                            placeholder="Select Region"
                                            disabled={!prodForm.division || (!isPrivileged && facilities.filter(f => f.activity === prodForm.activity && f.division === prodForm.division).length === 1)}
                                        />
                                    </div>
                                    <Field className="input-group" label="Month">
<NativeSelect
                                            value={prodForm.month}
                                            onChange={(e) => setProdForm({ ...prodForm, month: parseInt(e.target.value) })}
                                            className="component-select"
                                        >
                                            {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                                <option key={m} value={m}>{new Date(2000, m - 1).toLocaleString('default', { month: 'long' })}</option>
                                            ))}
                                        </NativeSelect>
</Field>
                                    <Field className="input-group" label="Year">
<Input type="number" value={prodForm.year} onChange={(e) => setProdForm({ ...prodForm, year: e.target.value })} />
</Field>
                                    <div className="input-group">
                                        <label>Oil ({prodForm.oil_unit}) <button onClick={openOilConverter} style={{ fontSize: '0.65rem', padding: '2px 4px', marginLeft: '8px', cursor: 'pointer', background: 'var(--accent-color)', color: 'white', border: 'none', borderRadius: '3px' }}>Convert m³</button></label>
                                        <div className="flex! gap-[8px]!">
                                            <input type="number" value={prodForm.oil_amount} onChange={(e) => setProdForm({ ...prodForm, oil_amount: e.target.value })} className="mole-input flex-1!" placeholder="0.0" />
                                            <NativeSelect value={prodForm.oil_unit} onChange={(e) => setProdForm({ ...prodForm, oil_unit: e.target.value })} className="component-select w-[80px]!">
                                                <option value="bbl">bbl</option>
                                                <option value="m³">m³</option>
                                            </NativeSelect>
                                        </div>
                                    </div>
                                    <div className="input-group">
                                        <label>Gas ({prodForm.gas_unit}) <button onClick={openGasConverter} style={{ fontSize: '0.65rem', padding: '2px 4px', marginLeft: '8px', cursor: 'pointer', background: 'var(--accent-color)', color: 'white', border: 'none', borderRadius: '3px' }}>Convert m³</button></label>
                                        <div className="flex! gap-[8px]!">
                                            <input type="number" value={prodForm.gas_amount} onChange={(e) => setProdForm({ ...prodForm, gas_amount: e.target.value })} className="mole-input flex-1!" placeholder="0.0" />
                                            <NativeSelect value={prodForm.gas_unit} onChange={(e) => setProdForm({ ...prodForm, gas_unit: e.target.value })} className="component-select w-[80px]!">
                                                <option value="mscf">mscf</option>
                                                <option value="m³">m³</option>
                                            </NativeSelect>
                                        </div>
                                    </div>
                                    <Field className="input-group" label="Gross Gas (MMSm³)">
<Input type="number" step="any" value={prodForm.gross_gas_mmsm3} onChange={(e) => setProdForm({ ...prodForm, gross_gas_mmsm3: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Gas w/o Injection (MMSm³)">
<Input type="number" step="any" value={prodForm.gas_without_injected_mmsm3} onChange={(e) => setProdForm({ ...prodForm, gas_without_injected_mmsm3: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Injected Gas (MMSm³)">
<Input type="number" step="any" value={prodForm.injected_gas_mmsm3} onChange={(e) => setProdForm({ ...prodForm, injected_gas_mmsm3: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Crude Oil (MMBOE)">
<Input type="number" step="any" value={prodForm.crude_oil_mmboe} onChange={(e) => setProdForm({ ...prodForm, crude_oil_mmboe: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Condensate (MMBOE)">
<Input type="number" step="any" value={prodForm.condensate_mmboe} onChange={(e) => setProdForm({ ...prodForm, condensate_mmboe: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="LPG (MMBOE)">
<Input type="number" step="any" value={prodForm.lpg_mmboe} onChange={(e) => setProdForm({ ...prodForm, lpg_mmboe: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Total Production (MMBOE)">
<Input type="number" step="any" value={prodForm.total_production_mmboe} onChange={(e) => setProdForm({ ...prodForm, total_production_mmboe: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Total Saleable (MMBOE)">
<Input type="number" step="any" value={prodForm.saleable_production_mmboe} onChange={(e) => setProdForm({ ...prodForm, saleable_production_mmboe: e.target.value })} placeholder="0.0" />
</Field>
                                </div>
                                <div className="flex! gap-[12px]! mt-[20px]!">
                                    <button className="action-btn" onClick={handleSaveProduction}>Save Record</button>
                                </div>
                                <div className="flex! gap-[12px]! mt-[10px]!">
                                    <button className="action-btn bg-[color:var(--text-secondary)]!" onClick={() => exportToCSV(productionData, 'production_data.csv')}>Export CSV</button>
                                </div>


                                <div className="table-container mt-[40px]!">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Activity</th>
                                                <th>Division</th>
                                                <th>Region</th>
                                                <th>Year</th>
                                                <th>Month</th>
                                                <th className="text-right!">Oil (bbl)</th>
                                                <th className="text-right!">Gas (mcf)</th>
                                                <th className="text-right!">Gross Gas (MMSm³)</th>
                                                <th className="text-right!">Total (MMBOE)</th>
                                                <th className="text-right!">Saleable (MMBOE)</th>
                                                <th className="text-center!">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredProduction.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(d => (
                                                <tr key={d.id}>
                                                    <td>{ACTIVITY_LABELS[d.activity] || d.activity || '-'}</td>
                                                    <td>{d.division || '-'}</td>
                                                    <td>
                                                        {(() => {
                                                            const fac = facilities.find(f => f.id === d.facilityId);
                                                            if (!fac) return d.facilityId;
                                                            return <>{fac.name}{fac.field && <span className="text-[length:0.85em]! text-[color:#9ca3af]! font-normal!">-{fac.field}</span>}</>;
                                                        })()}
                                                    </td>
                                                    <td>{d.year}</td>
                                                    <td>{new Date(2000, d.month - 1).toLocaleString('default', { month: 'short' })}</td>
                                                    <td className="text-right!">{(d.oil || 0).toLocaleString()} {d.oilUnit || 'bbl'}</td>
                                                    <td className="text-right!">{(d.gas || 0).toLocaleString()} {d.gasUnit || 'mscf'}</td>
                                                    <td className="text-right!">{d.gross_gas_mmsm3 ? Number(d.gross_gas_mmsm3).toLocaleString(undefined, { minimumFractionDigits: 2 }) : '-'}</td>
                                                    <td className="text-right!">{d.total_production_mmboe ? Number(d.total_production_mmboe).toLocaleString(undefined, { minimumFractionDigits: 2 }) : '-'}</td>
                                                    <td className="text-right!">{d.saleable_production_mmboe ? Number(d.saleable_production_mmboe).toLocaleString(undefined, { minimumFractionDigits: 2 }) : '-'}</td>
                                                    <td className="text-center!">
                                                        <button
                                                            className="btn-delete p-[6px_12px]! text-[length:0.8rem]!"
                                                           
                                                            onClick={() => handleDeleteProduction(d.id)}
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {filteredProduction.length === 0 && (
                                                <tr>
                                                    <td colSpan="11" className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                                                        No production records found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredProduction.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default ProductionTab;
