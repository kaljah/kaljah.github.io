import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  sourceType?: string;
}

export const DehydratorForm: React.FC<Scope1SubFormProps> = ({ data, onChange, sourceType }) => {
  // Default/Custom: Simple inputs (throughput only)
  // Specific: Full engineering calculation inputs

  const isEngineering = sourceType === "specific";

  return (
    <div className="dehydrator-form">
      {/* Simple Mode: Throughput Only */}
      {!isEngineering && (
        <>
          <Field className="input-group" label="Throughput (MMscf/yr)">
            <Input
              type="number"
              value={data.dehy_throughput || ""}
              onChange={(e) => onChange("dehy_throughput", e.target.value)}
              placeholder="Annual throughput"
            />
          </Field>
        </>
      )}

      {/* Engineering Mode: Full API 5.3 Inputs */}
      {isEngineering && (
        <>
          <Field
            className="input-group"
            label={
              <>
                Throughput (MMscf/yr)
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={data.dehy_throughput || ""}
              onChange={(e) => onChange("dehy_throughput", e.target.value)}
              placeholder="Volume"
              required
            />
          </Field>

          <div className="input-group">
            <label>
              Glycol pump rate
              <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
            </label>
            <div className="flex! gap-[10px]!">
              <input
                type="number"
                className="mole-input flex-1!"
                value={data.dehy_pump_rate || ""}
                onChange={(e) => onChange("dehy_pump_rate", e.target.value)}
                placeholder="Rate"
                required
              />
              <div className="w-[100px]!">
                <CustomDropdown
                  options={[
                    { value: "gph", label: "gal/hr" },
                    { value: "lph", label: "L/hr" },
                    { value: "m3h", label: "m³/hr" },
                  ]}
                  value={data.dehy_pump_unit || "gph"}
                  onChange={(val) => onChange("dehy_pump_unit", val)}
                />
              </div>
            </div>
          </div>

          <Field
            className="input-group"
            label={
              <>
                CH₄ (%)
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={
                data.dehy_ch4_content !== undefined && data.dehy_ch4_content !== null
                  ? data.dehy_ch4_content
                  : ""
              }
              onChange={(e) => onChange("dehy_ch4_content", e.target.value)}
              placeholder="e.g. 85"
              required
            />
          </Field>

          <Field
            className="input-group"
            label={
              <>
                Hours per year
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={data.dehy_hours || ""}
              onChange={(e) => onChange("dehy_hours", e.target.value)}
              placeholder="whole month if blank"
              required
            />
          </Field>

          <Field
            className="input-group"
            label={
              <>
                Contactor pressure (psig)
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={data.dehy_press !== undefined ? data.dehy_press : ""}
              onChange={(e) => onChange("dehy_press", e.target.value)}
              placeholder="e.g. 1000"
              required
            />
          </Field>

          <Field
            className="input-group"
            label={
              <>
                Contactor temp (°F)
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={data.dehy_temp !== undefined ? data.dehy_temp : ""}
              onChange={(e) => onChange("dehy_temp", e.target.value)}
              placeholder="e.g. 100"
              required
            />
          </Field>

          <Field className="input-group" label="Stripping gas (scf/h)">
            <Input
              type="number"
              value={
                data.dehy_stripping_rate !== undefined && data.dehy_stripping_rate !== null
                  ? data.dehy_stripping_rate
                  : ""
              }
              onChange={(e) => onChange("dehy_stripping_rate", e.target.value)}
              placeholder="0 (Optional stripping gas)"
            />
          </Field>

          <div className="input-group">
            <label>Control device</label>
            <CustomDropdown
              options={[
                { value: "none", label: "No Controls" },
                { value: "flash", label: "Flash Tank Separator Only" },
                { value: "condenser", label: "Condenser" },
                { value: "flare", label: "Flare / Thermal Oxidizer" },
                { value: "vru", label: "Vapor Recovery Unit (VRU)" },
              ]}
              value={data.dehy_control || "none"}
              onChange={(val) => onChange("dehy_control", val)}
            />
          </div>

          {data.dehy_control !== "none" && (
            <Field className="input-group" label="Control Efficiency (%)">
              <Input
                type="number"
                value={data.dehy_eff || ""}
                onChange={(e) => onChange("dehy_eff", e.target.value)}
                placeholder="e.g. 60 (flash) or 90 (condenser)"
              />
            </Field>
          )}
        </>
      )}
    </div>
  );
};

export default DehydratorForm;
