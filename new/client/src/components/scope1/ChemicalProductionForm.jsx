import React from "react";
import CustomDropdown from "../CustomDropdown";

const CHEMICAL_OPTIONS = [
  { value: "Ethylene", label: "Ethylene (0.77 t CO₂/t)" },
  { value: "Ethylene Oxide", label: "Ethylene Oxide (0.46 t CO₂/t)" },
  { value: "Ethylene Dichloride", label: "Ethylene Dichloride (0.041 t CO₂/t)" },
  { value: "Acrylonitrile", label: "Acrylonitrile (1.00 t CO₂/t)" },
  { value: "Carbon Black", label: "Carbon Black (2.63 t CO₂/t)" },
  { value: "Methanol", label: "Methanol (0.67 t CO₂/t, 2.3 kg CH₄/t)" },
];

const ChemicalProductionForm = ({ data, onChange }) => {
  return (
    <div className="chemical-production-form">
      <h4 style={{ color: "var(--accent-color)", marginBottom: "15px" }}>
        Chemical Manufacturing Parameters
      </h4>

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Chemical Product
            <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
          </label>
          <CustomDropdown
            options={CHEMICAL_OPTIONS}
            value={data.fuel || "Ethylene"}
            onChange={(val) => onChange("fuel", val)}
            placeholder="Select Chemical..."
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
                { value: "tonne", label: "tonne (metric)" },
                { value: "ton", label: "ton (short)" },
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
        <strong>API Compendium 2021 Section 6, Table 6-167:</strong> Stoichiometric process CO₂ and CH₄ emissions from petrochemical production based on mass balance and catalytic selectivity.
      </div>
    </div>
  );
};

export default ChemicalProductionForm;
