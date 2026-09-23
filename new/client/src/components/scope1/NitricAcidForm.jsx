import React from "react";
import CustomDropdown from "../CustomDropdown";

const NITRIC_ACID_OPTIONS = [
  { value: "Nitric Acid - With NSCR", label: "With Non-Selective Catalytic Reduction (NSCR) (2.0 kg N₂O/t)" },
  { value: "Nitric Acid - Without NSCR", label: "Without NSCR / Uncontrolled (9.0 kg N₂O/t)" },
];

const NitricAcidForm = ({ data, onChange }) => {
  return (
    <div className="nitric-acid-form">
      <h4 style={{ color: "var(--accent-color)", marginBottom: "15px" }}>
        Nitric Acid Production (N₂O)
      </h4>

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Abatement Technology
            <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
          </label>
          <CustomDropdown
            options={NITRIC_ACID_OPTIONS}
            value={data.fuel || "Nitric Acid - With NSCR"}
            onChange={(val) => onChange("fuel", val)}
            placeholder="Select Abatement..."
          />
        </div>

        <div className="input-group">
          <label>
            Production Quantity
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
                { value: "tonne", label: "tonne HNO₃" },
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
        <strong>API Compendium 2021 Section 6, pg 407:</strong> N₂O formed as a byproduct of ammonia oxidation in the production of nitric acid (HNO₃). High GWP greenhouse gas (265× CO₂ AR5).
      </div>
    </div>
  );
};

export default NitricAcidForm;
