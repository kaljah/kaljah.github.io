import React, { useEffect } from "react";
import { Input } from "../../ui";
import CustomDropdown from "../CustomDropdown";

const ADIPIC_ACID_OPTIONS = [
  { value: "Adipic Acid - Thermal Abatement", label: "Thermal Abatement (13.0 kg N₂O/t)" },
  { value: "Adipic Acid - Catalytic Abatement", label: "Catalytic Abatement (53.0 kg N₂O/t)" },
  { value: "Adipic Acid - Uncontrolled", label: "Uncontrolled (300.0 kg N₂O/t)" },
];

const AdipicAcidForm = ({ data, onChange }) => {
  // the product and unit shown by default must also be in the submitted data (browser test #8:
  // "Please select a unit" while the unit box showed a tonne)
  useEffect(() => {
    if (!data.fuel) onChange("fuel", "Adipic Acid - Thermal Abatement");
    if (!data.unit) onChange("unit", "tonne");
  }, [data.fuel, data.unit, onChange]);

  return (
    <div className="adipic-acid-form">

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Abatement Technology
            <span className="text-[color:#b91c1c]! ml-[3px]!">*</span>
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
            <span className="text-[color:#b91c1c]! ml-[3px]!">*</span>
          </label>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 120px",
              gap: "10px",
            }}
          >
            <Input
              type="number"
             
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

    </div>
  );
};

export default AdipicAcidForm;
