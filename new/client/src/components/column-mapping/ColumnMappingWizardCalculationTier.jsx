import React from "react";
import { NativeSelect } from "../../ui/NativeSelect";
import { PROCESS_TYPES } from "../../utils/EmissionFactors";
import { activateOnKey } from "../../utils/a11yKeys";

// Extracted from ColumnMappingWizard.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const ColumnMappingWizardCalculationTier = ({ selectedProcess, selectedProcessScope, selectedTier, setSelectedProcess, setSelectedProcessScope, setSelectedTier }) => (
<div className="cmw-body">
            <div
              className="p-[20px]! flex! flex-col! gap-[24px]!"
            >
              <div>
                <h3
                  className="mb-[16px]! text-[color:var(--text-primary)]! text-[length:1.1rem]!"
                >
                  Calculation Tier
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                  }}
                >
                  <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                    className={`[transition:all_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[background:var(--color-ink-50)]! [&.active]:[border-color:var(--color-blue-600)]! [&.active]:[background:var(--color-blue-50)]! [&.active]:[box-shadow:0_0_0_1px_var(--color-blue-600)]! [&.active_h4]:[color:#1e40af]! [&.active>div>div]:[background:var(--color-blue-600)]! [&.active>div>div]:[border-color:var(--color-blue-600)]! ${selectedTier === "1" ? "active" : ""}`}
                    onClick={() => setSelectedTier("1")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedTier === "1"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      className="flex! items-center! gap-[8px]! mb-[8px]!"
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedTier === "1"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 className="m-[0px]! text-[color:var(--text-primary)]!">
                        Tier 1 (Default Factors)
                      </h4>
                    </div>
                    <p
                      className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]!"
                    >
                      Basic calculation using industry defaults.
                    </p>
                  </div>
                  <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                    className={`[transition:all_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[background:var(--color-ink-50)]! [&.active]:[border-color:var(--color-blue-600)]! [&.active]:[background:var(--color-blue-50)]! [&.active]:[box-shadow:0_0_0_1px_var(--color-blue-600)]! [&.active_h4]:[color:#1e40af]! [&.active>div>div]:[background:var(--color-blue-600)]! [&.active>div>div]:[border-color:var(--color-blue-600)]! ${selectedTier === "3" ? "active" : ""}`}
                    onClick={() => setSelectedTier("3")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedTier === "3"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      className="flex! items-center! gap-[8px]! mb-[8px]!"
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedTier === "3"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 className="m-[0px]! text-[color:var(--text-primary)]!">
                        Tier 3 (Engineering)
                      </h4>
                    </div>
                    <p
                      className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]!"
                    >
                      Advanced calculation using process specifications.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3
                  className="mb-[16px]! text-[color:var(--text-primary)]! text-[length:1.1rem]!"
                >
                  Process Scope
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                    marginBottom: "16px",
                  }}
                >
                  <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                    className={`[transition:all_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[background:var(--color-ink-50)]! [&.active]:[border-color:var(--color-blue-600)]! [&.active]:[background:var(--color-blue-50)]! [&.active]:[box-shadow:0_0_0_1px_var(--color-blue-600)]! [&.active_h4]:[color:#1e40af]! [&.active>div>div]:[background:var(--color-blue-600)]! [&.active>div>div]:[border-color:var(--color-blue-600)]! ${selectedProcessScope === "all" ? "active" : ""}`}
                    onClick={() => setSelectedProcessScope("all")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedProcessScope === "all"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      className="flex! items-center! gap-[8px]! mb-[8px]!"
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedProcessScope === "all"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 className="m-[0px]! text-[color:var(--text-primary)]!">
                        All Processes
                      </h4>
                    </div>
                    <p
                      className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]!"
                    >
                      Upload data for various process types together.
                    </p>
                  </div>
                  <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                    className={`[transition:all_0.2s_ease]! hover:[border-color:var(--color-ink-300)]! hover:[background:var(--color-ink-50)]! [&.active]:[border-color:var(--color-blue-600)]! [&.active]:[background:var(--color-blue-50)]! [&.active]:[box-shadow:0_0_0_1px_var(--color-blue-600)]! [&.active_h4]:[color:#1e40af]! [&.active>div>div]:[background:var(--color-blue-600)]! [&.active>div>div]:[border-color:var(--color-blue-600)]! ${selectedProcessScope === "specific" ? "active" : ""}`}
                    onClick={() => setSelectedProcessScope("specific")}
                    style={{
                      padding: "16px",
                      border: "1px solid var(--border-color)",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedProcessScope === "specific"
                          ? "var(--bg-secondary)"
                          : "transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    <div
                      className="flex! items-center! gap-[8px]! mb-[8px]!"
                    >
                      <div
                        style={{
                          width: "16px",
                          height: "16px",
                          borderRadius: "50%",
                          border: "2px solid var(--sonatrach-orange)",
                          background:
                            selectedProcessScope === "specific"
                              ? "var(--sonatrach-orange)"
                              : "transparent",
                        }}
                      ></div>
                      <h4 className="m-[0px]! text-[color:var(--text-primary)]!">
                        Choose by Process
                      </h4>
                    </div>
                    <p
                      className="m-[0px]! text-[length:0.9rem]! text-[color:var(--text-secondary)]!"
                    >
                      Upload data for a single specific process.
                    </p>
                  </div>
                </div>

                {selectedProcessScope === "specific" && (
                  <div className="mt-[12px]!">
                    <label
                      style={{
                        display: "block",
                        marginBottom: "8px",
                        color: "var(--text-secondary)",
                        fontWeight: "bold",
                      }}
                    >
                      Select Process Type:
                    </label>
                    <NativeSelect
                      value={selectedProcess}
                      onChange={(e) => setSelectedProcess(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "12px",
                        borderRadius: "6px",
                        border: "1px solid var(--border-color)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-primary)",
                        outline: "none",
                      }}
                    >
                      {Object.entries(PROCESS_TYPES).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                )}
              </div>
            </div>
          </div>
);

export default ColumnMappingWizardCalculationTier;
