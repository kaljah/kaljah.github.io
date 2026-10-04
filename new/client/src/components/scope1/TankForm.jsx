import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";

const TankForm = ({ data, onChange, sourceType }) => {
  const isEngineering = sourceType === "specific";
  const processType = data.process_type || "tank";


  return (
    <div className="tank-form">

      <div className="input-group">
        <label>
          Throughput
          <span className="text-[color:#b91c1c]! ml-[3px]!">*</span>
        </label>
        <div
          className="grid gap-[10px] [grid-template-columns:1fr_100px] max-[600px]:[grid-template-columns:1fr]"
        >
          <Input
            type="number"
           
            value={data.amount || ""}
            onChange={(e) => onChange("amount", e.target.value)}
            placeholder="Enter throughput"
            required
          />
          <CustomDropdown
            options={[
              { value: "bbl", label: "bbl" },
              { value: "m3", label: "m³" },
              { value: "gal", label: "gal" },
            ]}
            value={data.tank_unit || "bbl"}
            onChange={(val) => onChange("tank_unit", val)}
          />
        </div>
      </div>

      {/* Tank Type: only needed for engineering mode. Default/Custom uses the outer catalog dropdown */}
      {isEngineering && (
        <div className="input-group">
          <label>Tank Type / Service</label>
          <CustomDropdown
            options={[
              { value: "TankCrudeSmall", label: "Crude Oil (< 10 bbl/d)" },
              { value: "TankCrudeLarge", label: "Crude Oil (> 10 bbl/d)" },
              { value: "TankProdSmall", label: "Condensate (< 10 bbl/d)" },
              { value: "TankProdLarge", label: "Condensate (> 10 bbl/d)" },
            ]}
            value={data.tank_type || "TankCrudeSmall"}
            onChange={(val) => onChange("tank_type", val)}
            placeholder="Select Tank Type..."
          />
        </div>
      )}

      {/* Engineering Mode: Calculation */}
      {isEngineering && (
        <>
          {/* Flashing / Working / Breathing Specific Inputs */}
          {["tank", "tank_flashing", "tank_working", "tank_breathing"].includes(processType) && (
            <>
              <Field className="input-group" label={<>GOR (scf/bbl)
                  <span className="text-[color:#b91c1c]! ml-[3px]!">*</span></>}>
<Input
                  type="number"
                 
                  value={data.tank_gor || ""}
                  onChange={(e) => onChange("tank_gor", e.target.value)}
                  placeholder="e.g. 500"
                  required
                />
</Field>

              <Field className="input-group" label="Oil API Gravity">
<Input
                  type="number"
                 
                  value={data.tank_api_gravity || ""}
                  onChange={(e) => onChange("tank_api_gravity", e.target.value)}
                  placeholder="e.g. 35"
                />
</Field>
            </>
          )}

          {/* Common Engineering Inputs */}
          <Field className="input-group" label="Temperature (°F)">
<Input
              type="number"
             
              value={data.tank_temp || ""}
              onChange={(e) => onChange("tank_temp", e.target.value)}
              placeholder="e.g. 60"
            />
</Field>

          <Field className="input-group" label="Separator pressure (psig)">
<Input
              type="number"
             
              value={data.tank_sep_pressure || ""}
              onChange={(e) => onChange("tank_sep_pressure", e.target.value)}
              placeholder="e.g. 50"
            />
</Field>

          <Field className="input-group" label={<>CH₄ (%)
              <span className="text-[color:#b91c1c]! ml-[3px]!">*</span></>}>
<Input
              type="number"
             
              value={
                data.tank_ch4_content !== undefined &&
                data.tank_ch4_content !== null
                  ? data.tank_ch4_content
                  : ""
              }
              onChange={(e) => onChange("tank_ch4_content", e.target.value)}
              placeholder="e.g. 85"
              required
            />
</Field>

          <div className="input-group">
            <label>Control Efficiency (%)</label>
            <Input
              type="number"
             
              value={data.tank_control_eff || ""}
              onChange={(e) => onChange("tank_control_eff", e.target.value)}
              placeholder="e.g. 95"
            />
            <div
              className="text-[length:0.75rem]! text-[color:#888]! mt-[4px]!"
            >
              VRU, Flaring, etc. (0 = uncontrolled)
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TankForm;
