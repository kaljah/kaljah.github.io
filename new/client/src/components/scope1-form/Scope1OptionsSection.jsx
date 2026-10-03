import React from "react";
import { Input } from "../../ui";
import { MoreOptions, Section } from "../scope1/ui";

// Extracted from Scope1Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope1OptionsSection = ({ gcUncertaintyPct, meterUncertaintyPct, renderSpecificForm, setGcUncertaintyPct, setMeterUncertaintyPct, setUserUncertainty, sourceType, uncertainty, userUncertainty }) => (
<Section n={3} title="Activity Data">
          <div className="s1-inputs">{renderSpecificForm()}</div>
          <MoreOptions label="Uncertainty">
          <div className="form-grid-3">
            {sourceType === "specific" && (
              <div
                className="input-group"
                style={{ gridColumn: "span 3", marginBottom: "8px" }}
              >
                <label>Measurement Instrumentation Precision</label>
                <div className="flex! gap-[8px]! flex-wrap!">
                  <div
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      background: "#f3f4f6",
                      borderRadius: "6px",
                      border: "1px solid #e5e7eb",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: "#374151",
                      }}
                    >
                      Meter Calibration Tolerance
                    </span>
                    <div className="flex! items-center!">
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="2.0"
                        value={meterUncertaintyPct}
                        onChange={(e) => setMeterUncertaintyPct(e.target.value)}
                        step="0.1"
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  </div>
                  <div
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      background: "#f3f4f6",
                      borderRadius: "6px",
                      border: "1px solid #e5e7eb",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: "#374151",
                      }}
                    >
                      GC Analytical Precision
                    </span>
                    <div className="flex! items-center!">
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        style={{
                          width: "55px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="Opt."
                        value={gcUncertaintyPct}
                        onChange={(e) => setGcUncertaintyPct(e.target.value)}
                        step="0.1"
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  </div>
                  <div className="flex-1!"></div>
                </div>
              </div>
            )}
            <div className="input-group" style={{ gridColumn: "span 3" }}>
              <label>
                Emission Factor / Direct Measurement Uncertainty Override (±%)
              </label>
              <div className="flex! gap-[8px]! flex-wrap!">
                <div
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    background: "#f3f4f6",
                    borderRadius: "6px",
                    border: "1px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#374151",
                    }}
                  >
                    CO₂
                  </span>
                  {sourceType === "specific" ? (
                    <div className="flex! items-center!">
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="—"
                        value={userUncertainty.co2}
                        onChange={(e) =>
                          setUserUncertainty({
                            ...userUncertainty,
                            co2: e.target.value,
                          })
                        }
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.co2 != null ? "#10b981" : "#9ca3af",
                      }}
                    >
                      {uncertainty.co2 != null
                        ? `±${(uncertainty.co2 * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    background: "#f3f4f6",
                    borderRadius: "6px",
                    border: "1px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#374151",
                    }}
                  >
                    CH₄
                  </span>
                  {sourceType === "specific" ? (
                    <div className="flex! items-center!">
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="—"
                        value={userUncertainty.ch4}
                        onChange={(e) =>
                          setUserUncertainty({
                            ...userUncertainty,
                            ch4: e.target.value,
                          })
                        }
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.ch4 != null ? "#3b82f6" : "#9ca3af",
                      }}
                    >
                      {uncertainty.ch4 != null
                        ? `±${(uncertainty.ch4 * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    background: "#f3f4f6",
                    borderRadius: "6px",
                    border: "1px solid #e5e7eb",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "#374151",
                    }}
                  >
                    N₂O
                  </span>
                  {sourceType === "specific" ? (
                    <div className="flex! items-center!">
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginRight: "2px",
                        }}
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        style={{
                          width: "45px",
                          padding: "2px 4px",
                          fontSize: "0.85rem",
                          textAlign: "right",
                        }}
                        placeholder="—"
                        value={userUncertainty.n2o}
                        onChange={(e) =>
                          setUserUncertainty({
                            ...userUncertainty,
                            n2o: e.target.value,
                          })
                        }
                      />
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: "#9ca3af",
                          marginLeft: "2px",
                        }}
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.n2o != null ? "#8b5cf6" : "#9ca3af",
                      }}
                    >
                      {uncertainty.n2o != null
                        ? `±${(uncertainty.n2o * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
          </MoreOptions>
        </Section>
);

export default Scope1OptionsSection;
