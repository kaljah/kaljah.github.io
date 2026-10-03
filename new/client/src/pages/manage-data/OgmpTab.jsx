import React from 'react';
import { Input, Field } from "../../ui";
import { CircleAlert } from "lucide-react";
import { NativeSelect } from "../../ui/NativeSelect";
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const OgmpTab = ({ ACTIVITY_LABELS, ITEMS_PER_PAGE, NON_OG_ACTIVITIES, currentPage, editingOgmpId, facilities, filteredOgmp, getAvailableActivities, getAvailableDivisions, handleDeleteOgmpSurvey, handleSaveOgmpSurvey, ogmpForm, setCurrentPage, setEditingOgmpId, setOgmpForm }) => (
<div className="tab-pane active">
                                <div className="section-header mb-[24px]!">
                                    <h2>OGMP 2.0 Level 4 & 5 Top-Down / Bottom-Up Surveys</h2>
                                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
                                        Log site-level top-down measurements (satellite, aerial LiDAR, drone, ground OGI) to reconcile against inventory estimates under Oil and Gas Methane Partnership (OGMP 2.0) Level 4/5 standards.
                                    </p>
                                </div>

                                {/* O&G Scope Notice */}
                                <div style={{
                                    display: 'flex', alignItems: 'center', gap: '10px',
                                    background: '#eff6ff', border: '1px solid #bfdbfe',
                                    borderRadius: '10px', padding: '12px 16px', marginBottom: '24px'
                                }}>
                                    <CircleAlert size="18" strokeWidth="2" className="shrink-0!" aria-hidden="true" />
                                    <div>
                                        <strong style={{ color: '#1d4ed8', fontSize: '0.85rem' }}>Oil & Gas Scope Only</strong>
                                        <span style={{ color: '#3b82f6', fontSize: '0.83rem', marginLeft: '8px' }}>
                                            OGMP 2.0 applies exclusively to Oil & Gas operations (Upstream, Midstream, LNG). Heavy industry facilities (Steel, Cement, Chemicals) are not in scope.
                                        </span>
                                    </div>
                                </div>

                                <div className="form-grid-3">
                                    <Field className="input-group" label="Activity">
<NativeSelect
                                            value={ogmpForm.activity}
                                            onChange={(e) => {
                                                const act = e.target.value;
                                                const divs = getAvailableDivisions(act);
                                                const autoDiv = divs.length === 1 ? divs[0] : '';
                                                const facs = facilities.filter(f => (!act || f.activity === act) && (!autoDiv || f.division === autoDiv));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setOgmpForm({ ...ogmpForm, activity: act, division: autoDiv, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Activity (Oil &amp; Gas) --</option>
                                            {getAvailableActivities().filter(a => !NON_OG_ACTIVITIES.includes(a)).map(a => (
                                                <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>
                                            ))}
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Division">
<NativeSelect
                                            value={ogmpForm.division}
                                            onChange={(e) => {
                                                const div = e.target.value;
                                                const facs = facilities.filter(f => (!ogmpForm.activity || f.activity === ogmpForm.activity) && (!div || f.division === div));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setOgmpForm({ ...ogmpForm, division: div, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                            disabled={!ogmpForm.activity}
                                        >
                                            <option value="">-- Select Division --</option>
                                            {getAvailableDivisions(ogmpForm.activity).map(d => (
                                                <option key={d} value={d}>{d}</option>
                                            ))}
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Facility / Region *">
<NativeSelect
                                            value={ogmpForm.facility_id}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, facility_id: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="">-- Select O&amp;G Facility --</option>
                                            {facilities
                                                .filter(f =>
                                                    !NON_OG_ACTIVITIES.includes(f.activity) &&
                                                    (!ogmpForm.activity || f.activity === ogmpForm.activity) &&
                                                    (!ogmpForm.division || f.division === ogmpForm.division)
                                                )
                                                .map(f => (
                                                    <option key={f.id} value={f.id}>{f.name} ({f.location || f.field || 'General'})</option>
                                                ))
                                            }
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Survey Date *">
<Input
                                            type="date"
                                            value={ogmpForm.survey_date}
                                            onChange={(e) => {
                                                const dateVal = e.target.value;
                                                const yr = dateVal ? new Date(dateVal).getFullYear() : ogmpForm.year;
                                                setOgmpForm({ ...ogmpForm, survey_date: dateVal, year: yr });
                                            }}
                                           
                                        />
</Field>

                                    <Field className="input-group" label="Measurement Technology (Level 4/5) *">
<NativeSelect
                                            value={ogmpForm.survey_type}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, survey_type: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="Satellite (Sentinel-5P/MethaneSAT)">Satellite (Sentinel-5P / MethaneSAT / GHGSat)</option>
                                            <option value="Aircraft OGI / Hyperspectral">Aircraft Hyperspectral / LiDAR Aerial</option>
                                            <option value="Drone / UAV LiDAR Scanning">Drone / UAV Tunable Diode Laser (TDLAS)</option>
                                            <option value="Ground Mobile / OGI FLIR Camera">Ground Mobile / Optical Gas Imaging (OGI FLIR)</option>
                                            <option value="Fixed Continuous Sensor Array">Fixed Continuous Point Sensor Array</option>
                                            <option value="Bottom-Up Source Component Measurement">Bottom-Up High-Flow Component Sampling</option>
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Measured Emission Rate (kg CH₄ / hr) *">
<Input
                                            type="number"
                                            step="0.1"
                                            value={ogmpForm.measured_rate_kg_hr}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, measured_rate_kg_hr: e.target.value })}
                                           
                                            placeholder="0.0"
                                        />
</Field>

                                    <Field className="input-group" label="Reconciliation Status">
<NativeSelect
                                            value={ogmpForm.reconciliation_status}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, reconciliation_status: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="Reconciled">Reconciled (Within Uncertainty Margin)</option>
                                            <option value="Discrepancy Detected">Discrepancy Detected (Bottom-Up Underestimated)</option>
                                            <option value="Investigation Pending">Investigation Pending / Root Cause Analysis</option>
                                            <option value="Under Review">Under Review by Operations</option>
                                        </NativeSelect>
</Field>

                                    <div className="input-group" style={{ gridColumn: 'span 2' }}>
                                        <label>Operator Notes & Campaign Metadata</label>
                                        <Input
                                            type="text"
                                            value={ogmpForm.operator_notes}
                                            onChange={(e) => setOgmpForm({ ...ogmpForm, operator_notes: e.target.value })}
                                           
                                            placeholder="Wind speed, flight altitude, pass number, observation conditions"
                                        />
                                    </div>
                                </div>

                                <div className="flex! gap-[12px]! mt-[20px]!">
                                    <button className="action-btn" onClick={handleSaveOgmpSurvey}>
                                        {editingOgmpId ? 'Update Survey Record' : 'Save OGMP Survey'}
                                    </button>
                                    {editingOgmpId && (
                                        <button
                                            className="action-btn"
                                            style={{ background: 'var(--text-secondary)' }}
                                            onClick={() => {
                                                setEditingOgmpId(null);
                                                setOgmpForm({
                                                    id: null, activity: '', division: '', facility_id: '',
                                                    year: new Date().getFullYear(),
                                                    survey_date: new Date().toISOString().split('T')[0],
                                                    survey_type: 'Satellite (Sentinel-5P/MethaneSAT)',
                                                    measured_rate_kg_hr: '', reconciliation_status: 'Reconciled', operator_notes: ''
                                                });
                                            }}
                                        >
                                            Cancel Edit
                                        </button>
                                    )}
                                </div>

                                <div className="table-container mt-[40px]!">
                                    <div className="flex! justify-between! items-center! mb-[16px]!">
                                        <h3>OGMP 2.0 Survey Records</h3>
                                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                            Total Surveys: {filteredOgmp.length}
                                        </span>
                                    </div>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Facility</th>
                                                <th>Survey Date</th>
                                                <th>Measurement Method</th>
                                                <th className="text-right!">Measured Rate (kg CH₄/hr)</th>
                                                <th className="text-right!">Annualized (tCH₄/yr)</th>
                                                <th>Reconciliation Status</th>
                                                <th>Campaign Notes</th>
                                                <th className="text-center!">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredOgmp.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(o => {
                                                const fid = o.facility_id || o.facilityId;
                                                const fac = facilities.find(f => f.id === fid);
                                                const fName = o.facility_name || o.facilityName || fac?.name || `Facility #${fid}`;
                                                const sDate = o.survey_date || o.surveyDate || '';
                                                const sType = o.survey_type || o.surveyType || 'Satellite';
                                                const mRate = parseFloat(o.measured_rate_kg_hr ?? o.measuredRateKgHr ?? 0);
                                                const annualizedTonne = o.estimated_annual_tch4 ?? o.estimatedAnnualTch4 ?? ((mRate * 8760) / 1000.0);
                                                const rStatus = o.reconciliation_status || o.reconciliationStatus || 'Reconciled';
                                                const isReconciled = rStatus === 'Reconciled';
                                                const notes = o.operator_notes || o.operatorNotes || '-';

                                                return (
                                                    <tr key={o.id}>
                                                        <td><strong>{fName}</strong></td>
                                                        <td>{sDate}</td>
                                                        <td>
                                                            <span className="font-medium!">{sType}</span>
                                                        </td>
                                                        <td className="text-right! font-semibold!">
                                                            {mRate.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
                                                        </td>
                                                        <td style={{ textAlign: 'right', color: '#10b981', fontWeight: 700 }}>
                                                            {parseFloat(annualizedTonne).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                                                        </td>
                                                        <td>
                                                            <span className={`status-badge ${isReconciled ? 'active' : 'planned'}`} style={{
                                                                background: isReconciled ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                                                                color: isReconciled ? '#10b981' : '#ef4444',
                                                                borderColor: isReconciled ? '#10b981' : '#ef4444'
                                                            }}>
                                                                {rStatus}
                                                            </span>
                                                        </td>
                                                        <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{notes}</td>
                                                        <td className="text-center!">
                                                            <div className="flex! gap-[6px]! justify-center!">
                                                                <button
                                                                    className="action-btn"
                                                                    style={{ padding: '4px 8px', fontSize: '0.75rem', background: '#3b82f6' }}
                                                                    onClick={() => {
                                                                        setEditingOgmpId(o.id);
                                                                        setOgmpForm({
                                                                            id: o.id,
                                                                            activity: fac?.activity || '',
                                                                            division: fac?.division || '',
                                                                            facility_id: fid ? fid.toString() : '',
                                                                            year: o.year || (sDate ? new Date(sDate).getFullYear() : new Date().getFullYear()),
                                                                            survey_date: sDate,
                                                                            survey_type: sType,
                                                                            measured_rate_kg_hr: mRate.toString(),
                                                                            reconciliation_status: rStatus,
                                                                            operator_notes: notes === '-' ? '' : notes
                                                                        });
                                                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                                                    }}
                                                                >
                                                                    Edit
                                                                </button>
                                                                <button
                                                                    className="btn-delete"
                                                                    style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                                                    onClick={() => handleDeleteOgmpSurvey(o.id)}
                                                                >
                                                                    Delete
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                            {filteredOgmp.length === 0 && (
                                                <tr>
                                                    <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                                                        No OGMP survey records found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredOgmp.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default OgmpTab;
