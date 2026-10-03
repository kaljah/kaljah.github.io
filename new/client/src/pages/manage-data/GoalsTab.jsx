import React from 'react';
import { Button, Input, Textarea, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { Calendar, Check, CheckCircle, History, Plus, Target } from 'lucide-react';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const GoalsTab = ({ baseYearForm, baseYearsData, editingGoalYear, filteredBaseYears, filteredGoals, goalForm, goals, handleDeleteBaseYearRecalc, handleDeleteGoal, handleEditGoal, handleSaveBaseYear, handleSaveGoal, handleSaveSbti, hasSbti, sbtiConfig, setBaseYearForm, setEditingGoalYear, setGoalForm, setSbtiConfig }) => (
<div className="[border-radius:var(--radius-lg)]! [padding:32px]! [animation:fadeIn_0.3s_ease-out]! [@media(max-width:768px)]:[padding:18px_14px]! [@media(max-width:768px)]:[border-radius:var(--radius-lg)]! glass-panel">
                                {/* Active Baseline Status Banner */}
                                <div className="[background:linear-gradient(_135deg,_rgba(255,_102,_0,_0.06),_rgba(255,_153,_51,_0.02)_)]! [border:1px_solid_rgba(255,_102,_0,_0.2)]! [&&]:[border-radius:var(--radius-lg)]! [padding:20px]! [margin-bottom:24px]! [display:flex]! [justify-content:space-between] [align-items:center] [flex-wrap:wrap] [gap:16px]">
                                    <div>
                                        <div className="flex! items-center! gap-[8px]! mb-[6px]!">
                                            <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-link)', fontWeight: 700 }}>
                                                GHG Protocol & OGMP 2.0 Baseline
                                            </span>
                                            <span className="goal-badge [background:var(--color-green-50)]! [color:var(--color-green-700)]! [border:1px_solid_#a7f3d0]!">
                                                <CheckCircle size={12} /> Active Baseline
                                            </span>
                                        </div>
                                        <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                                            Current Base Year: {baseYearsData.active_year || '2023'}
                                        </div>
                                        {baseYearsData.active_record?.reason && (
                                            <div className="text-[length:0.88rem]! text-[color:var(--text-secondary)]! mt-[4px]!">
                                                <span className="font-semibold!">Active Justification:</span> {baseYearsData.active_record.reason}
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex! gap-[20px]! items-center!">
                                        <div className="text-right!">
                                            <div className="text-[length:0.8rem]! text-[color:var(--text-secondary)]! font-semibold!">ANNUAL TARGETS SET</div>
                                            <div className="text-[length:1.3rem]! font-bold! text-[color:var(--text-primary)]!">{goals.length} Years</div>
                                        </div>
                                        {baseYearsData.active_record?.recalc_date && (
                                            <div style={{ textAlign: 'right', borderLeft: '1px solid var(--border-color)', paddingLeft: '16px' }}>
                                                <div className="text-[length:0.8rem]! text-[color:var(--text-secondary)]! font-semibold!">LAST RECALCULATED</div>
                                                <div className="text-[length:0.95rem]! font-semibold! text-[color:var(--text-primary)]!">
                                                    {new Date(baseYearsData.active_record.recalc_date).toLocaleDateString()}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Section 1: Yearly Emission Goals */}
                                <div className="mb-[40px]!">
                                    <div className="flex! justify-between! items-start! mb-[20px]!">
                                        <div>
                                            <h2 className="mb-[6px]! font-bold! flex! items-center! gap-[8px]!">
                                                <Target size={22} color="var(--accent-color, #ff6600)" /> Yearly Emission Goals
                                            </h2>
                                            <p className="text-[color:var(--text-secondary)]! m-[0px]! text-[length:0.9rem]!">
                                                Configure annual corporate emission limits and target pathways (tCO₂e) to monitor reduction trajectory.
                                            </p>
                                        </div>
                                    </div>

                                    {/* Goal Input Form */}
                                    <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)', background: '#fafafa', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                                        <Field className="input-group" label="Target Year">
<Input
                                                type="number"
                                                min="1990"
                                                max="2100"
                                                value={goalForm.year}
                                                onChange={(e) => setGoalForm({ ...goalForm, year: e.target.value })}
                                               
                                                placeholder="e.g. 2030"
                                            />
</Field>
                                        <Field className="input-group" label="Target Emission Amount (tCO₂e)">
<Input
                                                type="number"
                                                step="any"
                                                value={goalForm.target_amount}
                                                onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                                               
                                                placeholder="e.g. 150000"
                                            />
</Field>
                                        <div className="input-group flex! items-end! gap-[8px]!">
                                            <button
                                                className="action-btn flex-1! p-[12px_16px]! h-[46px]! flex! items-center! justify-center! gap-[6px]!"
                                                onClick={handleSaveGoal}
                                               
                                            >
                                                <Plus size={16} /> {editingGoalYear ? 'Update Goal' : 'Save Goal'}
                                            </button>
                                            {editingGoalYear && (
                                                <Button
                                                    variant="ghost" type="submit"
                                                    onClick={() => {
                                                        setEditingGoalYear(null);
                                                        setGoalForm({ year: new Date().getFullYear(), target_amount: '' });
                                                    }}
                                                    style={{ height: '46px', padding: '0 12px', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                                                >
                                                    Cancel
                                                </Button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Goals Table */}
                                    <div className="table-container mt-[20px]!">
                                        <table className="data-table">
                                            <thead>
                                                <tr>
                                                    <th className="w-[120px]!">Target Year</th>
                                                    <th className="text-right!">Target Limit (tCO₂e)</th>
                                                    <th>Scope Coverage</th>
                                                    <th>Recorded On</th>
                                                    <th className="text-center! w-[140px]!">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {filteredGoals.length === 0 ? (
                                                    <tr>
                                                        <td colSpan="5" className="text-center! p-[32px]! text-[color:var(--text-secondary)]!">
                                                            No emission goals recorded yet. Use the form above to add a yearly goal.
                                                        </td>
                                                    </tr>
                                                ) : (
                                                    filteredGoals.map(g => (
                                                        <tr key={g.year}>
                                                            <td className="font-bold! text-[length:0.95rem]!">
                                                                <span className="inline-flex! items-center! gap-[6px]!">
                                                                    <Calendar size={15} color="var(--accent-color, #ff6600)" />
                                                                    {g.year}
                                                                </span>
                                                            </td>
                                                            <td className="text-right! font-semibold! text-[color:var(--text-primary)]!">
                                                                {Number(g.target_amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} tCO₂e
                                                            </td>
                                                            <td>
                                                                <span className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
                                                                    Corporate Total (Scope 1 + Scope 2)
                                                                </span>
                                                            </td>
                                                            <td className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
                                                                {g.created_at ? new Date(g.created_at).toLocaleDateString() : '-'}
                                                            </td>
                                                            <td className="text-center!">
                                                                <div className="flex! gap-[8px]! justify-center!">
                                                                    <Button
                                                                        variant="ghost" type="submit"
                                                                        onClick={() => handleEditGoal(g)}
                                                                        style={{ padding: '4px 8px', fontSize: '0.8rem', border: '1px solid var(--border-color)', borderRadius: '6px' }}
                                                                        title="Edit Goal"
                                                                    >
                                                                        Edit
                                                                    </Button>
                                                                    <button
                                                                        className="btn-delete p-[4px_8px]! text-[length:0.8rem]!"
                                                                        onClick={() => handleDeleteGoal(g.year)}
                                                                       
                                                                        title="Delete Goal"
                                                                    >
                                                                        Delete
                                                                    </button>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    ))
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                {/* Section 2: Base Years & Recalculation History */}
                                <div style={{ borderTop: '2px dashed var(--border-color)', paddingTop: '32px', marginTop: '16px' }}>
                                    <div className="flex! justify-between! items-start! mb-[16px]!">
                                        <div>
                                            <h2 className="mb-[6px]! font-bold! flex! items-center! gap-[8px]!">
                                                <History size={22} color="var(--accent-color, #ff6600)" /> Base Years & Recalculations History
                                            </h2>
                                            <p className="text-[color:var(--text-secondary)]! m-[0px]! text-[length:0.9rem]!">
                                                Document base year adjustments, justification audits, and baseline emissions changes in compliance with GHG Protocol.
                                            </p>
                                        </div>
                                    </div>

                                    <div className="[background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-left:4px_solid_var(--accent-color,_var(--color-brand-500))]! [&&]:[border-radius:var(--radius-md)]! [padding:14px_18px]! [margin-bottom:24px]! [font-size:var(--text-base)]! [color:var(--text-secondary)]! [line-height:1.5]">
                                        <strong>GHG Protocol Recalculation Rule:</strong> Base year emissions must be recalculated to reflect significant structural changes (e.g. acquisitions, divestments, boundary changes), methodology updates (e.g. new emission factors or GWP standards), or cumulative data errors exceeding significance thresholds. Every adjustment must include a documented reason.
                                    </div>

                                    {/* Base Year Input Form */}
                                    <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(4, 1fr)', background: '#fafafa', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', gap: '16px' }}>
                                        <Field className="input-group" label="Base Year">
<Input
                                                type="number"
                                                min="1990"
                                                max="2100"
                                                value={baseYearForm.year}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, year: e.target.value })}
                                               
                                                placeholder="e.g. 2023"
                                            />
</Field>
                                        <Field className="input-group" label="Prev. Emissions (tCO₂e)">
<Input
                                                type="number"
                                                step="any"
                                                value={baseYearForm.previous_emissions}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, previous_emissions: e.target.value })}
                                               
                                                placeholder="Optional"
                                            />
</Field>
                                        <Field className="input-group" label="Adjusted Emissions (tCO₂e)">
<Input
                                                type="number"
                                                step="any"
                                                value={baseYearForm.adjusted_emissions}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, adjusted_emissions: e.target.value })}
                                               
                                                placeholder="Optional"
                                            />
</Field>
                                        <div className="input-group flex! items-end!">
                                            <button
                                                className="action-btn w-full! p-[12px_16px]! h-[46px]! flex! items-center! justify-center! gap-[6px]!"
                                                onClick={handleSaveBaseYear}
                                               
                                            >
                                                <Plus size={16} /> Save Recalculation
                                            </button>
                                        </div>
                                        <div className="input-group " style={{ gridColumn: 'span 4' }}>
                                            <label>Reason for Change / Recalculation Justification *</label>
                                            <Textarea
                                                value={baseYearForm.reason}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, reason: e.target.value })}
                                               
                                                placeholder="Detail the justification for setting or recalculating the base year (e.g. 'Structural acquisition of 2 production units', 'Methodology update to IPCC AR5 GWPs', 'Boundary adjustment')..."
                                                className="min-h-[80px]!"
                                            />
                                        </div>
                                    </div>

                                    {/* Base Years Recalculation History Table */}
                                    <div className="table-container mt-[20px]!">
                                        <table className="data-table">
                                            <thead>
                                                <tr>
                                                    <th className="w-[130px]!">Date</th>
                                                    <th className="w-[120px]!">Base Year</th>
                                                    <th>Reason for Change / Audit Justification</th>
                                                    <th className="text-right!">Previous (tCO₂e)</th>
                                                    <th className="text-right!">Adjusted (tCO₂e)</th>
                                                    <th className="text-right!">Adjustment Δ</th>
                                                    <th className="text-center! w-[100px]!">Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {filteredBaseYears.length === 0 ? (
                                                    <tr>
                                                        <td colSpan="7" className="text-center! p-[32px]! text-[color:var(--text-secondary)]!">
                                                            No base year recalculations recorded yet. Use the form above to document the baseline.
                                                        </td>
                                                    </tr>
                                                ) : (
                                                    filteredBaseYears.map((b, idx) => {
                                                        const diff = (b.adjusted_emissions !== null && b.previous_emissions !== null && b.adjusted_emissions !== undefined && b.previous_emissions !== undefined)
                                                            ? b.adjusted_emissions - b.previous_emissions
                                                            : null;
                                                        const isLatest = idx === 0;
                                                        return (
                                                            <tr key={b.id}>
                                                                <td className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
                                                                    {b.recalc_date ? new Date(b.recalc_date).toLocaleDateString() : '-'}
                                                                </td>
                                                                <td className="font-bold!">
                                                                    <div className="flex! items-center! gap-[6px]!">
                                                                        <span>{b.year}</span>
                                                                        {isLatest && (
                                                                            <span className="goal-badge [background:var(--color-green-50)]! [color:var(--color-green-700)]! [border:1px_solid_#a7f3d0]! text-[length:0.7rem]!">
                                                                                Active
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </td>
                                                                <td style={{ maxWidth: '350px', whiteSpace: 'normal', wordBreak: 'break-word', fontSize: '0.9rem' }}>
                                                                    {b.reason}
                                                                </td>
                                                                <td className="text-right! text-[length:0.88rem]!">
                                                                    {b.previous_emissions !== null && b.previous_emissions !== undefined
                                                                        ? Number(b.previous_emissions).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                                                                        : '-'}
                                                                </td>
                                                                <td className="text-right! text-[length:0.88rem]! font-semibold!">
                                                                    {b.adjusted_emissions !== null && b.adjusted_emissions !== undefined
                                                                        ? Number(b.adjusted_emissions).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                                                                        : '-'}
                                                                </td>
                                                                <td className="text-right! text-[length:0.88rem]!">
                                                                    {diff !== null ? (
                                                                        <span style={{ color: diff > 0 ? '#b91c1c' : diff < 0 ? '#15803d' : 'var(--text-secondary)', fontWeight: 600 }}>
                                                                            {diff > 0 ? `+${diff.toLocaleString()}` : diff.toLocaleString()} tCO₂e
                                                                        </span>
                                                                    ) : '-'}
                                                                </td>
                                                                <td className="text-center!">
                                                                    <button
                                                                        className="btn-delete p-[4px_8px]! text-[length:0.8rem]!"
                                                                        onClick={() => handleDeleteBaseYearRecalc(b.id)}
                                                                       
                                                                        title="Delete Recalculation Entry"
                                                                    >
                                                                        Delete
                                                                    </button>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                {/* Section 3: SBTi Science-Based Net-Zero Targets */}
                                <div style={{ borderTop: '2px dashed var(--border-color)', paddingTop: '32px', marginTop: '32px' }}>
                                    <div className="flex! justify-between! items-start! mb-[20px]!">
                                        <div>
                                            <h2 className="mb-[6px]! font-bold! flex! items-center! gap-[8px]!">
                                                <Target size={22} color="var(--accent-color, #ff6600)" /> Science-Based Targets (SBTi 1.5°C Trajectory)
                                            </h2>
                                            <p className="text-[color:var(--text-secondary)]! m-[0px]! text-[length:0.9rem]!">
                                                Configure enterprise decarbonization targets aligned with SBTi Net-Zero and Paris Agreement 1.5°C pathways.
                                            </p>
                                        </div>
                                        {hasSbti && (
                                            <span className="goal-badge [background:var(--color-green-50)]! [color:var(--color-green-700)]! [border:1px_solid_#a7f3d0]! inline-flex! items-center! gap-[6px]! text-[length:0.85rem]! p-[6px_14px]!">
                                                <CheckCircle size={14} /> SBTi Target Active
                                            </span>
                                        )}
                                    </div>

                                    <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                                        <Field className="input-group" label="Base Year">
<Input
                                                type="number"
                                                value={sbtiConfig.base_year}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, base_year: parseInt(e.target.value) || 2024 })}
                                               
                                            />
</Field>
                                        <Field className="input-group" label="Base Year Verified Emissions (tCO₂e)">
<Input
                                                type="number"
                                                value={sbtiConfig.base_year_emissions}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, base_year_emissions: parseFloat(e.target.value) || 0 })}
                                               
                                                placeholder="Auto-calculated or manual override"
                                            />
</Field>
                                        <Field className="input-group" label="Target Year (Net-Zero)">
<Input
                                                type="number"
                                                value={sbtiConfig.target_year}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, target_year: parseInt(e.target.value) || 2050 })}
                                               
                                            />
</Field>
                                        <Field className="input-group" label="Annual Reduction Rate (%)">
<Input
                                                type="number"
                                                step="0.1"
                                                value={sbtiConfig.reduction_rate_pct}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, reduction_rate_pct: parseFloat(e.target.value) || 4.2 })}
                                               
                                                placeholder="4.2% for 1.5°C"
                                            />
</Field>
                                        <Field className="input-group" label="Climate Pathway Standard">
<NativeSelect
                                                value={sbtiConfig.pathway_type}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, pathway_type: e.target.value })}
                                                className="component-select"
                                            >
                                                <option value="1.5C">SBTi 1.5°C Aligned (Recommended, 4.2%/yr linear)</option>
                                                <option value="well-below 2C">Well-Below 2°C (2.5%/yr linear)</option>
                                            </NativeSelect>
</Field>
                                    </div>

                                    <div className="mt-[20px]! flex! gap-[12px]!">
                                        <button className="action-btn inline-flex! items-center! gap-[8px]!" onClick={handleSaveSbti}>
                                            <Check size={16} /> Save SBTi Target Configuration
                                        </button>
                                    </div>
                                </div>
                            </div>
);

export default GoalsTab;
