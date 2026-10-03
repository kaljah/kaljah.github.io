import React from 'react';
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from '../../components/CustomDropdown';
import { PROCESS_TYPES } from '../../utils/EmissionFactors';
import { Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SourcesTab = ({ ACTIVITY_LABELS, ITEMS_PER_PAGE, currentPage, exportToCSV, facilities, filteredSources, getAvailableActivities, getAvailableDivisions, handleDeleteSource, handleSaveSource, isPrivileged, setCurrentPage, setImportModal, setSourceForm, sourceForm, sources }) => (
<div className="[border-radius:var(--radius-lg)]! [padding:32px]! [animation:fadeIn_0.3s_ease-out]! [@media(max-width:768px)]:[padding:18px_14px]! [@media(max-width:768px)]:[border-radius:var(--radius-lg)]! glass-panel">
                                <h2 className="mb-[8px]! font-bold!">Emission Sources Inventory</h2>
                                <p className="text-[color:var(--text-secondary)]! mb-[32px]!">Manage operational equipment and emission sources.</p>

                                <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                    <Field className="input-group" label={<>Activity
                                            {!isPrivileged && getAvailableActivities().length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}</>}>
<NativeSelect
                                            value={sourceForm.activity}
                                            onChange={(e) => setSourceForm({ ...sourceForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={!isPrivileged && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </NativeSelect>
</Field>
                                    <Field className="input-group" label={<>Division
                                            {!isPrivileged && getAvailableDivisions(sourceForm.activity).length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}</>}>
<NativeSelect
                                            value={sourceForm.division}
                                            onChange={(e) => setSourceForm({ ...sourceForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!sourceForm.activity || (!isPrivileged && getAvailableDivisions(sourceForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(sourceForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </NativeSelect>
</Field>

                                    <div className="input-group">
                                        <label className="flex! items-center! gap-[6px]!">
                                            Region
                                            {!isPrivileged && facilities.filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1 && (
                                                <span className="text-[length:0.65rem]! bg-[color:#dbeafe]! text-[color:#1d4ed8]! rounded-[4px]! p-[1px_5px]! font-semibold!">Auto</span>
                                            )}
                                        </label>
                                        <CustomDropdown
                                            options={[
                                                { value: '', label: 'Select Region' },
                                                ...facilities
                                                    .filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division)
                                                    .map(f => ({ value: f.id.toString(), label: f.name, subLabel: f.field }))
                                            ]}
                                            value={sourceForm.facility_id}
                                            onChange={(val) => setSourceForm({ ...sourceForm, facility_id: val })}
                                            placeholder="Select Region"
                                            disabled={!sourceForm.division || (!isPrivileged && facilities.filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1)}
                                        />
                                    </div>
                                    <Field className="input-group" label="Source Name">
<Input type="text" value={sourceForm.name} onChange={(e) => setSourceForm({ ...sourceForm, name: e.target.value })} placeholder="e.g. Flare A" />
</Field>
                                    <Field className="input-group" label="Type">
<NativeSelect value={sourceForm.type} onChange={(e) => setSourceForm({ ...sourceForm, type: e.target.value })} className="component-select">
                                            <option value="">Select Type</option>
                                            {Object.entries(PROCESS_TYPES).map(([val, label]) => (
                                                <option key={val} value={val}>{label}</option>
                                            ))}
                                        </NativeSelect>
</Field>
                                    <Field className="input-group" label="Equipment ID (Optional)">
<Input type="text" value={sourceForm.equipment_id} onChange={(e) => setSourceForm({ ...sourceForm, equipment_id: e.target.value })} placeholder="e.g. COMP-001" />
</Field>
                                    <Field className="input-group" label="Fuel">
<Input type="text" value={sourceForm.fuel_type} onChange={(e) => setSourceForm({ ...sourceForm, fuel_type: e.target.value })} />
</Field>
                                </div>
                                <div className="flex! gap-[12px]! mt-[20px]!">
                                    <button className="action-btn" onClick={handleSaveSource}>Add Source</button>
                                    <button className="action-btn bg-[color:#10b981]!" onClick={() => setImportModal({ isOpen: true, type: 'sources' })}>
                                        <Upload size={16} /> Import Sources CSV
                                    </button>
                                    <button className="action-btn bg-[color:var(--text-secondary)]!" onClick={() => exportToCSV(sources, 'emission_sources.csv')}>Export CSV</button>
                                </div>


                                <div className="table-container mt-[40px]!">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Equipment ID</th>
                                                <th>Type</th>
                                                <th>Region</th>
                                                <th>Status</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredSources.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(s => (
                                                <tr key={s.id}>
                                                    <td><strong>{s.name}</strong></td>
                                                    <td className="text-[color:var(--text-secondary)]! text-[length:0.85rem]!">{s.equipment_id || '-'}</td>
                                                    <td>{PROCESS_TYPES[s.type] || s.type}</td>
                                                    <td>
                                                        {(() => {
                                                            const fac = facilities.find(f => f.id === s.facility_id);
                                                            if (!fac) return s.facility_id;
                                                            return <>{fac.name}{fac.field && <span className="text-[length:0.85em]! text-[color:#9ca3af]! font-normal!">-{fac.field}</span>}</>;
                                                        })()}
                                                    </td>
                                                    <td>{s.status}</td>
                                                    <td>
                                                        <button className="btn-delete p-[4px_8px]! text-[length:0.75rem]!" onClick={() => handleDeleteSource(s.id)}>Delete</button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {filteredSources.length === 0 && (
                                                <tr>
                                                    <td colSpan="6" className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                                                        No emission sources found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredSources.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default SourcesTab;
