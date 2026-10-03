import React from 'react';
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import PaginationControls from './PaginationControls';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const CbamTab = ({ ACTIVITY_LABELS, ITEMS_PER_PAGE, cbamForm, currentPage, editingCbamId, facilities, filteredCbam, getAvailableActivities, getAvailableDivisions, handleDeleteCbamExport, handleSaveCbamExport, setCbamForm, setCurrentPage, setEditingCbamId }) => (
<div className="tab-pane active">
                                <div className="section-header mb-[24px]!">
                                    <h2>EU CBAM Export & Embedded Emission Tracking</h2>
                                    <p className="text-[color:var(--text-secondary)]! mt-[4px]!">
                                        Record product exports subject to EU Carbon Border Adjustment Mechanism (CBAM) with direct and indirect embedded emissions under EU Regulation (EU) 2023/956.
                                    </p>
                                </div>

                                <div className="form-grid-3 [display:grid]! [grid-template-columns:repeat(3,_1fr)] [gap:20px] [margin-bottom:20px]! [@media(max-width:600px)]:[grid-template-columns:1fr]! [@media(max-width:600px)]:[gap:12px]!">
                                    <Field className="input-group" label="Activity">
<NativeSelect
                                            value={cbamForm.activity}
                                            onChange={(e) => {
                                                const act = e.target.value;
                                                const divs = getAvailableDivisions(act);
                                                const autoDiv = divs.length === 1 ? divs[0] : '';
                                                const facs = facilities.filter(f => (!act || f.activity === act) && (!autoDiv || f.division === autoDiv));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setCbamForm({ ...cbamForm, activity: act, division: autoDiv, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Activity --</option>
                                            {getAvailableActivities().map(a => (
                                                <option key={a} value={a}>{ACTIVITY_LABELS[a] || a}</option>
                                            ))}
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Division">
<NativeSelect
                                            value={cbamForm.division}
                                            onChange={(e) => {
                                                const div = e.target.value;
                                                const facs = facilities.filter(f => (!cbamForm.activity || f.activity === cbamForm.activity) && (!div || f.division === div));
                                                const autoFac = facs.length === 1 ? facs[0].id.toString() : '';
                                                setCbamForm({ ...cbamForm, division: div, facility_id: autoFac });
                                            }}
                                            className="component-select"
                                            disabled={!cbamForm.activity}
                                        >
                                            <option value="">-- Select Division --</option>
                                            {getAvailableDivisions(cbamForm.activity).map(d => (
                                                <option key={d} value={d}>{d}</option>
                                            ))}
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Facility / Region *">
<NativeSelect
                                            value={cbamForm.facility_id}
                                            onChange={(e) => setCbamForm({ ...cbamForm, facility_id: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="">-- Select Facility --</option>
                                            {facilities
                                                .filter(f => (!cbamForm.activity || f.activity === cbamForm.activity) && (!cbamForm.division || f.division === cbamForm.division))
                                                .map(f => (
                                                    <option key={f.id} value={f.id}>{f.name} ({f.location || f.field || 'General'})</option>
                                                ))
                                            }
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Product Name *">
<Input
                                            type="text"
                                            value={cbamForm.product_name}
                                            onChange={(e) => setCbamForm({ ...cbamForm, product_name: e.target.value })}
                                           
                                            placeholder="e.g. Export Blend Crude Oil"
                                        />
</Field>

                                    <Field className="input-group" label="EU CN Code *">
<NativeSelect
                                            value={cbamForm.cn_code}
                                            onChange={(e) => setCbamForm({ ...cbamForm, cn_code: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="2709 00">2709 00 - Crude Petroleum Oil</option>
                                            <option value="2711 11">2711 11 - Natural Gas (Liquefied / LNG)</option>
                                            <option value="2711 21">2711 21 - Natural Gas (Gaseous / Pipeline)</option>
                                            <option value="2710 12">2710 12 - Light Oils & Preparations</option>
                                            <option value="2710 19">2710 19 - Heavy Oils / Diesel / Gas Oil</option>
                                            <option value="2814 10">2814 10 - Anhydrous Ammonia</option>
                                            <option value="2901 21">2901 21 - Ethylene / Petrochemicals</option>
                                            <option value="3102 10">3102 10 - Urea & Nitrogenous Fertilizers</option>
                                            <option value="Custom">Custom / Other CN Code</option>
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Export Destination">
<NativeSelect
                                            value={cbamForm.export_destination}
                                            onChange={(e) => setCbamForm({ ...cbamForm, export_destination: e.target.value })}
                                            className="component-select"
                                        >
                                            <option value="EU">European Union (EU-27)</option>
                                            <option value="UK">United Kingdom</option>
                                            <option value="US">United States</option>
                                            <option value="APAC">Asia-Pacific</option>
                                            <option value="Non-EU">Other Non-EU</option>
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Reporting Year">
<Input
                                            type="number"
                                            value={cbamForm.year}
                                            onChange={(e) => setCbamForm({ ...cbamForm, year: e.target.value })}
                                           
                                        />
</Field>

                                    <Field className="input-group" label="Reporting Month">
<NativeSelect
                                            value={cbamForm.month}
                                            onChange={(e) => setCbamForm({ ...cbamForm, month: e.target.value })}
                                            className="component-select"
                                        >
                                            {Array.from({ length: 12 }, (_, i) => (
                                                <option key={i + 1} value={i + 1}>
                                                    {new Date(2000, i).toLocaleString('default', { month: 'long' })}
                                                </option>
                                            ))}
                                        </NativeSelect>
</Field>

                                    <Field className="input-group" label="Export Quantity (Metric Tonnes) *">
<Input
                                            type="number"
                                            value={cbamForm.quantity_tonnes}
                                            onChange={(e) => setCbamForm({ ...cbamForm, quantity_tonnes: e.target.value })}
                                           
                                            placeholder="0.00"
                                        />
</Field>

                                    <Field className="input-group" label="Direct Specific Embedded (tCO₂e / t)">
<Input
                                            type="number"
                                            step="0.001"
                                            value={cbamForm.specific_embedded_direct}
                                            onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_direct: e.target.value })}
                                           
                                            placeholder="0.000"
                                        />
</Field>

                                    <Field className="input-group" label="Indirect Specific Embedded (tCO₂e / t)">
<Input
                                            type="number"
                                            step="0.001"
                                            value={cbamForm.specific_embedded_indirect}
                                            onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_indirect: e.target.value })}
                                           
                                            placeholder="0.000"
                                        />
</Field>

                                    <Field className="input-group" label="Notes & Verification References">
<Input
                                            type="text"
                                            value={cbamForm.notes}
                                            onChange={(e) => setCbamForm({ ...cbamForm, notes: e.target.value })}
                                           
                                            placeholder="Accredited Verifier / Certificate ID"
                                        />
</Field>
                                </div>

                                <div className="flex! gap-[12px]! mt-[20px]!">
                                    <button className="action-btn" onClick={handleSaveCbamExport}>
                                        {editingCbamId ? 'Update CBAM Record' : 'Save CBAM Record'}
                                    </button>
                                    {editingCbamId && (
                                        <button
                                            className="action-btn bg-[color:var(--text-secondary)]!"
                                           
                                            onClick={() => {
                                                setEditingCbamId(null);
                                                setCbamForm({
                                                    id: null, activity: '', division: '', facility_id: '',
                                                    year: new Date().getFullYear(), month: 1,
                                                    product_name: 'Crude Petroleum Oil', cn_code: '2709 00',
                                                    quantity_tonnes: '', export_destination: 'EU',
                                                    specific_embedded_direct: '', specific_embedded_indirect: '', notes: ''
                                                });
                                            }}
                                        >
                                            Cancel Edit
                                        </button>
                                    )}
                                </div>

                                <div className="table-container mt-[40px]!">
                                    <div className="flex! justify-between! items-center! mb-[16px]!">
                                        <h3>CBAM Product Export Records</h3>
                                        <span className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
                                            Total Records: {filteredCbam.length}
                                        </span>
                                    </div>
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Facility</th>
                                                <th>Product</th>
                                                <th>EU CN Code</th>
                                                <th>Period</th>
                                                <th>Destination</th>
                                                <th className="text-right!">Quantity (t)</th>
                                                <th className="text-right!">Direct (tCO₂e/t)</th>
                                                <th className="text-right!">Indirect (tCO₂e/t)</th>
                                                <th className="text-right!">Total Embedded (tCO₂e)</th>
                                                <th className="text-center!">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredCbam.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map(c => {
                                                const fid = c.facility_id || c.facilityId;
                                                const fac = facilities.find(f => f.id === fid);
                                                const fName = c.facility_name || c.facilityName || fac?.name || `Facility #${fid}`;
                                                const pName = c.product_name || c.productName || 'Product';
                                                const cn = c.cn_code || c.cnCode || '-';
                                                const dest = c.export_destination || c.exportDestination || 'EU';
                                                const qTonnes = parseFloat(c.quantity_tonnes ?? c.quantityTonnes ?? 0);
                                                const direct = parseFloat(c.specific_embedded_direct ?? c.specificEmbeddedDirect ?? 0);
                                                const indirect = parseFloat(c.specific_embedded_indirect ?? c.specificEmbeddedIndirect ?? 0);
                                                const totalEmbedded = (direct + indirect) * qTonnes;
                                                return (
                                                    <tr key={c.id}>
                                                        <td><strong>{fName}</strong></td>
                                                        <td>{pName}</td>
                                                        <td><span className="font-mono! bg-[color:var(--bg-card)]! p-[2px_6px]! rounded-[4px]!">{cn}</span></td>
                                                        <td>{c.year} - M{c.month || '1'}</td>
                                                        <td><span className="status-badge [font-size:var(--text-sm)]! [padding:4px_12px]! [border-radius:var(--radius-lg)]! [background:rgba(255,_255,_255,_0.05)]! [color:var(--text-secondary)]! active">{dest}</span></td>
                                                        <td className="text-right! font-semibold!">{qTonnes.toLocaleString()}</td>
                                                        <td className="text-right!">{direct.toFixed(3)}</td>
                                                        <td className="text-right!">{indirect.toFixed(3)}</td>
                                                        <td className="text-right! text-[color:#1d4ed8]! font-bold!">
                                                            {totalEmbedded.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                                                        </td>
                                                        <td className="text-center!">
                                                            <div className="flex! gap-[6px]! justify-center!">
                                                                <button
                                                                    className="action-btn p-[4px_8px]! text-[length:0.75rem]! bg-[color:#3b82f6]!"
                                                                   
                                                                    onClick={() => {
                                                                        setEditingCbamId(c.id);
                                                                        setCbamForm({
                                                                            id: c.id,
                                                                            activity: fac?.activity || '',
                                                                            division: fac?.division || '',
                                                                            facility_id: fid ? fid.toString() : '',
                                                                            year: c.year,
                                                                            month: c.month || 1,
                                                                            product_name: pName,
                                                                            cn_code: cn,
                                                                            quantity_tonnes: qTonnes.toString(),
                                                                            export_destination: dest,
                                                                            specific_embedded_direct: direct ? direct.toString() : '',
                                                                            specific_embedded_indirect: indirect ? indirect.toString() : '',
                                                                            notes: c.notes || ''
                                                                        });
                                                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                                                    }}
                                                                >
                                                                    Edit
                                                                </button>
                                                                <button
                                                                    className="[background:#fee2e2]! [color:var(--color-red-700)]! [border:1px_solid_#fecaca]! [padding:6px_12px]! [border-radius:var(--radius-md)]! [cursor:pointer] [font-size:var(--text-base)]! [transition:all_0.2s]! hover:[background:var(--color-red-700)]! hover:[color:white]! p-[4px_8px]! text-[length:0.75rem]!"
                                                                   
                                                                    onClick={() => handleDeleteCbamExport(c.id)}
                                                                >
                                                                    Delete
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                            {filteredCbam.length === 0 && (
                                                <tr>
                                                    <td colSpan="10" className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                                                        No CBAM product export records found.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                    <PaginationControls currentPage={currentPage} totalItems={filteredCbam.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />
                                </div>
                            </div>
);

export default CbamTab;
