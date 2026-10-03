import React from "react";
import { Button } from "../../ui";
import { Activity, Save, ShieldCheck, Target } from "lucide-react";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsOGMP20Framework = ({ defaultBaseYear, globalThreshold, handleSaveGlobal, isAdmin, midstreamTarget, saving, setDefaultBaseYear, setGlobalThreshold, setMidstreamTarget, setUpstreamTarget, upstreamTarget }) => (
<div className="[background:var(--bg-card,_var(--color-white))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [&&]:[border-radius:var(--radius-lg)]! [padding:32px]! [display:flex]! [flex-direction:column] [gap:28px] [box-shadow:var(--shadow-card,_0_4px_6px_-1px_rgba(0,_0,_0,_0.05))]!">
          <div className="section-intro">
            <div className="[display:flex]! [align-items:center] [gap:10px]">
              <Target size={20} className="section-icon" />
              <h2>OGMP 2.0 Framework & Threshold Configuration</h2>
            </div>
            <p>
              Establish global compliance benchmarks, default asset membership
              years, and acceptable reconciliation tolerances.
            </p>
          </div>

          <div className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(420px,_1fr))] [gap:24px]">
            <div className="[background:var(--bg-hover,_var(--color-ink-50))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [&&]:[border-radius:var(--radius-lg)]! [padding:24px]! [display:flex]! [flex-direction:column] [gap:14px]">
              <label className="[font-size:var(--text-md)]! [font-weight:700]! [color:var(--text-primary,_var(--color-ink-900))]!">
                Default OGMP 2.0 Membership Baseline Year
              </label>
              <span className="[font-size:var(--text-base)]! [color:var(--text-secondary,_var(--color-ink-500))]! [line-height:1.45]">
                The year from which the Gold Standard milestone clock begins
                (Year 0).
              </span>
              <div className="[display:flex]! [gap:8px] [flex-wrap:wrap] [margin:4px_0]!">
                {Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i).map((yr) => (
                  <button
                    key={yr}
                    type="button"
                    disabled={!isAdmin}
                    className={`[background:var(--bg-card,_var(--color-white))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [color:var(--text-primary,_var(--color-ink-900))]! [font-weight:600]! [font-size:var(--text-base)]! [padding:8px_16px]! [&&]:[border-radius:var(--radius-md)]! [cursor:pointer]! [transition:all_0.2s_ease]! [box-shadow:var(--shadow-xs)]! hover:[border-color:var(--color-brand-400)]! hover:[background:rgba(255,_102,_0,_0.04)]! [&.active]:[background:var(--color-primary)]! [&.active]:[color:var(--color-white)]! [&.active]:[border-color:var(--color-brand-500)]! [&.active]:[box-shadow:0_4px_12px_rgba(255,_102,_0,_0.25)]! ${defaultBaseYear === yr ? "active" : ""}`}
                    onClick={() => setDefaultBaseYear(yr)}
                  >
                    {yr}
                  </button>
                ))}
              </div>
              <div className="[background:var(--bg-card,_var(--color-white))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [&&]:[border-radius:var(--radius-md)]! [padding:12px_16px]! [font-size:var(--text-base)]! [color:var(--text-secondary,_var(--color-ink-500))]!">
                <div className="[display:flex]! [align-items:center] [gap:6px] [color:var(--text-primary,_var(--color-ink-900))]! [font-weight:700]! [margin-bottom:6px]!">
                  <ShieldCheck size={15} />
                  <span>Gold Standard Deadlines:</span>
                </div>
                <ul className="[margin:0_0_0_18px]! [padding:0]! [&_li]:[margin-bottom:3px]!">
                  <li>
                    Operated Assets (3 Years):{" "}
                    <strong>{defaultBaseYear + 3}</strong>
                  </li>
                  <li>
                    Non-Operated Assets (5 Years):{" "}
                    <strong>{defaultBaseYear + 5}</strong>
                  </li>
                </ul>
              </div>
            </div>

            <div className="[background:var(--bg-hover,_var(--color-ink-50))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [&&]:[border-radius:var(--radius-lg)]! [padding:24px]! [display:flex]! [flex-direction:column] [gap:14px]">
              <label className="[font-size:var(--text-md)]! [font-weight:700]! [color:var(--text-primary,_var(--color-ink-900))]!">
                Global Reconciliation Variance Threshold (±%)
              </label>
              <span className="[font-size:var(--text-base)]! [color:var(--text-secondary,_var(--color-ink-500))]! [line-height:1.45]">
                Maximum tolerable difference between Bottom-Up (L1-L4) inventory
                and Top-Down (L4/L5) site measurements.
              </span>

              <div className="[display:flex]! [align-items:center] [gap:16px] [margin:8px_0]!">
                <input
                  type="range"
                  min="5"
                  max="50"
                  step="1"
                  disabled={!isAdmin}
                  value={globalThreshold}
                  onChange={(e) => setGlobalThreshold(Number(e.target.value))}
                  className="range-slider"
                  id="global-threshold-slider"
                />
                <div className="[font-size:var(--text-lg)]! [font-weight:800]! [color:var(--color-link)]! [background:rgba(255,_102,_0,_0.08)]! [padding:6px_14px]! [border-radius:var(--radius-md)]! [border:1px_solid_rgba(255,_102,_0,_0.2)]! [min-width:80px] [text-align:center]!">±{globalThreshold}%</div>
              </div>
              <p className="[font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [margin:0]!">
                OGMP 2.0 recommended default is <strong>±20.0%</strong>.
                Facilities exceeding this threshold will be flagged for
                investigation.
              </p>
            </div>
          </div>

          <div className="target-standards-box">
            <div className="[display:flex]! [align-items:center] [gap:8px]">
              <Activity size={18} className="[color:var(--color-link)]!" />
              <h3>OGMP 2.0 Methane Intensity Targets</h3>
            </div>
            <div className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(300px,_1fr))] [gap:16px]">
              <div className="target-card upstream">
                <div className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]! [margin-bottom:6px]!">
                  Upstream Exploration & Production
                </div>
                <div
                  className="flex! items-center! gap-[8px]! m-[8px_0]!"
                >
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="5.0"
                    disabled={!isAdmin}
                    value={upstreamTarget}
                    onChange={(e) => setUpstreamTarget(Number(e.target.value))}
                    className="form-input w-[100px]! font-bold! text-[length:1.1rem]! text-[color:#2563eb]!"
                   
                    id="upstream-target-input"
                  />
                  <span
                    className="font-bold! text-[length:1.1rem]! text-[color:#2563eb]!"
                  >
                    %
                  </span>
                </div>
                <div className="[font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [line-height:1.45] [margin:0]!">
                  Methane loss volume as % of total marketable natural gas
                  volume. (Default: 0.20%)
                </div>
              </div>
              <div className="target-card midstream">
                <div className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-secondary,_var(--color-ink-500))]! [margin-bottom:6px]!">Midstream Processing & LNG</div>
                <div
                  className="flex! items-center! gap-[8px]! m-[8px_0]!"
                >
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="5.0"
                    disabled={!isAdmin}
                    value={midstreamTarget}
                    onChange={(e) => setMidstreamTarget(Number(e.target.value))}
                    className="form-input w-[100px]! font-bold! text-[length:1.1rem]! text-[color:#2e7d32]!"
                   
                    id="midstream-target-input"
                  />
                  <span
                    className="font-bold! text-[length:1.1rem]! text-[color:#2e7d32]!"
                  >
                    %
                  </span>
                </div>
                <div className="[font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [line-height:1.45] [margin:0]!">
                  Methane loss volume as % of total throughput volume. (Default:
                  0.05%)
                </div>
              </div>
            </div>
          </div>

          <div
            className="mt-[24px]! flex! justify-end!"
          >
            <Button
              type="submit"
              onClick={handleSaveGlobal}
              disabled={saving || !isAdmin}
              title={!isAdmin ? "Administrator privileges required to modify settings" : "Save changes"}
              id="save-ogmp-settings-btn"
              className="flex! items-center! gap-[8px]! p-[10px_24px]!"
            >
              <Save size={18} />
              {saving ? "Saving Changes..." : "Save OGMP & Target Settings"}
            </Button>
          </div>
        </div>
);

export default SettingsOGMP20Framework;
