import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";

const PneumaticsForm = ({ data, onChange, sourceType }) => {
  const isEngineering = sourceType === "specific";

  return (
    <div className="pneumatics-form">

      {/* Device Type removed as per request */}

      <Field className="input-group" label={<>Devices
          <span className="text-[color:#b91c1c]! ml-[3px]!">*</span></>}>
<Input
          type="number"
         
          value={data.amount || ""}
          onChange={(e) => onChange("amount", e.target.value)}
          placeholder="Count"
          required
        />
</Field>

      {/* Engineering Mode: Additional Inputs */}
      {isEngineering && (
        <>
          <div className="input-group">
            <label>
              Bleed rate
              <span className="text-[color:#b91c1c]! ml-[3px]!">*</span>
            </label>
            <div
              className="grid gap-[10px] [grid-template-columns:1fr_100px] max-[600px]:[grid-template-columns:1fr]"
            >
              <Input
                type="number"
               
                value={data.pneu_bleed_rate || ""}
                onChange={(e) => onChange("pneu_bleed_rate", e.target.value)}
                placeholder="e.g. 15.4"
                required
              />
              <CustomDropdown
                options={[
                  { value: "scf", label: "scf/hr" },
                  { value: "m3", label: "m³/hr" },
                ]}
                value={data.pneu_bleed_unit || "scf"}
                onChange={(val) => onChange("pneu_bleed_unit", val)}
              />
            </div>
          </div>

          <Field className="input-group" label={<>CH₄ (%)
              <span className="text-[color:#b91c1c]! ml-[3px]!">*</span></>}>
<Input
              type="number"
             
              value={
                data.pneu_ch4_content !== undefined &&
                data.pneu_ch4_content !== null
                  ? data.pneu_ch4_content
                  : ""
              }
              onChange={(e) => onChange("pneu_ch4_content", e.target.value)}
              placeholder="e.g. 85"
              required
            />
</Field>

          <Field className="input-group" label={<>Hours per year
              <span className="text-[color:#b91c1c]! ml-[3px]!">*</span></>}>
<Input
              type="number"
             
              value={data.pneu_hours || ""}
              onChange={(e) => onChange("pneu_hours", e.target.value)}
              placeholder="whole month if blank"
              required
            />
</Field>
        </>
      )}
    </div>
  );
};

export default PneumaticsForm;
