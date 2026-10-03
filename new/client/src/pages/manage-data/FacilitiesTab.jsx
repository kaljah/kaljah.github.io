import React from 'react';
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { BOUNDARY_OPTIONS } from '../../constants';
import { Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const FacilitiesTab = ({ ACTIVITY_LABELS, HIERARCHY, ITEMS_PER_PAGE, currentPage, exportToCSV, facilities, facilityForm, filteredFacilities, handleAddFacility, handleDeleteFacility, handleFacilityChange, setCurrentPage, setFacilityForm, setImportModal, user }) => (
<div className="[border-radius:var(--radius-lg)]! [padding:32px]! [animation:fadeIn_0.3s_ease-out]! [@media(max-width:768px)]:[padding:18px_14px]! [@media(max-width:768px)]:[border-radius:var(--radius-lg)]! glass-panel">
                                <h2 className="mb-[8px]! font-bold!">Active Regions</h2>
                                <p className="text-[color:var(--text-secondary)]! mb-[32px]!">Manage operational regions and their boundaries.</p>


                                {/* Add Region form */}
                                {['admin', 'superuser'].includes(user?.role) && (
                                    <>
                                        <div className="[display:grid]! [grid-template-columns:1fr_1fr] [gap:20px] [margin-bottom:24px]! [&_select.component-select]:[height:48px]! [&_select.component-select]:[width:100%]! [@media(max-width:768px)]:[grid-template-columns:1fr]! [@media(max-width:768px)]:[gap:14px]!" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                            <Field className="input-group" label="Region Name">
<Input type="text" name="name" value={facilityForm.name} onChange={handleFacilityChange} placeholder="e.g. Hassi R'Mel" />
</Field>
                                            <Field className="input-group" label="Activity">
<NativeSelect name="activity" value={facilityForm.activity} onChange={(e) => setFacilityForm({ ...facilityForm, activity: e.target.value, division: '' })} className="component-select">
                                                    <option value="">Select Activity</option>
                                                    {Object.keys(HIERARCHY).map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a]}</option>)}
                                                </NativeSelect>
</Field>
                                            <Field className="input-group" label="Division">
<NativeSelect name="division" value={facilityForm.division} onChange={handleFacilityChange} className="component-select" disabled={!facilityForm.activity}>
                                                    <option value="">Select Division</option>
                                                    {facilityForm.activity && HIERARCHY[facilityForm.activity] && HIERARCHY[facilityForm.activity].map(d => <option key={d} value={d}>{d}</option>)}
                                                </NativeSelect>
</Field>
                                            <Field className="input-group" label="Field / Block">
<Input type="text" name="field" value={facilityForm.field} onChange={handleFacilityChange} placeholder="Optional" />
</Field>
                                            <Field className="input-group" label="Location (Wilaya)">
<Input type="text" name="location" value={facilityForm.location} onChange={handleFacilityChange} placeholder="e.g. Laghouat" />
</Field>
                                            <Field className="input-group" label="Consolidation Approach">
<NativeSelect
                                                    name="boundary_type"
                                                    value={facilityForm.boundary_type}
                                                    onChange={(e) => setFacilityForm({ ...facilityForm, boundary_type: e.target.value, boundary_detail: '' })}
                                                    className="component-select"
                                                >
                                                    <option value="">Select Approach</option>
                                                    {Object.keys(BOUNDARY_OPTIONS).map(opt => (
                                                        <option key={opt} value={opt}>{opt}</option>
                                                    ))}
                                                </NativeSelect>
</Field>
                                            <Field className="input-group" label="Boundary Details">
<NativeSelect
                                                    name="boundary_detail"
                                                    value={facilityForm.boundary_detail}
                                                    onChange={(e) => setFacilityForm({ ...facilityForm, boundary_detail: e.target.value })}
                                                    className="component-select"
                                                    disabled={!facilityForm.boundary_type}
                                                >
                                                    <option value="">Select Details</option>
                                                    {facilityForm.boundary_type && BOUNDARY_OPTIONS[facilityForm.boundary_type]?.map(detail => (
                                                        <option key={detail} value={detail}>{detail}</option>
                                                    ))}
                                                </NativeSelect>
</Field>
                                            {facilityForm.boundary_type === 'Equity Share' && (
                                                <Field className="input-group" label="Equity Share Percentage (%)">
<Input
                                                        type="number"
                                                        step="0.01"
                                                        min="0"
                                                        max="100"
                                                        name="equity_share_pct"
                                                        value={facilityForm.equity_share_pct !== undefined ? facilityForm.equity_share_pct : ''}
                                                        onChange={(e) => setFacilityForm({ ...facilityForm, equity_share_pct: e.target.value })}
                                                       
                                                        placeholder="e.g. 51.00"
                                                    />
</Field>
                                            )}
                                            <Field className="input-group" label="Supply Chain Segment">
<NativeSelect name="segment" value={facilityForm.segment} onChange={handleFacilityChange} className="component-select">
                                                    <option value="">Select Segment</option>
                                                    <option value="Upstream">Upstream</option>
                                                    <option value="Midstream">Midstream</option>
                                                    <option value="Downstream">Downstream</option>
                                                    <option value="Heavy Industry">Heavy Industry</option>
                                                    <option value="Utilities">Utilities</option>
                                                    <option value="Other">Other</option>
                                                </NativeSelect>
</Field>
                                            <Field className="input-group" label="Latitude">
<Input type="number" step="any" name="latitude" value={facilityForm.latitude} onChange={handleFacilityChange} placeholder="e.g. 33.8" />
</Field>
                                            <Field className="input-group" label="Longitude">
<Input type="number" step="any" name="longitude" value={facilityForm.longitude} onChange={handleFacilityChange} placeholder="e.g. 6.07" />
</Field>
                                        </div>

                                        <div className="flex! gap-[12px]! mt-[20px]!">
                                            <button className="action-btn" onClick={handleAddFacility}>Add Region</button>
                                            <button className="action-btn" onClick={() => setImportModal({ isOpen: true, type: 'facilities' })} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}>
                                                <Upload size={16} /> Bulk Import (CSV)
                                            </button>
                                            <button className="action-btn bg-[color:var(--text-secondary)]!" onClick={() => exportToCSV(facilities, 'regions_export.csv')}>Export CSV</button>
                                        </div>
                                    </>
                                )}

                                <div className="table-container mt-[40px]!">
                                    <h3>Active Regions</h3>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Region Name</th>
                                                <th>Activity</th>
                                                <th>Division</th>
                                                <th>Location</th>
                                                <th>Boundary</th>
                                                <th>Segment</th>
                                                <th>Coordinates</th>
                                                {['admin', 'superuser'].includes(user?.role) && <th className="text-center!">Actions</th>}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredFacilities.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(f => (
                                                <tr key={f.id}>
                                                    <td><strong>{f.name}</strong></td>
                                                    <td>{ACTIVITY_LABELS[f.activity] || f.activity}</td>
                                                    <td>{f.division}</td>
                                                    <td>{f.location || '-'}</td>
                                                    <td>{f.boundary_notes || (f.boundary_type ? `${f.boundary_type}${f.boundary_detail ? ' - ' + f.boundary_detail : ''}` : '-')}</td>
                                                    <td>{f.segment || '-'}</td>
                                                    <td className="text-[length:0.8rem]!">{f.latitude ? `${f.latitude}, ${f.longitude}` : 'Not Set'}</td>
                                                    {['admin', 'superuser'].includes(user?.role) && (
                                                        <td className="text-center!">
                                                            <button
                                                                className="[background:#fee2e2]! [color:var(--color-red-700)]! [border:1px_solid_#fecaca]! [padding:6px_12px]! [border-radius:var(--radius-md)]! [cursor:pointer] [font-size:var(--text-base)]! [transition:all_0.2s]! hover:[background:var(--color-red-700)]! hover:[color:white]! p-[6px_12px]! text-[length:0.8rem]!"
                                                               
                                                                onClick={() => handleDeleteFacility(f.id)}
                                                            >
                                                                Delete
                                                            </button>
                                                        </td>
                                                    )}
                                                </tr>
                                            ))}
                                            {(filteredFacilities.length === 0) && (
                                                    <tr>
                                                        <td colSpan="8" className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                                                            No regions found.
                                                        </td>
                                                    </tr>
                                                )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredFacilities.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default FacilitiesTab;
