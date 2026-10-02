import React from 'react';
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from '../../components/CustomDropdown';
import { PROCESS_TYPES } from '../../utils/EmissionFactors';
import { Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SourcesTab = ({ ACTIVITY_LABELS, ITEMS_PER_PAGE, currentPage, exportToCSV, facilities, filteredSources, getAvailableActivities, getAvailableDivisions, handleDeleteSource, handleSaveSource, isPrivileged, setCurrentPage, setImportModal, setSourceForm, sourceForm, sources }) => (
<div className="manage-card glass-panel">
                                <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Emission Sources Inventory</h2>
                                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Manage operational equipment and emission sources.</p>

                                <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Activity
                                            {!isPrivileged && getAvailableActivities().length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <NativeSelect
                                            value={sourceForm.activity}
                                            onChange={(e) => setSourceForm({ ...sourceForm, activity: e.target.value, division: '', facility_id: '' })}
                                            className="component-select"
                                            disabled={!isPrivileged && getAvailableActivities().length === 1}
                                        >
                                            <option value="">Select Activity</option>
                                            {getAvailableActivities().map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>)}
                                        </NativeSelect>
                                    </div>
                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Division
                                            {!isPrivileged && getAvailableDivisions(sourceForm.activity).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
                                            )}
                                        </label>
                                        <NativeSelect
                                            value={sourceForm.division}
                                            onChange={(e) => setSourceForm({ ...sourceForm, division: e.target.value, facility_id: '' })}
                                            className="component-select"
                                            disabled={!sourceForm.activity || (!isPrivileged && getAvailableDivisions(sourceForm.activity).length === 1)}
                                        >
                                            <option value="">Select Division</option>
                                            {getAvailableDivisions(sourceForm.activity).map(d => <option key={d} value={d}>{d}</option>)}
                                        </NativeSelect>
                                    </div>

                                    <div className="input-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            Region
                                            {!isPrivileged && facilities.filter(f => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1 && (
                                                <span style={{ fontSize: '0.65rem', background: '#dbeafe', color: '#1d4ed8', borderRadius: '4px', padding: '1px 5px', fontWeight: 600 }}>Auto</span>
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
                                    <div className="input-group">
                                        <label>Source Name</label>
                                        <input type="text" value={sourceForm.name} onChange={(e) => setSourceForm({ ...sourceForm, name: e.target.value })} className="mole-input" placeholder="e.g. Flare A" />
                                    </div>
                                    <div className="input-group">
                                        <label>Type</label>
                                        <NativeSelect value={sourceForm.type} onChange={(e) => setSourceForm({ ...sourceForm, type: e.target.value })} className="component-select">
                                            <option value="">Select Type</option>
                                            {Object.entries(PROCESS_TYPES).map(([val, label]) => (
                                                <option key={val} value={val}>{label}</option>
                                            ))}
                                        </NativeSelect>
                                    </div>
                                    <div className="input-group">
                                        <label>Equipment ID (Optional)</label>
                                        <input type="text" value={sourceForm.equipment_id} onChange={(e) => setSourceForm({ ...sourceForm, equipment_id: e.target.value })} className="mole-input" placeholder="e.g. COMP-001" />
                                    </div>
                                    <div className="input-group">
                                        <label>Fuel</label>
                                        <input type="text" value={sourceForm.fuel_type} onChange={(e) => setSourceForm({ ...sourceForm, fuel_type: e.target.value })} className="mole-input" />
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                    <button className="action-btn" onClick={handleSaveSource}>Add Source</button>
                                    <button className="action-btn" onClick={() => setImportModal({ isOpen: true, type: 'sources' })} style={{ background: '#10b981' }}>
                                        <Upload size={16} /> Import Sources CSV
                                    </button>
                                    <button className="action-btn" onClick={() => exportToCSV(sources, 'emission_sources.csv')} style={{ background: 'var(--text-secondary)' }}>Export CSV</button>
                                </div>


                                <div className="table-container" style={{ marginTop: '40px' }}>
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
                                                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{s.equipment_id || '-'}</td>
                                                    <td>{PROCESS_TYPES[s.type] || s.type}</td>
                                                    <td>
                                                        {(() => {
                                                            const fac = facilities.find(f => f.id === s.facility_id);
                                                            if (!fac) return s.facility_id;
                                                            return <>{fac.name}{fac.field && <span style={{ fontSize: '0.85em', color: '#9ca3af', fontWeight: 400 }}>-{fac.field}</span>}</>;
                                                        })()}
                                                    </td>
                                                    <td>{s.status}</td>
                                                    <td>
                                                        <button className="btn-delete" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleDeleteSource(s.id)}>Delete</button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {filteredSources.length === 0 && (
                                                <tr>
                                                    <td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
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
