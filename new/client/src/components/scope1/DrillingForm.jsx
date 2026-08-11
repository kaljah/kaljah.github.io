import React from "react";
import CustomDropdown from "../CustomDropdown";

const DrillingForm = ({ data, onChange }) => {
  return (
    <div className="drilling-form">
      <h4 style={{ color: "var(--accent-color)", marginBottom: "15px" }}>
        Drilling Parameters
      </h4>

      <div className="input-group">
        <label>Mud Volume</label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 100px",
            gap: "10px",
          }}
        >
          <input
            type="number"
            className="mole-input"
            value={data.mud_vol || ""}
            onChange={(e) => onChange("mud_vol", e.target.value)}
            placeholder="Total Circulated"
          />
          <CustomDropdown
            options={[
              { value: "bbl", label: "bbl" },
              { value: "m3", label: "m³" },
              { value: "gal", label: "gal" },
            ]}
            value={data.mud_unit || "bbl"}
            onChange={(val) => onChange("mud_unit", val)}
          />
        </div>
      </div>

      <div className="input-group">
        <label>Mud Type</label>
        <CustomDropdown
          options={[
            { value: "water", label: "Water Based" },
            { value: "oil", label: "Oil Based" },
          ]}
          value={data.mud_type || "water"}
          onChange={(val) => onChange("mud_type", val)}
        />
      </div>

      <div className="input-group">
        <label>Fuel Use</label>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 100px",
            gap: "10px",
          }}
        >
          <input
            type="number"
            className="mole-input"
            value={data.fuel_use || ""}
            onChange={(e) => onChange("fuel_use", e.target.value)}
            placeholder="Diesel Gen/Engines"
          />
          <CustomDropdown
            options={[
              { value: "gal", label: "gal" },
              { value: "L", label: "L" },
              { value: "m3", label: "m³" },
            ]}
            value={data.fuel_unit || "gal"}
            onChange={(val) => onChange("fuel_unit", val)}
          />
        </div>
      </div>
      {/* Note: In legacy, fuel use here is separate from main combustion entry? Or integrated? 
                Legacy code processed it as: 
                em = { co2: co2Combustion, ch4: ch4Degassing, ... }
                So it combines both combustion and degassing into one record.
            */}
    </div>
  );
};

export default DrillingForm;
