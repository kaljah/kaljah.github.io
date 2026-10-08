import React from "react";
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  sourceType?: string;
}

export const BlowdownForm: React.FC<Scope1SubFormProps> = ({ data, onChange }) => {
  return (
    <div className="blowdown-form">
      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Physical Volume
            <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
          </label>
          <div className="flex! gap-[10px]!">
            <Input
              type="number"
              value={data.blowdown_volume || ""}
              onChange={(e) => onChange("blowdown_volume", e.target.value)}
              placeholder="Vessel Vol"
              required
            />
            <NativeSelect
              className="mole-input w-[80px]! max-[600px]:w-full!"
              value={data.blowdown_unit || "m3"}
              onChange={(e) => onChange("blowdown_unit", e.target.value)}
            >
              <option value="m3">m³</option>
              <option value="ft3">ft³</option>
              <option value="bbl">bbl</option>
            </NativeSelect>
          </div>
        </div>

        <Field
          className="input-group"
          label={
            <>
              Pressure (psig)
              <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
            </>
          }
        >
          <Input
            type="number"
            value={data.blowdown_pressure || ""}
            onChange={(e) => onChange("blowdown_pressure", e.target.value)}
            placeholder="Before blowdown (psig)"
            required
          />
        </Field>

        <Field
          className="input-group"
          label={
            <>
              Number of Events
              <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
            </>
          }
        >
          <Input
            type="number"
            value={data.blowdown_events || ""}
            onChange={(e) => onChange("blowdown_events", e.target.value)}
            placeholder="Count"
            required
          />
        </Field>

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
            value={data.ch4_content !== undefined && data.ch4_content !== null ? data.ch4_content : ""}
            onChange={(e) => onChange("ch4_content", e.target.value)}
            placeholder="e.g. 85"
            required
          />
        </Field>

        <Field className="input-group" label="Gas CO2 Content (%)">
          <Input
            type="number"
            value={data.co2_content || ""}
            onChange={(e) => onChange("co2_content", e.target.value)}
            placeholder="e.g. 2.5"
          />
        </Field>

        <Field className="input-group" label="Temperature (°F)">
          <Input
            type="number"
            value={data.blowdown_temp !== undefined ? data.blowdown_temp : ""}
            onChange={(e) => onChange("blowdown_temp", e.target.value)}
            placeholder="Default: 60°F"
          />
        </Field>

        <Field className="input-group" label={<>Flare Efficiency (%){" "}</>}>
          <Input
            type="number"
            value={data.control_efficiency || ""}
            onChange={(e) => onChange("control_efficiency", e.target.value)}
            placeholder="0 = Vented, 98 = Flared"
          />
        </Field>
      </div>
    </div>
  );
};

export default BlowdownForm;
