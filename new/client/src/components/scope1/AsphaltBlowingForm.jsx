import React, { useEffect } from "react";
import CustomDropdown from "../CustomDropdown";

const AsphaltBlowingForm = ({ data, onChange }) => {
  // Ensure fuel is set to Asphalt
  useEffect(() => {
    if (data.fuel !== "Asphalt") {
      onChange("fuel", "Asphalt");
    }
  }, [data.fuel, onChange]);

  return (
    <div className="asphalt-blowing-form">
      <h4 style={{ color: "var(--accent-color)", marginBottom: "15px" }}>
        Asphalt Blowing Process Parameters
      </h4>

      <div className="form-grid-2">
        <div className="input-group">
          <label>Process Emission Factor</label>
          <input
            type="text"
            className="mole-input readonly"
            value="Asphalt Blowing (10.43 kg CO₂/t, 0.0227 kg CH₄/t)"
            disabled
          />
        </div>

        <div className="input-group">
          <label>
            Asphalt Blown Throughput
            <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
          </label>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 120px",
              gap: "10px",
            }}
          >
            <input
              type="number"
              className="mole-input"
              value={data.amount || ""}
              onChange={(e) => onChange("amount", e.target.value)}
              placeholder="0.00"
              required
            />
            <CustomDropdown
              options={[
                { value: "tonne", label: "tonne" },
                { value: "ton", label: "short ton" },
                { value: "kg", label: "kg" },
              ]}
              value={data.unit || "tonne"}
              onChange={(val) => onChange("unit", val)}
            />
          </div>
        </div>
      </div>

      <div
        style={{
          marginTop: "12px",
          padding: "10px 14px",
          background: "#f9fafb",
          border: "1px solid #e5e7eb",
          borderRadius: "6px",
          fontSize: "0.8rem",
          color: "#6b7280",
        }}
      >
        <strong>API Compendium 2021 Section 6, Table 6-52:</strong> Oxidation of asphalt flux through air blowing at elevated temperature generating CO₂ and trace methane.
      </div>
    </div>
  );
};

export default AsphaltBlowingForm;
