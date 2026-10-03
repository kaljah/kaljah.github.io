import React from "react";
import { Building2, Save } from "lucide-react";
import { NativeSelect } from "../../ui/NativeSelect";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsFacilityLevelOGMPOverrides = ({ facilities, facilityEdits, handleFacilityChange, handleSaveFacility, isAdmin, user }) => (
<div className="[background:var(--bg-card,_var(--color-white))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [border-radius:var(--radius-lg)] [padding:32px] [display:flex] [flex-direction:column] [gap:28px] [box-shadow:var(--shadow-card,_0_4px_6px_-1px_rgba(0,_0,_0,_0.05))]">
          <div className="section-intro">
            <div className="[display:flex] [align-items:center] [gap:10px]">
              <Building2 size={20} className="[color:var(--color-link)]" />
              <h2>Facility-Level OGMP Overrides</h2>
            </div>
            <p>
              Customize operator status (Operated vs Non-Operated), country,
              base year, and specific reconciliation variance thresholds for
              each facility.
            </p>
          </div>

          <div className="[overflow-x:auto] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [border-radius:var(--radius-lg)] [background:var(--bg-card,_var(--color-white))]">
            <table className="facility-config-table">
              <thead>
                <tr>
                  <th>Facility Name</th>
                  <th>Segment</th>
                  <th>Operator Status</th>
                  <th>Country</th>
                  <th>Base Year</th>
                  <th>Target Year</th>
                  <th>Threshold (±%)</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {facilities.map((fac) => {
                  const edit = facilityEdits[fac.id] || {};
                  const opStatus = edit.operator_status || "operated";
                  const baseYear = Number(edit.ogmp_membership_year || 2023);
                  const targetYear =
                    baseYear + (opStatus === "operated" ? 3 : 5);

                  return (
                    <tr key={fac.id}>
                      <td className="[display:flex] [flex-direction:column] [gap:2px]">
                        <strong>{fac.name}</strong>
                        <span className="[font-size:var(--text-xs)] [color:var(--text-secondary,_var(--color-ink-500))]">
                          {fac.code || "FAC-" + fac.id}
                        </span>
                      </td>
                      <td>{fac.segment || "Upstream"}</td>
                      <td>
                        <NativeSelect
                          className="table-select"
                          value={opStatus}
                          disabled={!isAdmin}
                          onChange={(e) =>
                            handleFacilityChange(
                              fac.id,
                              "operator_status",
                              e.target.value,
                            )
                          }
                        >
                          <option value="operated">
                            Operated (3-yr target)
                          </option>
                          <option value="non_operated">
                            Non-Operated (5-yr target)
                          </option>
                        </NativeSelect>
                      </td>
                      <td>
                        <input
                          type="text"
                          className="table-input"
                          value={edit.country || "Algeria"}
                          disabled={!isAdmin}
                          onChange={(e) =>
                            handleFacilityChange(
                              fac.id,
                              "country",
                              e.target.value,
                            )
                          }
                        />
                      </td>
                      <td>
                        <NativeSelect
                          className="[background:var(--bg-card,_var(--color-white))] [border:1px_solid_var(--border-color,_var(--color-ink-300))] [color:var(--text-primary,_var(--color-ink-900))] [border-radius:var(--radius-md)] [padding:7px_8px] [font-size:var(--text-base)] [font-family:inherit]"
                          value={baseYear}
                          disabled={!isAdmin}
                          onChange={(e) =>
                            handleFacilityChange(
                              fac.id,
                              "ogmp_membership_year",
                              e.target.value,
                            )
                          }
                        >
                          {Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i).map((y) => (
                            <option key={y} value={y}>
                              {y}
                            </option>
                          ))}
                        </NativeSelect>
                      </td>
                      <td className="target-yr-cell">
                        <span className="[background:rgba(2,_132,_199,_0.1)] [color:var(--color-blue-700)] [border:1px_solid_rgba(2,_132,_199,_0.25)] [padding:4px_10px] [border-radius:var(--radius-sm)] [font-weight:700] [font-size:var(--text-sm)]">{targetYear}</span>
                      </td>
                      <td>
                        <div className="[display:flex] [align-items:center] [gap:4px] [font-weight:600] [color:var(--text-primary,_var(--color-ink-900))]">
                          <span>±</span>
                          <input
                            type="number"
                            min="1"
                            max="100"
                            className="[width:60px] [background:var(--bg-card,_var(--color-white))] [border:1px_solid_var(--border-color,_var(--color-ink-300))] [color:var(--text-primary,_var(--color-ink-900))] [border-radius:var(--radius-md)] [padding:6px_8px] [font-size:var(--text-base)] [text-align:center] [font-family:inherit]"
                            value={edit.reconciliation_threshold || 20.0}
                            disabled={!isAdmin}
                            onChange={(e) =>
                              handleFacilityChange(
                                fac.id,
                                "reconciliation_threshold",
                                e.target.value,
                              )
                            }
                          />
                          <span>%</span>
                        </div>
                      </td>
                      <td>
                        <button
                          className="btn-table-save"
                          onClick={() => handleSaveFacility(fac.id)}
                          disabled={user?.role === "it_admin" || (user?.role !== "admin" && user?.role !== "superuser")}
                          title={user?.role === "it_admin" || (user?.role !== "admin" && user?.role !== "superuser") ? "Administrator privileges required to update facility" : "Save Facility Settings"}
                        >
                          <Save size={13} />
                          <span>Save</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
);

export default SettingsFacilityLevelOGMPOverrides;
