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
                    className="flex-1! p-[8px_12px]! bg-[color:#f3f4f6]! rounded-[6px]! [border:1px_solid_#e5e7eb]! flex! justify-between! items-center!"
                  >
                    <span
                      className="text-[length:0.75rem]! font-semibold! text-[color:#374151]!"
                    >
                      Meter Calibration Tolerance
                    </span>
                    <div className="flex! items-center!">
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! mr-[2px]!"
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        className="w-[45px]! p-[2px_4px]! text-[length:0.85rem]! text-right!"
                        placeholder="2.0"
                        value={meterUncertaintyPct}
                        onChange={(e) => setMeterUncertaintyPct(e.target.value)}
                        step="0.1"
                      />
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! ml-[2px]!"
                      >
                        %
                      </span>
                    </div>
                  </div>
                  <div
                    className="flex-1! p-[8px_12px]! bg-[color:#f3f4f6]! rounded-[6px]! [border:1px_solid_#e5e7eb]! flex! justify-between! items-center!"
                  >
                    <span
                      className="text-[length:0.75rem]! font-semibold! text-[color:#374151]!"
                    >
                      GC Analytical Precision
                    </span>
                    <div className="flex! items-center!">
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! mr-[2px]!"
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        className="w-[55px]! p-[2px_4px]! text-[length:0.85rem]! text-right!"
                        placeholder="Opt."
                        value={gcUncertaintyPct}
                        onChange={(e) => setGcUncertaintyPct(e.target.value)}
                        step="0.1"
                      />
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! ml-[2px]!"
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
                  className="flex-1! p-[8px_12px]! bg-[color:#f3f4f6]! rounded-[6px]! [border:1px_solid_#e5e7eb]! flex! justify-between! items-center!"
                >
                  <span
                    className="text-[length:0.75rem]! font-semibold! text-[color:#374151]!"
                  >
                    CO₂
                  </span>
                  {sourceType === "specific" ? (
                    <div className="flex! items-center!">
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! mr-[2px]!"
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        className="w-[45px]! p-[2px_4px]! text-[length:0.85rem]! text-right!"
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
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! ml-[2px]!"
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.co2 != null ? "#2e7d32" : "#9ca3af",
                      }}
                    >
                      {uncertainty.co2 != null
                        ? `±${(uncertainty.co2 * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
                <div
                  className="flex-1! p-[8px_12px]! bg-[color:#f3f4f6]! rounded-[6px]! [border:1px_solid_#e5e7eb]! flex! justify-between! items-center!"
                >
                  <span
                    className="text-[length:0.75rem]! font-semibold! text-[color:#374151]!"
                  >
                    CH₄
                  </span>
                  {sourceType === "specific" ? (
                    <div className="flex! items-center!">
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! mr-[2px]!"
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        className="w-[45px]! p-[2px_4px]! text-[length:0.85rem]! text-right!"
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
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! ml-[2px]!"
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.ch4 != null ? "#1d4ed8" : "#9ca3af",
                      }}
                    >
                      {uncertainty.ch4 != null
                        ? `±${(uncertainty.ch4 * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                  )}
                </div>
                <div
                  className="flex-1! p-[8px_12px]! bg-[color:#f3f4f6]! rounded-[6px]! [border:1px_solid_#e5e7eb]! flex! justify-between! items-center!"
                >
                  <span
                    className="text-[length:0.75rem]! font-semibold! text-[color:#374151]!"
                  >
                    N₂O
                  </span>
                  {sourceType === "specific" ? (
                    <div className="flex! items-center!">
                      <span
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! mr-[2px]!"
                      >
                        ±
                      </span>
                      <Input
                        type="number"
                       
                        className="w-[45px]! p-[2px_4px]! text-[length:0.85rem]! text-right!"
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
                        className="text-[length:0.85rem]! text-[color:#9ca3af]! ml-[2px]!"
                      >
                        %
                      </span>
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: uncertainty.n2o != null ? "#6d28d9" : "#9ca3af",
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
