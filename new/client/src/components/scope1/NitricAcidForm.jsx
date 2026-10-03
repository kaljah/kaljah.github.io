import React, { useEffect } from "react";
import { Input } from "../../ui";
import CustomDropdown from "../CustomDropdown";

const NITRIC_ACID_OPTIONS = [
  { value: "Nitric Acid - With NSCR", label: "With Non-Selective Catalytic Reduction (NSCR) (2.0 kg N₂O/t)" },
  { value: "Nitric Acid - Without NSCR", label: "Without NSCR / Uncontrolled (9.0 kg N₂O/t)" },
];

const NitricAcidForm = ({ data, onChange }) => {
  // the product and unit shown by default must also be in the submitted data (browser test #8:
  // "Please select a unit" while the unit box showed a tonne)
  useEffect(() => {
    if (!data.fuel) onChange("fuel", "Nitric Acid - With NSCR");
    if (!data.unit) onChange("unit", "tonne");
  }, [data.fuel, data.unit, onChange]);

  return (
    <div className="nitric-acid-form">

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Abatement Technology
            <span className="text-[color:#ef4444]! ml-[3px]!">*</span>
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
            <span className="text-[color:#ef4444]! ml-[3px]!">*</span>
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

    </div>
  );
};

export default NitricAcidForm;
