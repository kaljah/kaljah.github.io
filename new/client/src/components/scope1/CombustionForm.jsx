import React from "react";
import CustomDropdown from "../CustomDropdown";

// Process types that require HHV input per API Compendium 2021 Section 5
const HHV_REQUIRED_PROCESSES = [
  "combustion",
  "stationary_combustion",
  "flaring",
];

const CombustionForm = ({ data, onChange, sourceType }) => {
  const isFlaring = data.process_type === "flaring";
  const isCombustion = ["combustion", "stationary_combustion"].includes(
    data.process_type,
  );
  const needsHHV = HHV_REQUIRED_PROCESSES.includes(data.process_type);

  return (
    <div className="combustion-form">
      <div className="form-grid-2">
        <div className="input-group">
          <label>
            {isFlaring
              ? "Gas Volume Flared"
              : data.process_type === "loading"
                ? "Volume Loaded"
                : data.process_type === "separation"
                  ? "Volume treated"
                  : "Quantity"}
          </label>
          <input
            type="number"
            className="mole-input"
            value={data.amount || ""}
            onChange={(e) => onChange("amount", e.target.value)}
            placeholder="0.00"
          />
        </div>

        <div className="input-group">
          <label>Unit</label>
          <CustomDropdown
            options={[
              { value: "m3", label: "m³" },
              { value: "scf", label: "scf" },
              { value: "Mcf", label: "Mcf" },
              { value: "MMscf", label: "MMscf" },
              { value: "gal", label: "gal" },
              { value: "bbl", label: "bbl" },
              { value: "L", label: "L" },
              { value: "kg", label: "kg" },
              { value: "ton", label: "ton (short)" },
              { value: "tonne", label: "tonne (metric)" },
              { value: "events", label: "events" },
            ]}
            value={data.unit}
            onChange={(val) => onChange("unit", val)}
          />
        </div>
      </div>

      {/* HHV — required in specific (Tier 3) mode */}
      {needsHHV && sourceType === "specific" && (
        <div className="s1-block" style={{ marginTop: "14px" }}>
          <div className="form-grid-2" style={{ gap: "10px" }}>
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: "0.75rem" }}>
                HHV
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <input
                id="hhv-input"
                type="number"
                className="mole-input"
                value={data.hhv || ""}
                onChange={(e) => onChange("hhv", e.target.value)}
                placeholder={
                  isFlaring ? "e.g. 983 (natural gas)" : "e.g. 1020 (BTU/scf)"
                }
                style={{ borderColor: !data.hhv ? "#fbbf24" : "#d1fae5" }}
              />
            </div>
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: "0.75rem" }}>HHV Unit</label>
              <select
                className="component-select"
                value={data.hhv_unit || "BTU/scf"}
                onChange={(e) => onChange("hhv_unit", e.target.value)}
              >
                <option value="BTU/scf">BTU/scf</option>
                <option value="BTU/ft3">BTU/ft³</option>
                <option value="MJ/m3">MJ/m³</option>
                <option value="MJ/kg">MJ/kg</option>
                <option value="BTU/gal">BTU/gal</option>
                <option value="BTU/lb">BTU/lb</option>
                <option value="kcal/m3">kcal/m³</option>
              </select>
            </div>
          </div>

          {/* Combustion efficiency — required for stationary combustion */}
          {isCombustion && (
            <div
              className="input-group"
              style={{ marginTop: "10px", marginBottom: 0 }}
            >
              <label style={{ fontSize: "0.75rem" }}>
                Combustion efficiency
                <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
              </label>
              <div
                style={{ display: "flex", gap: "8px", alignItems: "center" }}
              >
                <input
                  id="combustion-efficiency-input"
                  type="number"
                  className="mole-input"
                  min="0"
                  max="100"
                  step="0.1"
                  value={
                    data.combustion_efficiency != null
                      ? data.combustion_efficiency
                      : ""
                  }
                  onChange={(e) =>
                    onChange("combustion_efficiency", e.target.value)
                  }
                  placeholder="e.g. 99.5"
                  style={{
                    flex: 1,
                    borderColor:
                      data.combustion_efficiency == null
                        ? "#fbbf24"
                        : "#d1fae5",
                  }}
                />
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "#6b7280",
                    whiteSpace: "nowrap",
                  }}
                >
                  %
                </span>
              </div>
            </div>
          )}

          {/* Flare type & CH4 content for flaring */}
          {isFlaring && (
            <div className="form-grid-2" style={{ gap: "10px", marginTop: "10px" }}>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.75rem" }}>Flare Type</label>
                <select
                  className="component-select"
                  value={data.flare_type || "elevated"}
                  onChange={(e) => onChange("flare_type", e.target.value)}
                >
                  <option value="elevated">Elevated Flare (η_d=98%)</option>
                  <option value="enclosed_ground">
                    Enclosed Ground Flare (η_d=99.5%)
                  </option>
                  <option value="pit">Pit / Open Burn (η_d=95%)</option>
                </select>
              </div>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.75rem" }}>
                  CH₄ (%)
                  <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
                </label>
                <input
                  id="flare-ch4-input"
                  type="number"
                  className="mole-input"
                  min="0"
                  max="100"
                  step="0.1"
                  value={data.ch4_content !== undefined ? data.ch4_content : ""}
                  onChange={(e) => onChange("ch4_content", e.target.value)}
                  placeholder="e.g. 85.0"
                />
              </div>
            </div>
          )}

          {/* Operating conditions for Gas standard volume normalization */}
          <div
            className="form-grid-2"
            style={{ gap: "10px", marginTop: "10px" }}
          >
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: "0.75rem" }}>Operating Temp (°F)</label>
              <input
                type="number"
                className="mole-input"
                value={
                  data.operating_temperature !== undefined
                    ? data.operating_temperature
                    : ""
                }
                onChange={(e) =>
                  onChange("operating_temperature", e.target.value)
                }
                placeholder="Def: 60°F"
              />
            </div>
            <div className="input-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: "0.75rem" }}>
                Pressure (psia)
              </label>
              <input
                type="number"
                className="mole-input"
                value={
                  data.operating_pressure !== undefined
                    ? data.operating_pressure
                    : ""
                }
                onChange={(e) => onChange("operating_pressure", e.target.value)}
                placeholder="Def: 14.696"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CombustionForm;
