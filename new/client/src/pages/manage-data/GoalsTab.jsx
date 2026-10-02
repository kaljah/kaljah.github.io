import React from 'react';
import { Calendar, Check, CheckCircle, History, Plus, Target } from 'lucide-react';

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const GoalsTab = ({ baseYearForm, baseYearsData, editingGoalYear, filteredBaseYears, filteredGoals, goalForm, goals, handleDeleteBaseYearRecalc, handleDeleteGoal, handleEditGoal, handleSaveBaseYear, handleSaveGoal, handleSaveSbti, hasSbti, sbtiConfig, setBaseYearForm, setEditingGoalYear, setGoalForm, setSbtiConfig }) => (
<div className="manage-card glass-panel">
                                {/* Active Baseline Status Banner */}
                                <div className="baseline-highlight-card">
                                    <div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                                            <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-link)', fontWeight: 700 }}>
                                                GHG Protocol & OGMP 2.0 Baseline
                                            </span>
                                            <span className="goal-badge goal-badge-active">
                                                <CheckCircle size={12} /> Active Baseline
                                            </span>
                                        </div>
                                        <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                                            Current Base Year: {baseYearsData.active_year || '2023'}
                                        </div>
                                        {baseYearsData.active_record?.reason && (
                                            <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                                <span style={{ fontWeight: 600 }}>Active Justification:</span> {baseYearsData.active_record.reason}
                                            </div>
                                        )}
                                    </div>
                                    <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                                        <div style={{ textAlign: 'right' }}>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>ANNUAL TARGETS SET</div>
                                            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>{goals.length} Years</div>
                                        </div>
                                        {baseYearsData.active_record?.recalc_date && (
                                            <div style={{ textAlign: 'right', borderLeft: '1px solid var(--border-color)', paddingLeft: '16px' }}>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>LAST RECALCULATED</div>
                                                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                                    {new Date(baseYearsData.active_record.recalc_date).toLocaleDateString()}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Section 1: Yearly Emission Goals */}
                                <div style={{ marginBottom: '40px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                                        <div>
                                            <h2 style={{ marginBottom: '6px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <Target size={22} color="var(--accent-color, #ff6600)" /> Yearly Emission Goals
                                            </h2>
                                            <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                                                Configure annual corporate emission limits and target pathways (tCO₂e) to monitor reduction trajectory.
                                            </p>
                                        </div>
                                    </div>

                                    {/* Goal Input Form */}
                                    <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)', background: '#fafafa', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                                        <div className="input-group">
                                            <label>Target Year</label>
                                            <input
                                                type="number"
                                                min="1990"
                                                max="2100"
                                                value={goalForm.year}
                                                onChange={(e) => setGoalForm({ ...goalForm, year: e.target.value })}
                                                className="mole-input"
                                                placeholder="e.g. 2030"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Target Emission Amount (tCO₂e)</label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={goalForm.target_amount}
                                                onChange={(e) => setGoalForm({ ...goalForm, target_amount: e.target.value })}
                                                className="mole-input"
                                                placeholder="e.g. 150000"
                                            />
                                        </div>
                                        <div className="input-group" style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
                                            <button
                                                className="action-btn"
                                                onClick={handleSaveGoal}
                                                style={{ flex: 1, padding: '12px 16px', height: '46px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                                            >
                                                <Plus size={16} /> {editingGoalYear ? 'Update Goal' : 'Save Goal'}
                                            </button>
                                            {editingGoalYear && (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => {
                                                        setEditingGoalYear(null);
                                                        setGoalForm({ year: new Date().getFullYear(), target_amount: '' });
                                                    }}
                                                    style={{ height: '46px', padding: '0 12px', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                                                >
                                                    Cancel
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Goals Table */}
                                    <div className="table-container" style={{ marginTop: '20px' }}>
                                        <table className="data-table">
                                            <thead>
                                                <tr>
                                                    <th style={{ width: '120px' }}>Target Year</th>
                                                    <th style={{ textAlign: 'right' }}>Target Limit (tCO₂e)</th>
                                                    <th>Scope Coverage</th>
                                                    <th>Recorded On</th>
                                                    <th style={{ textAlign: 'center', width: '140px' }}>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {filteredGoals.length === 0 ? (
                                                    <tr>
                                                        <td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary)' }}>
                                                            No emission goals recorded yet. Use the form above to add a yearly goal.
                                                        </td>
                                                    </tr>
                                                ) : (
                                                    filteredGoals.map(g => (
                                                        <tr key={g.year}>
                                                            <td style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                                                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                                                                    <Calendar size={15} color="var(--accent-color, #ff6600)" />
                                                                    {g.year}
                                                                </span>
                                                            </td>
                                                            <td style={{ textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                                                                {Number(g.target_amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} tCO₂e
                                                            </td>
                                                            <td>
                                                                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                                    Corporate Total (Scope 1 + Scope 2)
                                                                </span>
                                                            </td>
                                                            <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                                {g.created_at ? new Date(g.created_at).toLocaleDateString() : '-'}
                                                            </td>
                                                            <td style={{ textAlign: 'center' }}>
                                                                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                                                                    <button
                                                                        className="btn-ghost"
                                                                        onClick={() => handleEditGoal(g)}
                                                                        style={{ padding: '4px 8px', fontSize: '0.8rem', border: '1px solid var(--border-color)', borderRadius: '6px' }}
                                                                        title="Edit Goal"
                                                                    >
                                                                        Edit
                                                                    </button>
                                                                    <button
                                                                        className="btn-delete"
                                                                        onClick={() => handleDeleteGoal(g.year)}
                                                                        style={{ padding: '4px 8px', fontSize: '0.8rem' }}
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
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                                        <div>
                                            <h2 style={{ marginBottom: '6px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <History size={22} color="var(--accent-color, #ff6600)" /> Base Years & Recalculations History
                                            </h2>
                                            <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                                                Document base year adjustments, justification audits, and baseline emissions changes in compliance with GHG Protocol.
                                            </p>
                                        </div>
                                    </div>

                                    <div className="guidance-box">
                                        <strong>GHG Protocol Recalculation Rule:</strong> Base year emissions must be recalculated to reflect significant structural changes (e.g. acquisitions, divestments, boundary changes), methodology updates (e.g. new emission factors or GWP standards), or cumulative data errors exceeding significance thresholds. Every adjustment must include a documented reason.
                                    </div>

                                    {/* Base Year Input Form */}
                                    <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(4, 1fr)', background: '#fafafa', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', gap: '16px' }}>
                                        <div className="input-group">
                                            <label>Base Year</label>
                                            <input
                                                type="number"
                                                min="1990"
                                                max="2100"
                                                value={baseYearForm.year}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, year: e.target.value })}
                                                className="mole-input"
                                                placeholder="e.g. 2023"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Prev. Emissions (tCO₂e)</label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={baseYearForm.previous_emissions}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, previous_emissions: e.target.value })}
                                                className="mole-input"
                                                placeholder="Optional"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Adjusted Emissions (tCO₂e)</label>
                                            <input
                                                type="number"
                                                step="any"
                                                value={baseYearForm.adjusted_emissions}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, adjusted_emissions: e.target.value })}
                                                className="mole-input"
                                                placeholder="Optional"
                                            />
                                        </div>
                                        <div className="input-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                                            <button
                                                className="action-btn"
                                                onClick={handleSaveBaseYear}
                                                style={{ width: '100%', padding: '12px 16px', height: '46px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                                            >
                                                <Plus size={16} /> Save Recalculation
                                            </button>
                                        </div>
                                        <div className="input-group form-full" style={{ gridColumn: 'span 4' }}>
                                            <label>Reason for Change / Recalculation Justification *</label>
                                            <textarea
                                                value={baseYearForm.reason}
                                                onChange={(e) => setBaseYearForm({ ...baseYearForm, reason: e.target.value })}
                                                className="mole-input"
                                                placeholder="Detail the justification for setting or recalculating the base year (e.g. 'Structural acquisition of 2 production units', 'Methodology update to IPCC AR5 GWPs', 'Boundary adjustment')..."
                                                style={{ minHeight: '80px' }}
                                            />
                                        </div>
                                    </div>

                                    {/* Base Years Recalculation History Table */}
                                    <div className="table-container" style={{ marginTop: '20px' }}>
                                        <table className="data-table">
                                            <thead>
                                                <tr>
                                                    <th style={{ width: '130px' }}>Date</th>
                                                    <th style={{ width: '120px' }}>Base Year</th>
                                                    <th>Reason for Change / Audit Justification</th>
                                                    <th style={{ textAlign: 'right' }}>Previous (tCO₂e)</th>
                                                    <th style={{ textAlign: 'right' }}>Adjusted (tCO₂e)</th>
                                                    <th style={{ textAlign: 'right' }}>Adjustment Δ</th>
                                                    <th style={{ textAlign: 'center', width: '100px' }}>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {filteredBaseYears.length === 0 ? (
                                                    <tr>
                                                        <td colSpan="7" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary)' }}>
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
                                                                <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                                    {b.recalc_date ? new Date(b.recalc_date).toLocaleDateString() : '-'}
                                                                </td>
                                                                <td style={{ fontWeight: 700 }}>
                                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                                        <span>{b.year}</span>
                                                                        {isLatest && (
                                                                            <span className="goal-badge goal-badge-active" style={{ fontSize: '0.7rem' }}>
                                                                                Active
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </td>
                                                                <td style={{ maxWidth: '350px', whiteSpace: 'normal', wordBreak: 'break-word', fontSize: '0.9rem' }}>
                                                                    {b.reason}
                                                                </td>
                                                                <td style={{ textAlign: 'right', fontSize: '0.88rem' }}>
                                                                    {b.previous_emissions !== null && b.previous_emissions !== undefined
                                                                        ? Number(b.previous_emissions).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                                                                        : '-'}
                                                                </td>
                                                                <td style={{ textAlign: 'right', fontSize: '0.88rem', fontWeight: 600 }}>
                                                                    {b.adjusted_emissions !== null && b.adjusted_emissions !== undefined
                                                                        ? Number(b.adjusted_emissions).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                                                                        : '-'}
                                                                </td>
                                                                <td style={{ textAlign: 'right', fontSize: '0.88rem' }}>
                                                                    {diff !== null ? (
                                                                        <span style={{ color: diff > 0 ? '#b91c1c' : diff < 0 ? '#15803d' : 'var(--text-secondary)', fontWeight: 600 }}>
                                                                            {diff > 0 ? `+${diff.toLocaleString()}` : diff.toLocaleString()} tCO₂e
                                                                        </span>
                                                                    ) : '-'}
                                                                </td>
                                                                <td style={{ textAlign: 'center' }}>
                                                                    <button
                                                                        className="btn-delete"
                                                                        onClick={() => handleDeleteBaseYearRecalc(b.id)}
                                                                        style={{ padding: '4px 8px', fontSize: '0.8rem' }}
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
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                                        <div>
                                            <h2 style={{ marginBottom: '6px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <Target size={22} color="var(--accent-color, #ff6600)" /> Science-Based Targets (SBTi 1.5°C Trajectory)
                                            </h2>
                                            <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                                                Configure enterprise decarbonization targets aligned with SBTi Net-Zero and Paris Agreement 1.5°C pathways.
                                            </p>
                                        </div>
                                        {hasSbti && (
                                            <span className="goal-badge goal-badge-active" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', padding: '6px 14px' }}>
                                                <CheckCircle size={14} /> SBTi Target Active
                                            </span>
                                        )}
                                    </div>

                                    <div className="grid-forms" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                                        <div className="input-group">
                                            <label>Base Year</label>
                                            <input
                                                type="number"
                                                value={sbtiConfig.base_year}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, base_year: parseInt(e.target.value) || 2024 })}
                                                className="mole-input"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Base Year Verified Emissions (tCO₂e)</label>
                                            <input
                                                type="number"
                                                value={sbtiConfig.base_year_emissions}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, base_year_emissions: parseFloat(e.target.value) || 0 })}
                                                className="mole-input"
                                                placeholder="Auto-calculated or manual override"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Target Year (Net-Zero)</label>
                                            <input
                                                type="number"
                                                value={sbtiConfig.target_year}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, target_year: parseInt(e.target.value) || 2050 })}
                                                className="mole-input"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Annual Reduction Rate (%)</label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                value={sbtiConfig.reduction_rate_pct}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, reduction_rate_pct: parseFloat(e.target.value) || 4.2 })}
                                                className="mole-input"
                                                placeholder="4.2% for 1.5°C"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Climate Pathway Standard</label>
                                            <select
                                                value={sbtiConfig.pathway_type}
                                                onChange={e => setSbtiConfig({ ...sbtiConfig, pathway_type: e.target.value })}
                                                className="component-select"
                                            >
                                                <option value="1.5C">SBTi 1.5°C Aligned (Recommended, 4.2%/yr linear)</option>
                                                <option value="well-below 2C">Well-Below 2°C (2.5%/yr linear)</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div style={{ marginTop: '20px', display: 'flex', gap: '12px' }}>
                                        <button className="action-btn" onClick={handleSaveSbti} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                                            <Check size={16} /> Save SBTi Target Configuration
                                        </button>
                                    </div>
                                </div>
                            </div>
);

export default GoalsTab;
