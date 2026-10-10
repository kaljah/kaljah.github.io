import React, { useEffect } from "react";
import { Input } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { t } from "../../i18n";

const NITRIC_ACID_OPTIONS = [
  { value: "Nitric Acid - With NSCR", label: t("With Non-Selective Catalytic Reduction (NSCR) (2.0 kg N₂O/t)") },
  { value: "Nitric Acid - Without NSCR", label: t("Without NSCR / Uncontrolled (9.0 kg N₂O/t)") },
];

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

export const NitricAcidForm: React.FC<Scope1SubFormProps> = ({ data, onChange }) => {
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
            {t("Abatement Technology")}
            <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
          </label>
          <CustomDropdown
            options={NITRIC_ACID_OPTIONS}
            value={data.fuel || "Nitric Acid - With NSCR"}
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
                { value: "tonne", label: t("tonne HNO₃") },
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

export default NitricAcidForm;
