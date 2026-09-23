import React from "react";
import CustomDropdown from "../CustomDropdown";

const ADIPIC_ACID_OPTIONS = [
  { value: "Adipic Acid - Thermal Abatement", label: "Thermal Abatement (13.0 kg N₂O/t)" },
  { value: "Adipic Acid - Catalytic Abatement", label: "Catalytic Abatement (53.0 kg N₂O/t)" },
  { value: "Adipic Acid - Uncontrolled", label: "Uncontrolled (300.0 kg N₂O/t)" },
];

const AdipicAcidForm = ({ data, onChange }) => {
  return (
    <div className="adipic-acid-form">
      <h4 style={{ color: "var(--accent-color)", marginBottom: "15px" }}>
        Adipic Acid Production (N₂O)
      </h4>

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Abatement Technology
            <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
          </label>
          <CustomDropdown
            options={ADIPIC_ACID_OPTIONS}
            value={data.fuel || "Adipic Acid - Thermal Abatement"}
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
                { value: "tonne", label: "tonne Adipic Acid" },
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
        <strong>API Compendium 2021 Section 6, pg 407:</strong> N₂O emissions from adipic acid synthesis during cyclohexanone/cyclohexanol oxidation with nitric acid.
      </div>
    </div>
  );
};

export default AdipicAcidForm;
