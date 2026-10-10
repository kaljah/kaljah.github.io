import React, { useEffect } from "react";
import { Input } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { t } from "../../i18n";

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

export const AsphaltBlowingForm: React.FC<Scope1SubFormProps> = ({ data, onChange }) => {
  // Ensure fuel is set to Asphalt
  useEffect(() => {
    if (data.fuel !== "Asphalt") {
      onChange("fuel", "Asphalt");
    }
    // the unit shown by default must also be submitted
    if (!data.unit) onChange("unit", "tonne");
  }, [data.fuel, data.unit, onChange]);

  return (
    <div className="asphalt-blowing-form">
      <div className="form-grid-2">
        <div className="input-group">
          <label>{t("Process Emission Factor")}</label>
          <input
            type="text"
            className="mole-input readonly"
            value="Asphalt Blowing (10.43 kg CO₂/t, 0.0227 kg CH₄/t)"
            disabled
          />
        </div>

        <div className="input-group">
          <label>
            {t("Asphalt Blown Throughput")}
            <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
          </label>
          <div className="grid gap-[10px] [grid-template-columns:1fr_120px] max-[600px]:[grid-template-columns:1fr]">
            <Input
              type="number"
              value={data.amount || ""}
              onChange={(e) => onChange("amount", e.target.value)}
              placeholder="0.00"
              required
            />
            <CustomDropdown
              options={[
                { value: "tonne", label: t("tonne") },
                { value: "ton", label: t("short ton") },
                { value: "kg", label: t("kg") },
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

export default AsphaltBlowingForm;
