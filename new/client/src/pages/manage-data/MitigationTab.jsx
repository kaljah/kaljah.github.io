import React from 'react';
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from '../../components/CustomDropdown';
import { Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MitigationTab = ({ ACTIVITY_LABELS, ITEMS_PER_PAGE, currentPage, facilities, filteredMitigations, getAvailableActivities, getAvailableDivisions, handleDeleteMitigation, handleSaveMitigation, isPrivileged, mitigationForm, mitigations, setCurrentPage, setImportModal, setMitigationForm }) => (
<div className="[border-radius:var(--radius-lg)]! [padding:32px]! [animation:fadeIn_0.3s_ease-out]! [@media(max-width:768px)]:[padding:18px_14px]! [@media(max-width:768px)]:[border-radius:var(--radius-lg)]! glass-panel">
                                <div className="flex! justify-between! items-start! mb-[32px]!">
                                    <div>
                                        <h2 className="mb-[8px]! font-bold!">Mitigation Projects</h2>
                                        <p className="text-[color:var(--text-secondary)]! m-[0px]!">Record CCUS, RECs, and Carbon Offsets.</p>
                                    </div>
                                    <button 
                                        className="action-btn" 
                                        onClick={() => setImportModal({ isOpen: true, type: 'mitigation' })}
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
                                            value={mitigationForm.activity}
                                            onChange={(e) => setMitigationForm({ ...mitigationForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={!isPrivileged && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </NativeSelect>
</Field>
                                    <Field className="input-group" label={<>Division
                                            {!isPrivileged && getAvailableDivisions(mitigationForm.activity).length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}</>}>
<NativeSelect
                                            value={mitigationForm.division}
                                            onChange={(e) => setMitigationForm({ ...mitigationForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!mitigationForm.activity || (!isPrivileged && getAvailableDivisions(mitigationForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(mitigationForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </NativeSelect>
</Field>

                                    <div className="input-group">
                                        <label className="flex! items-center! gap-[6px]!">
                                            Region
                                            {!isPrivileged && facilities.filter(f => f.activity === mitigationForm.activity && f.division === mitigationForm.division).length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}
                                        </label>
                                        <CustomDropdown
                                            options={[
                                                { value: '', label: 'Select Region' },
                                                ...facilities
                                                    .filter(f => f.activity === mitigationForm.activity && f.division === mitigationForm.division)
                                                    .map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
                                            ]}
                                            value={mitigationForm.facility_id}
                                            onChange={(val) => setMitigationForm({ ...mitigationForm, facility_id: val })}
                                            placeholder="Select Region"
                                            disabled={!mitigationForm.division || (!isPrivileged && facilities.filter(f => f.activity === mitigationForm.activity && f.division === mitigationForm.division).length === 1)}
                                        />
                                    </div>

                                    <Field className="input-group" label="Project Name">
<Input type="text" value={mitigationForm.name} onChange={(e) => setMitigationForm({ ...mitigationForm, name: e.target.value })} placeholder="e.g. Flare Reduction Unit 1" />
</Field>

                                    <Field className="input-group" label="Year">
<Input type="number" value={mitigationForm.year} onChange={(e) => setMitigationForm({ ...mitigationForm, year: e.target.value })} />
</Field>
                                    <Field className="input-group" label="Type">
<NativeSelect value={mitigationForm.type} onChange={(e) => setMitigationForm({ ...mitigationForm, type: e.target.value })} className="component-select">
                                            <option value="CCUS">CCUS (Carbon Capture)</option>
                                            <option value="REC">REC (Renewable Energy Credit)</option>
                                            <option value="Offset">Carbon Offset</option>
                                            <option value="Efficiency">Energy Efficiency</option>
                                            <option value="Process">Process Improvement</option>
                                        </NativeSelect>
</Field>
                                    <Field className="input-group" label="Quantity (tCO₂e)">
<Input type="number" value={mitigationForm.quantity_tco2e} onChange={(e) => setMitigationForm({ ...mitigationForm, quantity_tco2e: e.target.value })} placeholder="0.0" />
</Field>
                                    <Field className="input-group" label="Status">
<NativeSelect value={mitigationForm.status} onChange={(e) => setMitigationForm({ ...mitigationForm, status: e.target.value })} className="component-select">
                                            <option value="Active">Active</option>
                                            <option value="Planned">Planned</option>
                                            <option value="Completed">Completed</option>
                                        </NativeSelect>
</Field>
                                </div>
                                <div className="flex! gap-[12px]! mt-[20px]!">
                                    <button className="action-btn" onClick={handleSaveMitigation}>Save Record</button>
                                    <button className="action-btn bg-[color:#10b981]!" onClick={() => setImportModal({ isOpen: true, type: 'mitigation' })}>
                                        <Upload size={16} /> Import Mitigation CSV
                                    </button>
                                </div>

                                <div className="table-container mt-[40px]!">
                                    <h3>Mitigation Records</h3>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Project Name</th>
                                                <th>Activity</th>
                                                <th>Region</th>
                                                <th>Year</th>
                                                <th>Type</th>
                                                <th>Status</th>
                                                <th className="text-right!">Quantity (tCO₂e)</th>
                                                <th className="text-center!">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredMitigations.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(m => (
                                                <tr key={m.id}>
                                                    <td><strong>{m.name || m.mitigation_type}</strong></td>
                                                    <td>{ACTIVITY_LABELS[m.activity] || m.activity || '-'}</td>
                                                    <td>
                                                        {m.region || '-'}
                                                        {m.division && m.division !== '-' ? <div className="text-[length:0.75rem]! text-[color:var(--text-secondary)]!">{m.division}</div> : null}
                                                    </td>
                                                    <td>{m.year}</td>
                                                    <td>{m.mitigation_type || m.type}</td>
                                                    <td>
                                                        <span className={`status-badge ${m.status?.toLowerCase() || 'active'}`}>
                                                            {m.status || 'Active'}
                                                        </span>
                                                    </td>
                                                    <td className="text-right! text-[color:#2e7d32]! font-semibold!">
                                                        -{parseFloat(m.quantity_tco2e).toLocaleString()}
                                                    </td>
                                                    <td className="text-center!">
                                                        <button
                                                            className="btn-delete p-[6px_12px]! text-[length:0.8rem]!"
                                                           
                                                            onClick={() => handleDeleteMitigation(m.id)}
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {filteredMitigations.length === 0 && (
                                                <tr>
                                                    <td colSpan="8" className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                                                        {mitigations.length === 0 ? 'No mitigation projects recorded yet.' : 'No mitigation projects found matching active filters.'}
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredMitigations.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default MitigationTab;
