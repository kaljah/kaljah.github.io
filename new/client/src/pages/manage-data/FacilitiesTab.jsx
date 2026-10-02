import React from 'react';
import { BOUNDARY_OPTIONS } from '../../constants';
import { Upload } from 'lucide-react';
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const FacilitiesTab = ({ ACTIVITY_LABELS, HIERARCHY, ITEMS_PER_PAGE, currentPage, exportToCSV, facilities, facilityForm, filteredFacilities, handleAddFacility, handleDeleteFacility, handleFacilityChange, setCurrentPage, setFacilityForm, setImportModal, user }) => (
<div className="manage-card glass-panel">
                                <h2 style={{ marginBottom: '8px', fontWeight: 700 }}>Active Regions</h2>
                                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Manage operational regions and their boundaries.</p>


                                {/* Add Region form */}
                                {['admin', 'superuser'].includes(user?.role) && (
                                    <>
                                        <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                                            <div className="input-group">
                                                <label>Region Name</label>
                                                <input type="text" name="name" value={facilityForm.name} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. Hassi R'Mel" />
                                            </div>
                                            <div className="input-group">
                                                <label>Activity</label>
                                                <select name="activity" value={facilityForm.activity} onChange={(e) => setFacilityForm({ ...facilityForm, activity: e.target.value, division: '' })} className="component-select">
                                                    <option value="">Select Activity</option>
                                                    {Object.keys(HIERARCHY).map(a => <option key={a} value={a}>{ACTIVITY_LABELS[a]}</option>)}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Division</label>
                                                <select name="division" value={facilityForm.division} onChange={handleFacilityChange} className="component-select" disabled={!facilityForm.activity}>
                                                    <option value="">Select Division</option>
                                                    {facilityForm.activity && HIERARCHY[facilityForm.activity] && HIERARCHY[facilityForm.activity].map(d => <option key={d} value={d}>{d}</option>)}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Field / Block</label>
                                                <input type="text" name="field" value={facilityForm.field} onChange={handleFacilityChange} className="mole-input" placeholder="Optional" />
                                            </div>
                                            <div className="input-group">
                                                <label>Location (Wilaya)</label>
                                                <input type="text" name="location" value={facilityForm.location} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. Laghouat" />
                                            </div>
                                            <div className="input-group">
                                                <label>Consolidation Approach</label>
                                                <select
                                                    name="boundary_type"
                                                    value={facilityForm.boundary_type}
                                                    onChange={(e) => setFacilityForm({ ...facilityForm, boundary_type: e.target.value, boundary_detail: '' })}
                                                    className="component-select"
                                                >
                                                    <option value="">Select Approach</option>
                                                    {Object.keys(BOUNDARY_OPTIONS).map(opt => (
                                                        <option key={opt} value={opt}>{opt}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Boundary Details</label>
                                                <select
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
                                                </select>
                                            </div>
                                            {facilityForm.boundary_type === 'Equity Share' && (
                                                <div className="input-group">
                                                    <label>Equity Share Percentage (%)</label>
                                                    <input
                                                        type="number"
                                                        step="0.01"
                                                        min="0"
                                                        max="100"
                                                        name="equity_share_pct"
                                                        value={facilityForm.equity_share_pct !== undefined ? facilityForm.equity_share_pct : ''}
                                                        onChange={(e) => setFacilityForm({ ...facilityForm, equity_share_pct: e.target.value })}
                                                        className="mole-input"
                                                        placeholder="e.g. 51.00"
                                                    />
                                                </div>
                                            )}
                                            <div className="input-group">
                                                <label>Supply Chain Segment</label>
                                                <select name="segment" value={facilityForm.segment} onChange={handleFacilityChange} className="component-select">
                                                    <option value="">Select Segment</option>
                                                    <option value="Upstream">Upstream</option>
                                                    <option value="Midstream">Midstream</option>
                                                    <option value="Downstream">Downstream</option>
                                                    <option value="Heavy Industry">Heavy Industry</option>
                                                    <option value="Utilities">Utilities</option>
                                                    <option value="Other">Other</option>
                                                </select>
                                            </div>
                                            <div className="input-group">
                                                <label>Latitude</label>
                                                <input type="number" step="any" name="latitude" value={facilityForm.latitude} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. 33.8" />
                                            </div>
                                            <div className="input-group">
                                                <label>Longitude</label>
                                                <input type="number" step="any" name="longitude" value={facilityForm.longitude} onChange={handleFacilityChange} className="mole-input" placeholder="e.g. 6.07" />
                                            </div>
                                        </div>

                                        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                                            <button className="action-btn" onClick={handleAddFacility}>Add Region</button>
                                            <button className="action-btn" onClick={() => setImportModal({ isOpen: true, type: 'facilities' })} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', fontSize: '0.9rem', width: 'auto' }}>
                                                <Upload size={16} /> Bulk Import (CSV)
                                            </button>
                                            <button className="action-btn" onClick={() => exportToCSV(facilities, 'regions_export.csv')} style={{ background: 'var(--text-secondary)' }}>Export CSV</button>
                                        </div>
                                    </>
                                )}

                                <div className="table-container" style={{ marginTop: '40px' }}>
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
                                                {['admin', 'superuser'].includes(user?.role) && <th style={{ textAlign: 'center' }}>Actions</th>}
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
                                                    <td style={{ fontSize: '0.8rem' }}>{f.latitude ? `${f.latitude}, ${f.longitude}` : 'Not Set'}</td>
                                                    {['admin', 'superuser'].includes(user?.role) && (
                                                        <td style={{ textAlign: 'center' }}>
                                                            <button
                                                                className="btn-delete"
                                                                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
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
                                                        <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
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
