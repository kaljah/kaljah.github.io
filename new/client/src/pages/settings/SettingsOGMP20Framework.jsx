import React from "react";
import { Button } from "../../ui";
import { Activity, Save, ShieldCheck, Target } from "lucide-react";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsOGMP20Framework = ({ defaultBaseYear, globalThreshold, handleSaveGlobal, isAdmin, midstreamTarget, saving, setDefaultBaseYear, setGlobalThreshold, setMidstreamTarget, setUpstreamTarget, upstreamTarget }) => (
<div className="settings-section-card">
          <div className="section-intro">
            <div className="section-intro-header">
              <Target size={20} className="section-icon" />
              <h2>OGMP 2.0 Framework & Threshold Configuration</h2>
            </div>
            <p>
              Establish global compliance benchmarks, default asset membership
              years, and acceptable reconciliation tolerances.
            </p>
          </div>

          <div className="ogmp-config-grid">
            <div className="config-card">
              <label className="config-label">
                Default OGMP 2.0 Membership Baseline Year
              </label>
              <span className="config-subtext">
                The year from which the Gold Standard milestone clock begins
                (Year 0).
              </span>
              <div className="year-selector-buttons">
                {Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i).map((yr) => (
                  <button
                    key={yr}
                    type="button"
                    disabled={!isAdmin}
                    className={`btn-year-pill ${defaultBaseYear === yr ? "active" : ""}`}
                    onClick={() => setDefaultBaseYear(yr)}
                  >
                    {yr}
                  </button>
                ))}
              </div>
              <div className="deadline-preview-note">
                <div className="deadline-title">
                  <ShieldCheck size={15} />
                  <span>Gold Standard Deadlines:</span>
                </div>
                <ul className="deadline-list">
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

            <div className="config-card">
              <label className="config-label">
                Global Reconciliation Variance Threshold (±%)
              </label>
              <span className="config-subtext">
                Maximum tolerable difference between Bottom-Up (L1-L4) inventory
                and Top-Down (L4/L5) site measurements.
              </span>

              <div className="threshold-slider-box">
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
                <div className="threshold-val-display">±{globalThreshold}%</div>
              </div>
              <p className="slider-hint">
                OGMP 2.0 recommended default is <strong>±20.0%</strong>.
                Facilities exceeding this threshold will be flagged for
                investigation.
              </p>
            </div>
          </div>

          <div className="target-standards-box">
            <div className="target-header">
              <Activity size={18} className="target-icon" />
              <h3>OGMP 2.0 Methane Intensity Targets</h3>
            </div>
            <div className="targets-grid">
              <div className="target-card upstream">
                <div className="target-segment">
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
                <div className="target-desc">
                  Methane loss volume as % of total marketable natural gas
                  volume. (Default: 0.20%)
                </div>
              </div>
              <div className="target-card midstream">
                <div className="target-segment">Midstream Processing & LNG</div>
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
                    className="form-input w-[100px]! font-bold! text-[length:1.1rem]! text-[color:#10b981]!"
                   
                    id="midstream-target-input"
                  />
                  <span
                    className="font-bold! text-[length:1.1rem]! text-[color:#10b981]!"
                  >
                    %
                  </span>
                </div>
                <div className="target-desc">
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
