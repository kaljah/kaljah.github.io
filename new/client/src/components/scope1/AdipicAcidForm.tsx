import React, { useEffect } from "react";
import { Input } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { t } from "../../i18n";

const ADIPIC_ACID_OPTIONS = [
  { value: "Adipic Acid - Thermal Abatement", label: t("Thermal Abatement (13.0 kg N₂O/t)") },
  { value: "Adipic Acid - Catalytic Abatement", label: t("Catalytic Abatement (53.0 kg N₂O/t)") },
  { value: "Adipic Acid - Uncontrolled", label: t("Uncontrolled (300.0 kg N₂O/t)") },
];

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

export const AdipicAcidForm: React.FC<Scope1SubFormProps> = ({ data, onChange }) => {
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
            {t("Abatement Technology")}
            <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
          </label>
          <CustomDropdown
            options={ADIPIC_ACID_OPTIONS}
            value={data.fuel || "Adipic Acid - Thermal Abatement"}
            onChange={(val) => onChange("fuel", val)}
            placeholder={t("Select Abatement...")}
          />
        </div>

        <div className="input-group">
          <label>
            {t("Production Quantity")}
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
                { value: "tonne", label: t("tonne Adipic Acid") },
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

export default AdipicAcidForm;
